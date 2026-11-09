# What the measurements actually mean

The historical tables cover 2 and 5 November 2026. Schema 2 is the revised harness. Its offline tests check collection and failure handling; they do not establish model performance. The separate 9 November follow-up contains actual 7B/14B runs on the 3080 and M3, with five calls per speed prompt and full raw evidence retained privately. It is one overnight session; the 2070 SUPER was skipped. See the dated section in REPORT.md and evidence/2026-11-09/summary.json.

## What the revised collector records

Every invocation gets a session ID. Each model records the server version, requested settings, model order, context order and SHA-256 of the harness, tasks and ladder. The model name, manifest digest and details are read before the run; a changed digest at the end fails the summary. This detects a tag changing across those checks, not every possible concurrent modification. Avoid pulls or tag changes during a session. The digest identifies the server's model manifest; this harness does not independently hash remote weights.

Each measured call keeps its exact prompt and hash, output limit, full answer and thinking text, token counts, server durations, stop reason and client timings. Runtime allocation is sampled after the call and outside the timed interval. It is not continuous utilization or peak memory measurement. Missing optional counters remain null.

| Field | Meaning |
|---|---|
| `wall_s` | Client time from request start to the completed stream, including network and server waiting. |
| `first_output_s` | Time until the first nonempty answer or thinking chunk arrives. |
| `first_answer_s` | Time until the first nonempty answer chunk arrives, excluding separate thinking output. Null if there is no answer. |
| `gen_tps` | Server output-token count divided by server generation duration. |
| `first_load_s` | Server load duration in the initial request. Unloading is attempted first; disk caches may remain warm. |
| `truncated` | Server says generation stopped at its length limit. |

Streaming chunks can contain multiple tokens. The first-output timings approximate the user's wait; they are not exact GPU first-token timestamps. Thinking embedded inside an answer field cannot be separated by these timings. The collector follows Ollama's [generate API](https://docs.ollama.com/api/generate) and [model listing API](https://docs.ollama.com/api/tags).

## Repeats and cache

`--runs` now applies to both speed prompts and each context setting. Summaries use the ordinary median, including averaging the middle two values for an even run count. The per-call records remain available; a median does not replace them. Quality tasks still run once per model and are the unchanged eight-task smoke suite.

Prompts repeat within a condition. Prefix-cache reuse is possible. We preserve the reported cached-token counter when available, but do not publish an uncached prompt-throughput number. The context workload still increases input length and configured window together. Repetition improves the evidence; it does not isolate those two effects.

## Keeping the evidence

New summaries append to `results/<label>-<date>-v2.jsonl`. A sibling `-v2.events.jsonl` journals each completed sample before the allocation lookup or next generation request. If a later request fails or the user interrupts, earlier completed calls remain there. The interrupted request itself may have no complete timing record. A failed or interrupted summary has no complete performance result. The process exits nonzero on any model failure, and with 130 on interruption.

Events include starts and finishes. A fully parsed `complete` summary is the completion record, even if interruption prevents the following finish event. If neither exists, the session is incomplete. Interruption during startup, between models or during a file write may leave no interrupted summary. Preserve any partial trailing line; it is not a complete measurement. Writes flush to the operating system, without a promise of power-loss durability. Notes and prompts are stored as written. Use public fixtures and review them before publishing.

The four original raw files remain unchanged. `report.py` selects only legacy rows for the historical report. Schema 2 sessions must be reviewed separately before updating the narrative or comparing machines. Never combine different configurations just because their notes mention the same GPU.

## What still needs testing

Run the shared 7B and 14B tags on each machine with matching digests, requested context and settings. Use the same server version where supported; disclose any difference. Record driver, OS, CPU/RAM/swap limits, power mode and competing work in the note. Save a session with five calls per condition on each of three separate days. Rotate the model order manually and preserve the recorded order. Match output limits and inspect actual token counts and cutoff flags.

On the 2070 SUPER, change one constraint at a time: competing GPU use, container CPU limit, RAM limit, then swap. That is how we can investigate the slow run without declaring a cause from the original comparison.

Future work: verified cache controls for uncached prefill; power-meter readings; continuous host telemetry; a larger frozen set of practical tasks with independent checks. The existing tasks are public and tiny. They cannot estimate the fraction of someone's job a model can do. This revision does not execute model-generated code.
