#!/usr/bin/env python3
"""llmbench: speed + quality + VRAM-fit for models served by an Ollama host. Stdlib only.

  ./bench.py                       # every model on the default host, 3 speed runs each
  ./bench.py -m qwen2.5:14b --runs 5
  ./bench.py --host http://127.0.0.1:11434 --label m3 --note "M3 16GB"

The default host and label come from bench.local.json (git-ignored, e.g. {"host": "http://gpu-box:11434",
"label": "rtx3080"}), else LLMBENCH_HOST / LLMBENCH_LABEL, else localhost. Results never store the host URL:
one JSON line per model is appended to results/<label>-<date>.jsonl, and a table is printed.
Speed numbers are only comparable on an idle GPU: an open RDP session on the PC pins it in P0.
"""
import argparse, json, re, sys, time, urllib.request, datetime, pathlib

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
    body = {"model": model, "prompt": prompt, "stream": False, "keep_alive": keep,
            "options": {**SEED, "num_predict": num_predict, **({"num_ctx": cfg["num_ctx"]} if "num_ctx" in cfg else {})}}
    if "think" in cfg:
        body["think"] = cfg["think"]
    return call(host, "/api/generate", body)


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


def bench_model(host, model, runs, tasks, cfg=None):
    cfg = cfg or {}
    out = {"model": model, "cfg": cfg}
    out["unloaded_first"] = unload(host, model)  # so the load below starts with the model out of memory
    first = generate(host, model, "Say OK.", 4, cfg)  # forces the load; the OS file cache may still be warm
    out["cold_load_s"] = round(first["load_duration"] / 1e9, 1)

    ps = next((m for m in call(host, "/api/ps")["models"] if m["name"] in (model, model + ":latest")), None)
    if ps:
        out["size_gb"] = round(ps["size"] / 1e9, 1)
        out["vram_pct"] = round(100 * ps["size_vram"] / ps["size"]) if ps["size"] else None

    short = "Write a 120-word explanation of how a hash table handles collisions."
    long_ = haystack("Filler.", 1100) + "\n\nSummarize the text above in two sentences."
    for label, prompt in (("short", short), ("long", long_)):
        gens, pes, ctx = [], [], 0
        for _ in range(runs):
            d = generate(host, model, prompt, 200, cfg)
            gens.append(tps(d)); pes.append(ptps(d)); ctx = d["prompt_eval_count"]
        gens.sort(); pes.sort()
        out[label] = {"gen_tps": round(gens[len(gens) // 2], 1), "prompt_tps": round(pes[len(pes) // 2]),
                      "gen_min": round(gens[0], 1), "gen_max": round(gens[-1], 1), "prompt_tokens": ctx}

    results = []
    for t in tasks:
        p = t["prompt"]
        if "{{HAYSTACK}}" in p:
            p = p.replace("{{HAYSTACK}}", haystack(t["haystack_needle"]))
        d = generate(host, model, p, cfg.get("max_tokens", 400), cfg)
        results.append({"id": t["id"], "kind": t["kind"], "pass": check(t["check"], d["response"]),
                        "truncated": d.get("done_reason") == "length",  # hit the token cap: a harness limit, not a model error
                        "answer": strip_think(d["response"])[:200]})
    out["quality"] = {"passed": sum(r["pass"] for r in results), "total": len(results), "tasks": results}
    return out


def ctx_sweep(host, model, cfg, ctxs):
    """Same model at growing context windows: how much still fits in VRAM, and what that does to speed.
    The prompt fills ~60% of the window, so the KV cache is genuinely in use, not just reserved."""
    rows = []
    for n in ctxs:
        c = {**cfg, "num_ctx": n}
        generate(host, model, "Say OK.", 4, c)  # (re)load at this window size
        ps = next((m for m in call(host, "/api/ps")["models"] if m["name"] in (model, model + ":latest")), None)
        words = int(n * 0.6 / 1.14)
        d = generate(host, model, haystack("Filler.", words) + "\n\nSummarize the text above in one sentence.", 100, c)
        rows.append({"num_ctx": n, "size_gb": round(ps["size"] / 1e9, 1) if ps else None,
                     "vram_pct": round(100 * ps["size_vram"] / ps["size"]) if ps and ps["size"] else None,
                     "prompt_tokens": d["prompt_eval_count"], "gen_tps": round(tps(d), 1),
                     "prompt_tps": round(ptps(d))})
        print(f"   ctx {n:>6}: {rows[-1]['size_gb']} GB, {rows[-1]['vram_pct']}% in VRAM, "
              f"{rows[-1]['gen_tps']} gen t/s, {rows[-1]['prompt_tps']} prompt t/s", flush=True)
    return rows


def main():
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
            if m not in installed and not any(i.startswith(m) for i in installed):
                print(f"-> pulling {m} ...", flush=True)
                if not pull(a.host, m):
                    sys.exit(f"could not pull {m}")

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
    outfile = HERE / "results" / f"{label}-{stamp:%Y-%m-%d}.jsonl"
    rows, failed = [], []
    if a.ctx:
        ctxs = [int(x) for x in a.ctx.split(",")]
        for m in models:
            print(f"-> context sweep {m} ...", flush=True)
            sweep = ctx_sweep(a.host, m, cfgs.get(m, {}), ctxs)
            with open(outfile.with_name(outfile.stem + "-ctx.jsonl"), "a") as f:
                f.write(json.dumps({"ts": stamp.isoformat(timespec="seconds"), "host": label, "ollama": version,
                                    "note": a.note, "model": m, "sweep": sweep}) + "\n")
        return
    for m in models:
        print(f"-> {m} ...", flush=True)
        try:
            result = bench_model(a.host, m, a.runs, tasks, cfgs.get(m))
        except (OSError, KeyError, ValueError) as e:  # out of memory, server dropped, odd response: skip, keep going
            failed.append(m)
            print(f"   FAILED {m}: {e}\n   (no row written; mention it when you submit results)", flush=True)
            continue
        row = {"ts": stamp.isoformat(timespec="seconds"), "host": label, "ollama": version, "note": a.note, **result}
        rows.append(row)
        with open(outfile, "a") as f:
            f.write(json.dumps(row) + "\n")

    if not rows:
        sys.exit(f"\nno model finished; failed: {', '.join(failed)}")
    print(f"\n{'model':<22}{'GB':>5}{'VRAM%':>7}{'load s':>8}{'gen t/s':>9}{'long t/s':>9}{'quality':>9}")
    for r in rows:
        q = r["quality"]
        print(f"{r['model']:<22}{r.get('size_gb', '?'):>5}{str(r.get('vram_pct', '?')):>7}{r['cold_load_s']:>8}"
              f"{r['short']['gen_tps']:>9}{r['long']['gen_tps']:>9}"
              f"{q['passed']:>6}/{q['total']}")
    print("\nprompt-eval rates are saved in the JSONL but not shown: the speed prompts repeat and per-call"
          "\ntiming isn't kept, so they are not a valid prefill speed. Don't quote them (README, method rule 8).")
    if failed:
        print(f"\nfailed (no row): {', '.join(failed)}")
    if rows:
        print(f"\nsaved -> {outfile}")


if __name__ == "__main__":
    main()
