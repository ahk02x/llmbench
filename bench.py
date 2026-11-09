#!/usr/bin/env python3
"""llmbench: speed + quality + VRAM-fit for models served by an Ollama host. Stdlib only.

  ./bench.py                       # every model on the default host, 3 speed runs each
  ./bench.py -m qwen2.5:14b --runs 5
  ./bench.py --host http://127.0.0.1:11434 --label m3 --note "M3 16GB"

The default host and label come from bench.local.json (git-ignored, e.g. {"host": "http://gpu-box:11434",
"label": "rtx3080"}), else LLMBENCH_HOST / LLMBENCH_LABEL, else localhost. Results never store the host URL:
Version 2 summaries append to results/<label>-<date>-v2.jsonl; per-call events survive later failures.
Speed numbers are only comparable on an idle GPU: an open RDP session on the PC pins it in P0.
"""
import argparse, json, re, sys, time, urllib.request, datetime, pathlib
import hashlib, statistics, uuid, http.client

HERE = pathlib.Path(__file__).parent
import os
_LOCAL = json.loads((HERE / "bench.local.json").read_text()) if (HERE / "bench.local.json").exists() else {}
DEFAULT_HOST = _LOCAL.get("host") or os.environ.get("LLMBENCH_HOST") or "http://127.0.0.1:11434"
DEFAULT_LABEL = _LOCAL.get("label") or os.environ.get("LLMBENCH_LABEL") or ""
SEED = {"temperature": 0, "seed": 7}
PARA = ("The quick survey of the harbour district found that warehouse lighting, cold storage and "
        "ferry schedules were all running to plan, with only minor delays reported on Tuesday. ")


