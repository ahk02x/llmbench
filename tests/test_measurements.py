import io
import json
import pathlib
import tempfile
import unittest
import subprocess
from unittest.mock import patch

import bench
import report


def response():
    return {"response": "OK", "thinking": "", "done_reason": "stop", "eval_count": 10,
            "eval_duration": 2_000_000_000, "prompt_eval_count": 20,
            "prompt_eval_duration": 1_000_000_000, "load_duration": 100,
            "wall_s": 3, "first_output_s": 1, "first_answer_s": 1}


class Measurements(unittest.TestCase):
    def setUp(self):
        # Every test fails closed if it accidentally attempts a real HTTP request.
        self.network = patch.object(bench.urllib.request, "urlopen", side_effect=AssertionError("network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_stream_distinguishes_thinking_answer_and_completion(self):
        chunks = [{"thinking": "reason", "done": False}, {"response": "O", "done": False},
                  {"response": "K", "done": True, "eval_count": 2, "eval_duration": 100}]
        stream = io.BytesIO(b"\n".join(json.dumps(c).encode() for c in chunks))
        with patch.object(bench.urllib.request, "urlopen", return_value=stream), \
                patch.object(bench.time, "perf_counter", side_effect=[0, .1, .2, .3, .4]):
            d = bench.generate("http://fixture.invalid", "test", "prompt", 20)
        self.assertEqual(d["response"], "OK")
        self.assertEqual(d["thinking"], "reason")
        self.assertEqual((d["first_output_s"], d["first_answer_s"], d["wall_s"]), (.1, .2, .4))

    def test_incomplete_and_error_streams_are_not_results(self):
        for chunk in ({"response": "partial"}, {"error": "out of memory"}):
            with self.subTest(chunk=chunk), patch.object(bench.urllib.request, "urlopen",
                    return_value=io.BytesIO(json.dumps(chunk).encode())):
                with self.assertRaises(ValueError):
                    bench.generate("http://fixture.invalid", "test", "prompt", 20)

    def test_no_answer_has_no_first_answer_time(self):
        with patch.object(bench.urllib.request, "urlopen", return_value=io.BytesIO(
                b'{"thinking":"only thinking","done":true}')):
            d = bench.generate("http://fixture.invalid", "test", "prompt", 20)
        self.assertIsNone(d["first_answer_s"])
        self.assertIsNotNone(d["first_output_s"])

    def test_even_median_and_samples_are_preserved(self):
        samples = [{"gen_tps": n, "prompt_eval_count": 20} for n in (1, 9, 3, 5)]
        result = bench.summarize(samples)
        self.assertEqual(result["gen_tps"], 4)
        self.assertEqual(result["runs"], 4)
        self.assertEqual(result["samples"], samples)
        self.assertNotIn("prompt_tps", result)

    def test_completed_sample_survives_allocation_failure(self):
        events = []
        with patch.object(bench, "generate", return_value=response()), \
                patch.object(bench, "allocation", side_effect=OSError("lost server")):
            with self.assertRaises(OSError):
                bench.sample("fixture", "model", "prompt", 200, {}, "short", 0, events.append)
        self.assertEqual(events[0]["event"], "sample")
        self.assertEqual(events[0]["response"], "OK")
        self.assertEqual(events[0]["eval_duration"], 2_000_000_000)

    def test_context_repeats_every_setting(self):
        with patch.object(bench, "generate", return_value=response()) as gen, \
                patch.object(bench, "allocation", return_value=None):
            rows = bench.ctx_sweep("fixture", "model", {}, [2048, 8192], runs=4)
        self.assertEqual(gen.call_count, 10)  # two warmups plus eight measurements
        self.assertEqual([r["runs"] for r in rows], [4, 4])
        self.assertEqual([len(r["samples"]) for r in rows], [4, 4])

    def test_digest_lookup_and_latest_alias(self):
        with patch.object(bench, "call", return_value={"models": [{"name": "model:latest", "digest": "abc"}]}):
            self.assertEqual(bench.identity("fixture", "model")["digest"], "abc")
        with patch.object(bench, "call", return_value={"models": [{"name": "model:latest"}]}):
            with self.assertRaises(ValueError):
                bench.identity("fixture", "model")

    def test_invalid_runs_rejected_before_network(self):
        with patch("sys.argv", ["bench.py", "--runs", "0"]), self.assertRaises(SystemExit) as e:
            bench.main()
        self.assertEqual(e.exception.code, 2)

    def test_failed_attempt_retained_and_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for name in ("bench.py", "tasks.json", "ladders.json"):
                (root / name).write_bytes((bench.HERE / name).read_bytes())
            def fake_call(host, path, *args, **kwargs):
                return {"version": "fixture"} if path == "/api/version" else {"models": [{"name": "model"}]}
            with patch.object(bench, "HERE", root), patch.object(bench, "call", side_effect=fake_call), \
                    patch.object(bench, "identity", return_value={"digest": "abc"}), \
                    patch.object(bench, "bench_model", side_effect=OSError("private host details")), \
                    patch("sys.argv", ["bench.py", "--label", "fixture", "--models", "model"]):
                self.assertEqual(bench.main(), 1)
            summary = json.loads(next(root.glob("results/*-v2.jsonl")).read_text())
            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["model_identity"]["digest"], "abc")
            self.assertNotIn("private host details", json.dumps(summary))
            self.assertTrue(next(root.glob("results/*.events.jsonl")).exists())

    def test_new_sessions_cannot_replace_historical_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "results").mkdir()
            old = {"model": "m", "ts": "2026-11-02", "note": "RTX 3080", "value": 1}
            new = {**old, "schema_version": 2, "ts": "2026-11-09", "value": 999}
            (root / "results" / "test.jsonl").write_text(json.dumps(old) + "\n" + json.dumps(new) + "\n")
            (root / "results" / "test-v2.events.jsonl").write_text('{"schema_version":2,"broken":')
            (root / "results" / "test-v2.jsonl").write_text('{"schema_version":2,"broken":')
            with patch.object(report, "HERE", root):
                self.assertEqual(report.latest("*.jsonl", lambda r: r["model"])["m"]["value"], 1)

    def test_interrupt_during_startup_returns_130(self):
        with patch.object(bench, "call", side_effect=KeyboardInterrupt()), patch("sys.argv", ["bench.py"]):
            self.assertEqual(bench.main(), 130)

    def test_ladder_continues_failures_but_stops_interrupts(self):
        for code, calls in ((1, 4), (130, 1)):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                (root / "run_ladder.sh").write_bytes((bench.HERE / "run_ladder.sh").read_bytes())
                fake = root / "bench.py"
                fake.write_text('#!/bin/sh\necho call >> calls\nif [ "$(wc -l < calls)" -eq 1 ]; then exit '
                                + str(code) + '; fi\nexit 0\n')
                fake.chmod(0o700)
                result = subprocess.run(["/bin/zsh", str(root / "run_ladder.sh")], capture_output=True, text=True)
                self.assertEqual(result.returncode, code)
                self.assertEqual(len((root / "calls").read_text().splitlines()), calls)

    def test_full_session_success_digest_change_and_interrupt(self):
        for mode in ("success", "changed", "interrupt", "null_load"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                for name in ("bench.py", "tasks.json", "ladders.json"):
                    (root / name).write_bytes((bench.HERE / name).read_bytes())
                def fake_call(host, path, *args, **kwargs):
                    return {"version": "fixture"} if path == "/api/version" else {"models": [{"name": "model"}]}
                ids = [{"digest": "abc"}, {"digest": "different" if mode == "changed" else "abc"}]
                def generate(*args, **kwargs):
                    if mode == "interrupt":
                        raise KeyboardInterrupt()
                    if mode == "null_load":
                        return {**response(), "load_duration": None}
                    return response()
                with patch.object(bench, "HERE", root), patch.object(bench, "call", side_effect=fake_call), \
                        patch.object(bench, "identity", side_effect=ids), patch.object(bench, "unload", return_value=True), \
                        patch.object(bench, "allocation", return_value=None), patch.object(bench, "generate", side_effect=generate), \
                        patch("sys.argv", ["bench.py", "--label", "fixture", "--models", "model", "--runs", "2"]):
                    result = bench.main()
                self.assertEqual(result, {"success": 0, "changed": 1, "interrupt": 130, "null_load": 1}[mode])
                saved = json.loads(next(root.glob("results/*-v2.jsonl")).read_text())
                self.assertEqual(saved["status"], {"success": "complete", "changed": "failed", "interrupt": "interrupted", "null_load": "failed"}[mode])
                if mode == "success":
                    self.assertEqual(saved["short"]["runs"], 2)
                    self.assertEqual(len(saved["quality"]["tasks"]), 8)
                    events = [json.loads(l) for l in next(root.glob("results/*.events.jsonl")).read_text().splitlines()]
                    self.assertEqual(sum(e["event"] == "sample" for e in events), 12)

    def test_pull_refreshes_exact_installed_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for name in ("bench.py", "tasks.json", "ladders.json"):
                (root / name).write_bytes((bench.HERE / name).read_bytes())
            replies = [{"version": "fixture"}, {"models": [{"name": "model-other"}]},
                       {"models": [{"name": "model:latest"}]}]
            with patch.object(bench, "HERE", root), patch.object(bench, "call", side_effect=replies), \
                    patch.object(bench, "pull", return_value=True) as pull, \
                    patch.object(bench, "identity", return_value={"digest": "abc"}), \
                    patch.object(bench, "ctx_sweep", return_value=[]), \
                    patch("sys.argv", ["bench.py", "--label", "fixture", "--models", "model", "--pull", "--ctx", "2048"]):
                self.assertEqual(bench.main(), 0)
            pull.assert_called_once()


if __name__ == "__main__":
    unittest.main()
