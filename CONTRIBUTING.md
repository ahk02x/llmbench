# Contributing results

I want results from ordinary machines, including slow runs and failures. You do not need a fast GPU or a complete model ladder to contribute. Please keep the raw measurements intact and explain the conditions so someone else can interpret them.

## Run the shared comparison

Follow the [README quick start](README.md#quick-start) to install Python 3 and Ollama, start the local Ollama server, and open a terminal in the repository root. The harness has no pip dependencies. Use local model tags for this hardware benchmark.

Choose a public machine label such as `my-gpu` (lowercase letters, digits and hyphens), and replace the note with your actual details:

```sh
python3 bench.py --host http://127.0.0.1:11434 --label my-gpu --group card2 --pull --runs 3 --note "GPU=...; VRAM_or_unified_memory=...; driver=...; OS=...; power_limit=...; background_load=..."
```

`card2` in `ladders.json` contains `mistral`, `qwen2.5:7b`, `qwen2.5:14b-instruct-q3_K_M` and `qwen2.5:14b`. `--pull` downloads missing models. The two 14B tags can be very slow when they spill into system RAM. For a smaller submission, use the same command with `--models mistral,qwen2.5:7b` added. Include which models you skipped and why; do not invent rows for failed models.

Each completed speed/task result is appended to `results/<label>-<date>.jsonl`, using the local date in `YYYY-MM-DD` format. Existing rows remain when you rerun; use a distinct label for a different machine or configuration. If your filename conflicts with an existing contribution, choose a more specific public label before running.

For an optional context sweep, run:

```sh
python3 bench.py --host http://127.0.0.1:11434 --label my-gpu --group quant --models qwen2.5:14b --pull --ctx 2048,8192,16384,32768 --note "Replace with the same hardware and run conditions"
```

Context results go to `results/<label>-<date>-ctx.jsonl`. This mode makes one generation call per setting and replaces the speed/task suite; `--runs` does not add repetitions to it. Report any failed windows.

## What to record

Include the following in the pull request description (or the results issue template). Use `unknown` or `not applicable` when a value is unavailable, with a brief reason.

- Exact GPU or SoC model, number of GPUs, and VRAM per GPU; for unified memory, give the total shared memory instead of calling it dedicated VRAM.
- CPU, system RAM, and any container or VM CPU/RAM/swap limits.
- OS and version, GPU driver version, and Ollama version; each JSONL row records the server's Ollama version automatically.
- Configured GPU power limit in watts, whether it is stock or changed, and laptop AC/battery and power mode; a power limit is not a measured power draw.
- Other GPU/CPU users, occupied VRAM before the run, remote desktop sessions and other background work; aim for an idle machine but disclose what was running.
- Repository commit (`git rev-parse HEAD`), exact command, model tags, run count and date; include any changes to `bench.py`, `ladders.json` or `tasks.json` and any non-default Ollama settings, including context size, flash attention, KV-cache type or concurrency.
- Failures, interruptions, skipped models, and whether `unloaded_first` came out false for any row (the model could not be unloaded before timing its load).

The current harness stores aggregate generation rates and min/max, but not individual call timings, run count or model digests. Keep the command and run conditions with your submission. Matching model tags alone do not establish identical model bytes across machines or dates. Leave prompts, checkers and model settings unchanged for a baseline comparison; submit altered configurations separately and explain them.

The main speed rows' prompt-evaluation rates are invalid for uncached throughput because prompts repeat and per-call timing is missing. Preserve the raw fields, but do not present them as benchmark findings. The eight tasks are a smoke test, not a general quality ranking.

## Submit a pull request

1. Fork the repository and create a branch for your results.
2. Add your generated JSONL under `results/` as `<label>-<date>.jsonl` (plus the optional `-ctx.jsonl` file). Do not overwrite another submission or edit measured values, scores or answers. Include all completed rows from the run, not just the fastest ones.
3. Review the label, free-text note, logs and PR description for private hostnames, addresses, names, employer details or credentials before publishing. The JSONL `host` field stores your chosen label, not the server URL; notes are saved verbatim. If you need to redact identifying metadata, say which fields you redacted and leave measurements intact.
4. Open a pull request with the machine details, exact command and any failures listed above. By submitting results, you agree to publish them under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); code contributions use the [MIT License](LICENSE).

If you need help, open a **Submit my results** issue using the template and link your draft PR. The JSONL pull request is the submission of record; screenshots alone are not enough to check the measurements.

You do not need to edit the summary tables for a results submission. `report.py` currently selects the three original GPU families by text in the run notes, rather than building a leaderboard of distinct contributed machines. A maintainer must review that selection before including community results, so that different machines are not silently combined. `REPORT.md` and the README's tables are maintained by hand; `./report.py` builds `RESULTS.md` and `report.html` locally without network access.

For harness or documentation bugs, use the **Bug report** issue template with a minimal reproduction and relevant error output.