def call(host, path, body=None, timeout=600):
    req = urllib.request.Request(host + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def generate(host, model, prompt, num_predict, cfg=None, keep="10m"):
    """cfg: per-model overrides from ladders.json: think (false / "low"), num_ctx."""
    cfg = cfg or {}
    body = {"model": model, "prompt": prompt, "stream": True, "keep_alive": keep,
            "options": {**SEED, "num_predict": num_predict, **({"num_ctx": cfg["num_ctx"]} if "num_ctx" in cfg else {})}}
    if "think" in cfg:
        body["think"] = cfg["think"]
    req = urllib.request.Request(host + "/api/generate", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    first_output = first_answer = None
    answer, thinking, final = [], [], None
    with urllib.request.urlopen(req, timeout=600) as response:
        for line in response:
            if not line.strip():
                continue
            d = json.loads(line)
            if "error" in d:
                raise ValueError(d["error"])
            elapsed = time.perf_counter() - start
            if (d.get("response") or d.get("thinking")) and first_output is None:
                first_output = elapsed
            if d.get("response") and first_answer is None:
                first_answer = elapsed
            answer.append(d.get("response", ""))
            thinking.append(d.get("thinking", ""))
            if d.get("done"):
                final = d
                break
    if final is None:
        raise ValueError("generation stream ended without a completed response")
    return {**final, "response": "".join(answer), "thinking": "".join(thinking),
            "wall_s": time.perf_counter() - start, "first_output_s": first_output,
            "first_answer_s": first_answer}


def identity(host, model):
    entry = next((m for m in call(host, "/api/tags")["models"]
                  if m["name"] in (model, model + ":latest")), None)
    if entry is None or not entry.get("digest"):
        raise ValueError("model digest unavailable; cannot identify this measurement")
    return {k: entry.get(k) for k in ("name", "digest", "size", "details")}


def allocation(host, model):
    entry = next((m for m in call(host, "/api/ps")["models"]
                  if m["name"] in (model, model + ":latest")), None)
    return {k: entry.get(k) for k in ("name", "digest", "size", "size_vram", "context_length")} if entry else None


def sample(host, model, prompt, limit, cfg, phase, index, record):
    """Journal each completed call immediately, so a later failure cannot erase it."""
    d = generate(host, model, prompt, limit, cfg)
    if d.get("eval_count") is None or not d.get("eval_duration"):
        raise ValueError("missing generation counters; no speed can be measured")
    s = {"phase": phase, "index": index, "prompt": prompt,
         "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "output_limit": limit,
         **{k: d.get(k) for k in ("response", "thinking", "done_reason", "eval_count", "eval_duration",
            "prompt_eval_count", "prompt_eval_duration", "prompt_eval_cached_count", "load_duration",
            "total_duration", "wall_s", "first_output_s", "first_answer_s")},
         "gen_tps": tps(d), "truncated": d.get("done_reason") == "length"}
    record({"event": "sample", **s})
    # Timing has stopped before this diagnostic request.
    s["allocation_after"] = allocation(host, model)
    record({"event": "allocation", "phase": phase, "index": index, "allocation": s["allocation_after"]})
    return s


def summarize(samples):
    rates = [s["gen_tps"] for s in samples]
    return {"gen_tps": round(statistics.median(rates), 1), "gen_min": round(min(rates), 1),
            "gen_max": round(max(rates), 1), "runs": len(samples), "samples": samples,
            "prompt_tokens": samples[-1]["prompt_eval_count"],
            "cache_protocol": "repeated prompt; cache reuse possible; not uncached prefill"}


def pull(host, tag):
    """Download a model onto the host (streams progress, prints every ~10%). Returns True when present."""
    req = urllib.request.Request(host + "/api/pull", data=json.dumps({"model": tag, "stream": True}).encode(),
                                 headers={"Content-Type": "application/json"})
    last = -10
    with urllib.request.urlopen(req, timeout=3600) as r:
        for line in r:
            d = json.loads(line)
            if "error" in d:
                print(f"   pull error: {d['error']}", flush=True)
                return False
            if d.get("total") and d.get("completed") is not None:
                pct = int(100 * d["completed"] / d["total"])
                if pct >= last + 10:
                    last = pct // 10 * 10
                    print(f"   pull {tag}: {pct}%", flush=True)
    return True


def haystack(needle, words=1100):
    """~1.5k tokens of filler with one fact buried in the middle."""
    n = max(1, words // len(PARA.split()))
    return (PARA * (n // 2)) + needle + " " + (PARA * (n - n // 2))


def tps(d):
    return d["eval_count"] / (d["eval_duration"] / 1e9) if d.get("eval_duration") else 0.0


def ptps(d):
    return d["prompt_eval_count"] / (d["prompt_eval_duration"] / 1e9) if d.get("prompt_eval_duration") else 0.0


def strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def check(spec, text):
    t = strip_think(text)
    kind = spec["type"]
    if kind == "word":
        words = re.findall(r"[a-z]+", t.lower())
        return bool(words) and words[0] == spec["answer"]
    if kind == "contains":
        return spec["answer"].lower() in t.lower()
    if kind == "number":
        nums = re.findall(r"-?\d+(?:\.\d+)?", t.replace(",", ""))
        return bool(nums) and abs(float(nums[-1]) - spec["answer"]) < 0.01
    if kind == "json":
        m = re.search(r"\{.*\}", t, flags=re.S)
        try:
            got = json.loads(m.group(0)) if m else None
        except ValueError:
            return False
        return got == spec["equals"]
    if kind == "lines":
        lines = [l for l in t.splitlines() if l.strip()]
        return len(lines) == spec["count"] and all(l.startswith(spec["prefix"]) for l in lines)
    raise ValueError(kind)


def loaded(host, model):
    return any(m["name"] in (model, model + ":latest") for m in call(host, "/api/ps").get("models", []))


def unload(host, model, wait_s=30):
    """Ask Ollama to drop the model (keep_alive 0) and wait until /api/ps stops listing it. True if it left."""
    if not loaded(host, model):
        return True
    call(host, "/api/generate", {"model": model, "keep_alive": 0})
    for _ in range(wait_s * 2):
        if not loaded(host, model):
            return True
        time.sleep(0.5)
    return False


def bench_model(host, model, runs, tasks, cfg=None, record=lambda event: None):
    cfg = cfg or {}
    out = {"model": model, "cfg": cfg, "runs": runs}
    out["unloaded_first"] = unload(host, model)
    first = generate(host, model, "Say OK.", 4, cfg)
    out["load_request"] = first
    out["first_load_s"] = first.get("load_duration", 0) / 1e9
    record({"event": "warmup", "unloaded_first": out["unloaded_first"], "response": first})
    ps = allocation(host, model)
    if ps:
        out["size_gb"] = round(ps["size"] / 1e9, 1)
        out["vram_pct"] = round(100 * ps["size_vram"] / ps["size"]) if ps["size"] else None
    short = "Write a 120-word explanation of how a hash table handles collisions."
    long_ = haystack("Filler.", 1100) + "\n\nSummarize the text above in two sentences."
    for label, prompt in (("short", short), ("long", long_)):
        samples = [sample(host, model, prompt, 200, cfg, label, i, record) for i in range(runs)]
        out[label] = summarize(samples)
    results = []
    for t in tasks:
        prompt = t["prompt"].replace("{{HAYSTACK}}", haystack(t.get("haystack_needle", "")))
        d = sample(host, model, prompt, cfg.get("max_tokens", 400), cfg, "task:" + t["id"], 0, record)
        results.append({"id": t["id"], "kind": t["kind"], "pass": check(t["check"], d["response"]),
                        "truncated": d["truncated"], "answer": d["response"], "sample": d})
    out["quality"] = {"passed": sum(r["pass"] for r in results), "total": len(results), "tasks": results}
    return out


def ctx_sweep(host, model, cfg, ctxs, runs=3, record=lambda event: None):
    """Repeat each window; actual input counts are retained, cache state is not controlled."""
    rows = []
    for n in ctxs:
        c = {**cfg, "num_ctx": n}
        first = generate(host, model, "Say OK.", 4, c)
        record({"event": "warmup", "num_ctx": n, "response": first})
        words = int(n * 0.6 / 1.14)
        prompt = haystack("Filler.", words) + "\n\nSummarize the text above in one sentence."
        samples = [sample(host, model, prompt, 100, c, f"ctx:{n}", i, record) for i in range(runs)]
        rows.append({"num_ctx": n, **summarize(samples)})
        print(f"   ctx {n:>6}: {rows[-1]['gen_tps']} gen t/s ({runs} calls)", flush=True)
    return rows


def append_json(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row) + "\n")
        f.flush()


def run():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--label",
                    help="machine name stored in results and the filename, e.g. rtx3080 (never the host URL)")
    ap.add_argument("-m", "--models", help="comma list; default = every model on the host")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--note", default="", help="free text stored with the run, e.g. GPU and power limit")
    ap.add_argument("-g", "--group", help="a named group from ladders.json (models + per-model settings)")
    ap.add_argument("--pull", action="store_true", help="download any model that is not on the host yet")
    ap.add_argument("--ctx", help="comma list of context sizes: run the context sweep instead of the task suite")
    a = ap.parse_args()
    if a.runs < 1:
        ap.error("--runs must be at least 1")
    try:
        ctxs = [int(x) for x in a.ctx.split(",")] if a.ctx else None
        if ctxs is not None and any(n < 256 for n in ctxs):
            raise ValueError()
    except ValueError:
        ap.error("--ctx must contain comma-separated integers of at least 256")

    try:
        version = call(a.host, "/api/version", timeout=8)["version"]
        installed = [m["name"] for m in call(a.host, "/api/tags", timeout=8)["models"]]
    except OSError as e:
        sys.exit(f"cannot reach {a.host}: {e}\nIs Ollama running there? Start it with `ollama serve`.")
    cfgs = {}
    if a.group:
        groups = json.loads((HERE / "ladders.json").read_text())
        if a.group not in groups:
            sys.exit(f"no group {a.group!r} in ladders.json; groups: {', '.join(groups)}")
        entries = groups[a.group]
        cfgs = {e["model"]: {k: v for k, v in e.items() if k != "model"} for e in entries}
        models = [e["model"] for e in entries if not a.models or e["model"] in a.models.split(",")]
    else:
        models = a.models.split(",") if a.models else [m for m in installed if "embed" not in m]
    tasks = json.loads((HERE / "tasks.json").read_text())
    if a.pull:
        for m in models:
            if m not in installed and m + ":latest" not in installed:
                print(f"-> pulling {m} ...", flush=True)
                if not pull(a.host, m):
                    sys.exit(f"could not pull {m}")

    if a.pull:
        installed = [m["name"] for m in call(a.host, "/api/tags")["models"]]
    have = lambda m: m in installed or m + ":latest" in installed
    missing = [m for m in models if not have(m)]
    if missing:
        sys.exit(f"not on {a.host}: {', '.join(missing)}\nPull them with `ollama pull <tag>` or rerun with --pull."
                 f"\nInstalled: {', '.join(installed) or 'nothing yet'}")
    if not models:
        sys.exit("no models to run: pass --models / --group, or `ollama pull` one first")

    stamp = datetime.datetime.now().astimezone()
    # the saved label belongs to the saved host only; any other --host gets local/remote unless --label is given
    label = a.label or (DEFAULT_LABEL if a.host == DEFAULT_HOST else "") \
        or ("local" if any(h in a.host for h in ("127.0.0.1", "localhost")) else "remote")
    label = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')
    session = str(uuid.uuid4())
    outfile = HERE / "results" / f"{label or 'unnamed'}-{stamp:%Y-%m-%d}-v2.jsonl"
    journal = outfile.with_suffix(".events.jsonl")
    source_hashes = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                     for name in ("bench.py", "tasks.json", "ladders.json")}
    base = {"schema_version": 2, "session_id": session, "host": label, "ollama": version,
            "note": a.note, "source_sha256": source_hashes, "requested_runs": a.runs,
            "model_order": models, "context_order": ctxs,
            "sampling_options": SEED, "mode": "context" if ctxs else "speed_tasks"}
    failed = []
    for m in models:
        meta = {**base, "model": m, "cfg": cfgs.get(m, {})}
        def record(event):
            append_json(journal, {**meta, "ts": datetime.datetime.now().astimezone().isoformat(), **event})
        try:
            record({"event": "start"})
            print(f"-> {m} ...", flush=True)
            meta["model_identity"] = identity(a.host, m)
            record({"event": "identity"})
            if ctxs:
                result = {"sweep": ctx_sweep(a.host, m, cfgs.get(m, {}), ctxs, a.runs, record)}
            else:
                result = bench_model(a.host, m, a.runs, tasks, cfgs.get(m), record)
            after = identity(a.host, m)
            if after["digest"] != meta["model_identity"]["digest"]:
                raise ValueError("model tag changed digest during measurement")
            row = {**meta, **result, "status": "complete"}
        except (OSError, http.client.HTTPException, KeyError, ValueError, TypeError, KeyboardInterrupt) as e:
            # Preserve failed attempts without publishing a misleading complete summary.
            # Avoid persisting exception strings, which can contain a private host URL.
            row = {**meta, "status": "interrupted" if isinstance(e, KeyboardInterrupt) else "failed",
                   "error_type": type(e).__name__, "detail": "See terminal; completed samples retained in event journal"}
            failed.append(m)
            print(f"   {row['status'].upper()} {m}: {e}", flush=True)
            record({"event": "finish", **row})
            append_json(outfile, {**row, "ts": datetime.datetime.now().astimezone().isoformat()})
            if isinstance(e, KeyboardInterrupt):
                return 130
            continue
        row["ts"] = datetime.datetime.now().astimezone().isoformat()
        append_json(outfile, row)
        record({"event": "finish", "status": "complete"})
        if not ctxs:
            print(f"   {row['short']['gen_tps']} short / {row['long']['gen_tps']} long gen t/s; "
                  f"{row['quality']['passed']}/{row['quality']['total']} smoke tasks")
    print("Repeated prompts may reuse cache. No uncached prefill claim is made.")
    print(f"saved -> {outfile}\nevents -> {journal}")
    return 1 if failed else 0


def main():
    try:
        return run()
    except KeyboardInterrupt:
        # Also cover startup, between models and writes outside the measured call.
        # A parsed complete summary remains authoritative if its finish event is absent.
        print("Interrupted; retain the summary and event files, including any incomplete tail.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
