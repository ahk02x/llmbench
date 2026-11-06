# llmbench

What can normal hardware actually do with free, open AI models? I ran the same tests on three machines I already own and wrote down everything, including the parts that went wrong.

- **Start here:** [REPORT.md](REPORT.md) (or the nicer [report.html](report.html)). It opens with a plain-English short version and a glossary.
- **All the numbers:** [RESULTS.md](RESULTS.md), built from the raw data in [`results/`](results/).
- **What's next:** [ROADMAP.md](ROADMAP.md).

The machines: an RTX 3080 12 GB (Ryzen 9 3900X, 32 GB RAM, Ollama 0.32.5), an RTX 2070 SUPER 8 GB in a home server container capped at 4 cores and 8 GB RAM (Ollama 0.32.1), and an Apple M3 laptop with 16 GB of unified memory (Ollama 0.40.14). Another process was using some of the 2070 SUPER's VRAM, and I was lightly using the laptop during its run. The harness talks to Ollama over HTTP from any machine and never logs into the box it's testing.

## Latest findings

The biggest surprise: on a 14B model (qwen2.5 14B Q4), my **laptop ran 11.4x faster than the 8 GB GPU**, 8.0 vs 0.7 tokens/s. Ollama reported 100% GPU allocation share on the M3 and 64% on the 2070 SUPER. On the shared 7B tags, the discrete GPUs were about 4.0 to 7.6x faster than the laptop; the 2070 SUPER's mistral allocation was not recorded. The machines differ in more than memory (software, CPU, background load), so the report treats these as whole-system results, not proof of one cause.

Regenerate RESULTS.md and report.html with `./report.py` after editing REPORT.md.

## Quick start

