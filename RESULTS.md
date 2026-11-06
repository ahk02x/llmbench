# Results

## RTX 3080 12 GB

Ollama 0.32.5; measurements on 2026-11-02. Latest row per model on this GPU. Under the harness default, generation rates are medians of three calls per prompt (run count was not saved); load and tasks are single calls. The stored cold_load_s field is a first-request load duration, not a verified cold start: the harness does not force an unload. GPU share is Ollama's reported allocation ratio. See [REPORT.md](REPORT.md) for method and limitations.

| model | allocation GB | GPU share | short gen tok/s | long gen tok/s | first load s | tasks |
|---|---:|---:|---:|---:|---:|---|
| mistral 7B | 5.0 | 100% | 145.3 | 139.6 | 24.2 | 7/8 |
| qwen3 14B | 9.6 | 100% | 78.3 | 76.4 | 13.5 | 8/8 |
| qwen2.5 14B (4-bit) | 9.5 | 100% | 71.7 | 69.7 | 11.3 | 7/8 |
| qwen2.5-coder 14B | 9.5 | 100% | 71.4 | 69.9 | 21.6 | 8/8 |
| gpt-oss 20B (MoE) | 14.0 | 74% | 62.9 | 63.5 | 24.1 | 8/8 |
| qwen2.5 14B (3-bit) | 7.9 | 100% | 62.0 | 60.7 | 11.8 | 8/8 |
| qwen3 30B-A3B (MoE) | 19.2 | 55% | 42.6 | 48.3 | 24.7 | 8/8 |
| qwen3 30B-A3B thinking (MoE) | 19.2 | 55% | 41.4 | 42.2 | 23.5 | n/a (speed only) |
| qwen2.5 14B (6-bit) | 13.1 | 80% | 14.1 | 13.8 | 15.6 | 7/8 |
| qwen2.5 14B (8-bit) | 16.7 | 63% | 6.2 | 5.9 | 19.1 | 7/8 |
| qwen3 32B | 21.6 | 48% | 3.1 | 3.2 | 22.6 | 8/8 |

## RTX 2070 SUPER 8 GB

Ollama 0.32.1; measurements on 2026-11-05. Latest row per model on this GPU. Generation rates use the same harness default; run count was not saved. Mistral allocation and GPU share were not recorded because the earlier `/api/ps` lookup missed its `:latest` tag.

| model | allocation GB | GPU share | short gen tok/s | long gen tok/s | first load s | tasks |
|---|---:|---:|---:|---:|---:|---|
| mistral 7B | Not recorded | Not recorded | 77.6 | 75.8 | 4.0 | 7/8 |
| qwen2.5 7B | 4.7 | 100% | 75.7 | 75.7 | 6.8 | 7/8 |
| qwen2.5 14B (3-bit) | 8.3 | 77% | 1.1 | 1.1 | 18.1 | 8/8 |
| qwen2.5 14B (4-bit) | 10.0 | 64% | 0.7 | 0.7 | 24.9 | 7/8 |

## Apple M3 16 GB unified

Ollama 0.40.14; measurements on 2026-11-05. Latest row per model on this machine. Generation rates use the same harness default; run count was not saved. GPU share is Ollama's reported allocation ratio in a shared CPU/GPU memory pool, not a discrete VRAM boundary.

| model | allocation GB | GPU share | short gen tok/s | long gen tok/s | first load s | tasks |
|---|---:|---:|---:|---:|---:|---|
| mistral 7B | 5.0 | 100% | 19.2 | 18.1 | 5.9 | 7/8 |
| qwen2.5 7B | 4.8 | 100% | 19.1 | 18.9 | 3.9 | 7/8 |
| qwen2.5 14B (4-bit) | 9.5 | 100% | 8.0 | 8.0 | 8.4 | 7/8 |
| qwen2.5 14B (3-bit) | 7.9 | 100% | 7.8 | 7.8 | 7.8 | 7/8 |

## Shared tags: short generation

`mistral` resolves to `mistral:latest`; model digests were not stored. A dash means the tag was not measured on that machine.

| model | RTX 3080 12 GB share | RTX 3080 12 GB tok/s | RTX 2070 SUPER 8 GB share | RTX 2070 SUPER 8 GB tok/s | Apple M3 16 GB unified share | Apple M3 16 GB unified tok/s |
|---|---:|---:|---:|---:|---:|---:|
| mistral 7B | 100% | 145.3 | Not recorded | 77.6 | 100% | 19.2 |
| qwen2.5 7B | — | — | 100% | 75.7 | 100% | 19.1 |
| qwen2.5 14B (3-bit) | 100% | 62.0 | 77% | 1.1 | 100% | 7.8 |
| qwen2.5 14B (4-bit) | 100% | 71.7 | 64% | 0.7 | 100% | 8.0 |

Main-row long-prompt `prompt_tps` is omitted: repeated identical prompts produced implausible whole-prompt rates and per-call timings were not stored. The first three RTX 3080 speed rows have no truncation flag, so their cutoff status is unknown.

## RTX 3080 12 GB context window sweep (prompt fills about 58–60% of the window)

One call per setting. Prompt rates are API-reported single-call observations; cache diagnostics were not stored. The MoE sweep used a thinking tag distinct from the instruct tag above.

| model | window | prompt tokens | allocation GB | GPU share | gen tok/s | API prompt tok/s |
|---|---:|---:|---:|---:|---:|---:|
| qwen2.5 14B (4-bit) | 2,048 | 1,221 | 9.1 | 100% | 70.6 | 2,583 |
| qwen2.5 14B (4-bit) | 8,192 | 4,786 | 10.3 | 100% | 66.4 | 2,388 |
| qwen2.5 14B (4-bit) | 16,384 | 9,560 | 12.4 | 85% | 18.4 | 1,731 |
| qwen2.5 14B (4-bit) | 32,768 | 19,108 | 15.7 | 66% | 3.8 | 1,113 |
| qwen3 30B-A3B thinking (MoE) | 2,048 | 1,202 | 19.0 | 56% | 51.8 | 907 |
| qwen3 30B-A3B thinking (MoE) | 8,192 | 4,767 | 19.6 | 53% | 47.4 | 1,563 |
| qwen3 30B-A3B thinking (MoE) | 16,384 | 9,541 | 20.4 | 51% | 44.0 | 1,701 |
| qwen3 30B-A3B thinking (MoE) | 32,768 | 19,089 | 22.1 | 48% | 36.9 | 1,560 |
