# Run llmbench

Install Python 3 and [Ollama for your OS](https://ollama.com/download), then clone or download this repository and open a terminal in its root folder. The Python scripts use only the standard library; there are no pip dependencies. Open the Ollama app or start its service; if it is not already running, run `ollama serve` in another terminal. See the [Ollama CLI reference](https://docs.ollama.com/cli) for pull and serve commands.

Pull the two smaller shared tags, then run the benchmark against the local Ollama server:

```sh
ollama pull mistral
ollama pull qwen2.5:7b
python3 bench.py --host http://127.0.0.1:11434 --label my-gpu --models mistral,qwen2.5:7b --runs 3 --note "Replace with GPU, memory, driver, OS, power limit and background load"
```

Choose a public label for your machine and replace the note before running. Keep the machine idle if possible and record anything else using its CPU, GPU or memory. Each completed or failed model appends one summary row to `results/<label>-<date>-v2.jsonl` beside `bench.py`, using your local date (`YYYY-MM-DD`). Rerunning on the same day appends rows; it does not replace them. Model pulls need internet access; the benchmark uses the local server once the models are installed.

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

`--group` selects models and their settings from `ladders.json`; `--models` narrows that group when both are given. Without either, the harness runs installed models except tags containing `embed`. `--ctx` runs a context sweep instead of the speed/task suite and repeats each setting `--runs` times. Both modes write schema 2 summaries and a sibling `-v2.events.jsonl` journal, tagged with their mode and session ID.

For optional local defaults, create the git-ignored `bench.local.json`, for example `{"host": "http://127.0.0.1:11434", "label": "my-gpu"}`. Explicit `--host` and `--label` arguments override those defaults. Results store the label in the `host` field, not the server address; free-text notes are saved as written.

Every timed call retains its prompt, full response, token counts, server durations, client time to first output and first answer, total elapsed time, cutoff status and a post-call allocation snapshot. Each session records model identity and source hashes. Completed calls are journaled immediately so a later failure does not erase them. See [MEASUREMENTS.md](MEASUREMENTS.md) for field definitions and limits.

Repeated prompts may reuse cache. We do not turn those timings into an uncached prefill claim. Generation speed also does not tell you how long you wait before the answer starts; the new streaming timings capture that separately.

## Optional chat sandbox

```
./sandbox/serve.py --open    # http://127.0.0.1:8311
```

The sandbox is experimental. Its stored model badges do not yet handle the new result format correctly; use the report for benchmark results.

A chat page for every model on the host. Each answer shows tok/s, prompt speed, load time and how much
of the model sat on the GPU. **Compare A vs B** sends one prompt to two models, one after the other.
The **benchmark task** buttons send the exact bench prompt (temperature 0, seed 7, no history) and grade
the answer with `bench.check()`. One difference: the page uses `/api/chat` and the bench uses `/api/generate`.
Knobs: system prompt, temperature, context size, max tokens, thinking mode (defaults from `ladders.json`).
The server binds to localhost and relays only tags/ps/version/show/chat, so a stray web page can't pull or
delete models through it. POSTs need an `X-Sandbox` header, which forces a CORS preflight that is never granted.
Chats stay in this browser's localStorage. **Save as JSON** downloads one.


## Offline development checks

Run `python3 -m unittest discover -s tests -v` for offline collection checks. Run `python3 report.py` to rebuild the historical tables and the HTML edition of the report. Neither command runs inference.

The HTML edition is an offline file: clone or download the repository and open `report.html` in a browser. GitHub displays HTML as source; it does not host this report as a website.