Install Python 3 and [Ollama for your OS](https://ollama.com/download), then clone or download this repository and open a terminal in its root folder. The Python scripts use only the standard library; there are no pip dependencies. Open the Ollama app or start its service; if it is not already running, run `ollama serve` in another terminal. See the [Ollama CLI reference](https://docs.ollama.com/cli) for pull and serve commands.

Pull the two smaller shared tags, then run the benchmark against the local Ollama server:

```sh
ollama pull mistral
ollama pull qwen2.5:7b
python3 bench.py --host http://127.0.0.1:11434 --label my-gpu --models mistral,qwen2.5:7b --runs 3 --note "Replace with GPU, memory, driver, OS, power limit and background load"
```

Choose a public label for your machine and replace the note before running. Keep the machine idle if possible and record anything else using its CPU, GPU or memory. Each completed model appends one row to `results/<label>-<date>.jsonl` beside `bench.py`, using your local date (`YYYY-MM-DD`). Rerunning on the same day appends rows; it does not replace them. Model pulls need internet access; the benchmark uses the local server once the models are installed.

To run the four shared tags used on the 2070 SUPER and M3, including the larger 14B models:

```sh
python3 bench.py --host http://127.0.0.1:11434 --label my-gpu --group card2 --pull --runs 3 --note "Replace with hardware and run conditions"
```

The 14B tags can spill into system RAM and run slowly on smaller GPUs. A partial run is still useful: record failures or skipped models. See [CONTRIBUTING.md](CONTRIBUTING.md) to submit your JSONL and machine details by pull request.

More options, all from `python3 bench.py --help`:

```sh
python3 bench.py --host http://127.0.0.1:11434 --label my-gpu -m qwen2.5:14b --pull --runs 5
python3 bench.py --host http://127.0.0.1:11434 --label my-gpu -g moe --pull
python3 bench.py --host http://127.0.0.1:11434 --label my-gpu -g quant -m qwen2.5:14b --pull --ctx 2048,8192,16384,32768
```

`--group` selects models and their settings from `ladders.json`; `--models` narrows that group when both are given. Without either, the harness runs installed models except tags containing `embed`. `--ctx` runs a context sweep instead of the speed/task suite and writes `results/<label>-<date>-ctx.jsonl`; it makes one call per setting regardless of `--runs`.

For optional local defaults, create the git-ignored `bench.local.json`, for example `{"host": "http://127.0.0.1:11434", "label": "my-gpu"}`. Explicit `--host` and `--label` arguments override those defaults. Results store the label in the `host` field, not the server address; free-text notes are saved as written.

Each speed row records first-request load duration (`cold_load_s`; newer rows unload the model first and record `unloaded_first`), generation tok/s (short and roughly 1.2–1.4k-token prompts, the middle sorted rate under the default three calls), API-reported prompt-eval rates, loaded allocation and its **reported GPU-resident share**, and pass/fail answers for the tasks in `tasks.json`.

The main speed-run prompt-eval rates are not published because identical prompts were repeated and the stored aggregate rates do not support an uncached whole-prompt throughput estimate. Context-sweep prompt rates are single-call API observations from the RTX 3080 only. The RTX 2070 SUPER mistral row has no recorded allocation or GPU share because the older `/api/ps` lookup missed the `:latest` tag; that lookup is now fixed. On the M3, GPU share is Ollama's reported allocation within memory shared by CPU and GPU. See REPORT.md for details.

## Sandbox: talk to the models

```
./sandbox/serve.py --open    # http://127.0.0.1:8311
```

A chat page for every model on the host. Each answer shows tok/s, prompt speed, load time and how much
of the model sat on the GPU. **Compare A vs B** sends one prompt to two models, one after the other.
The **benchmark task** buttons send the exact bench prompt (temperature 0, seed 7, no history) and grade
the answer with `bench.check()`. One difference: the page uses `/api/chat` and the bench uses `/api/generate`.
Knobs: system prompt, temperature, context size, max tokens, thinking mode (defaults from `ladders.json`).
The server binds to localhost and relays only tags/ps/version/show/chat, so a stray web page can't pull or
delete models through it. POSTs need an `X-Sandbox` header, which forces a CORS preflight that is never granted.
Chats stay in this browser's localStorage. **Save as JSON** downloads one.

## Method rules (the part that makes the numbers worth trusting)

1. temperature 0, fixed seed, a fixed output-token cap for each speed prompt (200; answers can stop earlier). Same prompts every run.
2. The first-request load duration is reported separately and never mixed into tok/s. Since 6 November 2026 the harness unloads the model first and records `unloaded_first`; the disk cache may still be warm. The published rows predate that, so their load times may not be cold starts.
3. Record competing GPU use and host load. The RTX 2070 SUPER run shared VRAM with another process, which limits cross-host interpretation. An open RDP session pins the 3080 in P0 and invalidates power numbers; sign out, do not just close.
4. Every row carries the Ollama version and a free-text note (power limit, driver, anything unusual).
5. Quality tasks are checked by code, not by a model. A model that writes its reasoning into the answer cannot be graded fairly by these format checks, so `qwen3:30b-a3b` with thinking is reported as speed only; its `instruct-2507` variant is graded.
6. Newer rows record whether each task hit its token cap (`truncated`); the first three speed rows do not, so their cutoff status is unknown.
7. Under the three-call default, speed runs store medians and min/max but do not store the run count or individual call timings. Context points, first-request load durations, and task answers are single calls.
8. The speed rows' prompt-eval rates (`prompt_tps`) are kept in the JSONL but are not a valid prefill benchmark: the speed prompts repeat and per-call timing is not saved, so values can read in the hundreds of thousands of tokens/s. `bench.py` leaves them out of its summary table; don't quote them.

## Status

- [x] Harness, 8 deterministic tasks, first run (see `results/`)
- [x] Warm-up: once, the very first call after waking the PC ran at about 14 tok/s (seen by hand, not saved in `results/`). Warm, the same 14B does ~71 tok/s, so the harness now loads each model before timing anything. Cause of the slow first call not isolated
- [x] Model ladder: quantization levels, context length vs VRAM, MoE models spilling into system RAM (see `RESULTS.md`, `report.html`)
- [x] Second and third machine: RTX 2070 SUPER 8 GB and Apple M3 16 GB
- [x] Technical report with a plain-English summary
- [ ] Save run count, per-call timings and model digests, then rerun all 3 machines
- [ ] Power sweep: joules per token at 250 / 320 / 390 W
- [ ] Real-workload replay (see [ROADMAP.md](ROADMAP.md))
- [ ] Public page on the site via the existing daily publish job

The ordered plan is in [ROADMAP.md](ROADMAP.md).

## First results (2026-11-02, RTX 3080 12 GB, Ollama 0.32.5)

| model | allocation GB | GPU share | first load s | short gen tok/s | long gen tok/s | tasks |
|---|---:|---:|---:|---:|---:|---:|
| qwen2.5-coder:14b | 9.5 | 100% | 21.6 | 71.4 | 69.9 | 8/8 |
| qwen2.5:14b (latest row) | 9.5 | 100% | 11.3 | 71.7 | 69.7 | 7/8 |
| mistral (7B) | 5.0 | 100% | 24.2 | 145.3 | 139.6 | 7/8 |

The two 7/8 scores above missed the train-arrival task. Eight tasks are a smoke test, not a quality ranking. The first three speed rows have no task cutoff flags.

## Second-card results (2026-11-05, RTX 2070 SUPER 8 GB, Ollama 0.32.1)

| model | allocation GB | GPU share | short gen tok/s | long gen tok/s | tasks |
|---|---:|---:|---:|---:|---:|
| mistral 7B | Not recorded | Not recorded | 77.6 | 75.8 | 7/8 |
| qwen2.5 7B | 4.7 | 100% | 75.7 | 75.7 | 7/8 |
| qwen2.5 14B Q3 | 8.3 | 77% | 1.1 | 1.1 | 8/8 |
| qwen2.5 14B Q4 | 10.0 | 64% | 0.7 | 0.7 | 7/8 |

The mistral allocation fields were not recorded because the harness's older `/api/ps` lookup missed the `:latest` alias. The [report](REPORT.md) compares shared model tags and discusses host differences.

## Apple M3 results (2026-11-05, 16 GB unified memory, Ollama 0.40.14)

| model | allocation GB | GPU share | short gen tok/s | long gen tok/s | tasks |
|---|---:|---:|---:|---:|---:|
| mistral 7B | 5.0 | 100% | 19.2 | 18.1 | 7/8 |
| qwen2.5 7B | 4.8 | 100% | 19.1 | 18.9 | 7/8 |
| qwen2.5 14B Q3 | 7.9 | 100% | 7.8 | 7.8 | 7/8 |
| qwen2.5 14B Q4 | 9.5 | 100% | 8.0 | 8.0 | 7/8 |

Here, 100% is Ollama's allocation report for a shared memory pool. Q3 generated slightly slower than Q4 despite its smaller allocation; the run does not explain the ordering.

## License and attribution

Code is licensed under the [MIT License](LICENSE). The results data in `results/*.jsonl`, [RESULTS.md](RESULTS.md), and the report ([REPORT.md](REPORT.md) and its rendered content in [report.html](report.html)) are licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

When reusing the data or report, credit the llmbench contributors, link to the source repository and the license, and indicate changes. Include the commit and result filename when citing a measurement so readers can find the exact row. Model weights remain under their respective model licenses.
