# Local LLM inference on two NVIDIA cards and an Apple M3

Amir Khademi · Measurements from 2, 5 and 9 November 2026

## The short version

I wanted to know what I could actually run on the hardware I already own. My gaming PC has an RTX 3080 with 12 GB of memory. The home server has an older 8 GB 2070 SUPER. My laptop is an M3 with 16 GB shared between the CPU and GPU.

I expected the GPUs to win. On smaller models, they did. Then the laptop beat the older GPU on a 14B model tag, and I wanted to understand why.

The original measurements below are from 2 and 5 November 2026. A separate follow-up on 9 November used the improved harness on the 3080 and M3; the 2070 SUPER was skipped to preserve its existing workload. The old raw files stay exactly as recorded. Better code today cannot fill in something I did not measure then.

### Why did the 3080 slow down so much?

Think of memory as the space the model needs to work in. A powerful GPU with too little space can end up doing a very different job from the one you expected.

On the 3080, the Q4 version of Qwen2.5 14B generated **71.7 tokens a second**. The larger Q8 version reached **6.2**. Ollama reported all of the Q4 allocation on the GPU, compared with 63% for Q8. That is a big enough change to turn a comfortable reply into a wait.

Q4 and Q8 store the model's numbers at different precision. That changes size and computation together. The result gives me a reason to investigate memory spill; it does not prove that memory alone caused the slowdown.

### How did the laptop beat the older GPU?

The M3 generated **8.0 tokens a second** on the Qwen2.5 14B Q4 tag. The 2070 SUPER managed **0.7**. The laptop reported its whole allocation on the GPU side of shared memory; the card reported 64%.

That fits the memory explanation, but the machines had different software versions, CPU and RAM limits, and background work. I also did not save model digests, so the same tag is not proof of identical files. What I can say is that the laptop won this particular run. I need a more controlled comparison to explain how much each difference mattered.

On the smaller mistral tag, the order reversed: **145.3** on the 3080, **77.6** on the 2070 SUPER, and **19.2** on the M3. There is no single winner across these workloads.

### Does a bigger model help me do better work?

I don't know yet. The eight tasks ask for small things: pull fields out of a message, calculate a number, follow a format, find a fact in a longer prompt. The graded models scored 7 or 8 out of 8. That tells me the basic path works. It does not tell me which model I should trust to fix code or explain an incident.

A 30B mixture-of-experts model also ran much faster than a dense 32B model in this setup: **42.6 versus 3.1 tokens a second**. They are different models, so this is an interesting next test rather than proof that one architecture always wins.

### What happens when the conversation gets longer?

The model needs memory for the conversation as well as its weights. In the 3080 context test, Qwen2.5 14B Q4 went from **66.4 tokens a second at 8k** to **3.8 at 32k**. Its reported GPU share fell too. The input also grew, and I took only one measurement per setting. I would not call that a repeatable curve yet.

For me, the useful question is now: **which model can finish my task correctly, within a wait I can live with?** Fitting in memory and generating quickly are parts of that answer. Neither is the whole answer.

### Words used in this report

| Word | What it means here |
|:--|:--|
| Token | A chunk of text the model reads or writes; its size depends on the text and the model's tokenizer. |
| tok/s | Tokens generated per second during generation; this does not include the wait for the first token. |
| VRAM | The GPU's own memory. Very fast, but small: 8 GB and 12 GB on the two cards here. |
| Unified memory | On Apple chips the CPU and GPU share one pool of memory. The OS and other applications also need space in the laptop's 16 GB. |
| GPU share / spill | When a model doesn't fit in VRAM, Ollama puts the rest in normal system RAM and the CPU runs that part. "GPU share" is Ollama’s reported allocation ratio, not a direct count of layers or GPU work. |
| 7B, 14B, 32B | Billions of parameters, the numbers a model learned. Parameter count alone does not rank quality or determine runtime memory use. |
| Quantization (Q3, Q4, Q6, Q8) | Storing those numbers with fewer bits so the model is smaller. Q4 is about 4 bits each. Fewer bits generally reduce storage; the quality cost depends on the model and task. |
| MoE (mixture of experts) | A model split into many "expert" parts, where only a few run for each token. 30B-A3B means 30B parameters in total and about 3B active per token. |
| Context window | How much text the model can hold at once, prompt plus answer. Bigger windows need more memory. |
| KV cache | The model's working memory of the conversation so far. It grows with the context window. |
| Ollama | The free tool I used to download and run the models. |

## Follow-up: what I actually reran on 9 November

I set out to rerun all three machines. I completed the 7B and 14B tests on the 3080 and M3. I left the 2070 SUPER alone: it was holding a model for another workload, and this harness unloads a model before testing it. Changing that service just to get a score would make this a different experiment. There is **no new 2070 SUPER result** here.

For each completed condition I saved five short-prompt calls, five long-prompt calls and the same eight smoke tasks: 72 measured calls in total, plus warm-ups. Both machines used matching Qwen2.5 Q4_K_M manifest digests, temperature 0, seed 7 and a verified 2,048-token allocation context. This is one overnight session, not three separate days of repeatability. The 3080 ran 14B then 7B; the M3 ran 7B then 14B. Order was not randomized. The hosts were not run sequentially: their condition windows overlapped from 04:08:03 to 04:08:08 and from 04:12:34 to 04:12:48 UTC−05:00, verified from start/finish journal events. The same Mac ran local inference and timed the remote requests during those intervals. That adds competing work to the client-observed timings.

| Machine | Model | Short tok/s median (range) | Long tok/s median (range) | First output, short median s | Short request median s | Smoke tasks |
|:--|:--|--:|--:|--:|--:|:--|
| M3 16 GB | qwen2.5:14b | 9.3 (9.1–9.7) | 9.0 (8.8–9.4) | 0.163 | 18.160 | 7/8 |
| M3 16 GB | qwen2.5:7b | 18.8 (18.5–19.0) | 18.7 (17.8–19.1) | 0.064 | 6.851 | 7/8 |
| RTX 3080 12 GB | qwen2.5:14b | 71.9 (71.5–71.9) | 69.9 (69.4–70.0) | 0.266 | 2.329 | 7/8 |
| RTX 3080 12 GB | qwen2.5:7b | 125.5 (124.4–125.5) | 124.9 (124.4–125.0) | 0.253 | 1.247 | 7/8 |

The 3080 generated faster on both models. The Mac showed its first output sooner in these warm short-prompt calls, but took longer to finish. That is why I now keep waiting time, generation rate and total request time separate. The client ran on the Mac and reached the 3080 over the LAN, so this is an observation of the whole request path, not a hardware-only latency comparison. “First output” means the first nonempty streamed chunk observed by the client; it is not an exact server-side first-token timestamp.

Every condition scored 7/8. All four missed the train arrival-time question. None of the speed answers or task answers was marked cut off. A faster answer can still be wrong; these eight checks do not establish coding ability or a general quality ranking.

The model files matched, but the environments did not. The 3080 used Ollama 0.32.5; the M3 used 0.40.14 with one parallel request and one loaded model allowed in its temporary service. The Mac retained background applications and already had about 7.2 GiB of swap in use before inference. Both reported 100% GPU allocation share, which is an allocation report, not proof of equal memory behavior. The short answers also differed in length: 124 tokens for 7B on the 3080 versus 127 on the M3; 143–149 for 14B on the 3080 versus 166 on the M3. Same model and seed did not produce identical responses across these backends. Even the 3080’s 14B short-prompt repeats varied from 143 to 149 output tokens at the same requested seed and temperature.

Repeated prompts can reuse cache. I did not measure uncached prefill, wall energy, a new context sweep, or separate-day variation. I cannot use this partial rerun to explain the old 2070 SUPER slowdown or claim a result for AMD hardware I do not have.

The [derived evidence and per-call counters](evidence/2026-11-09/summary.json) record session IDs, model digests, source hashes, timings, output counts and hashes of the complete raw files. Full prompts and answers are preserved in the local review folder; they have not been published. The [evidence guide](EVIDENCE.md) explains where they are kept and what can be checked from the repository alone. These derived counters do not replace those originals. All four older raw files and their numeric tables are unchanged.

Afterwards, the benchmark models were unloaded from the 3080, its original server remained running and the GPU returned to its idle baseline. The temporary Mac service stopped and its API port closed. The 2070 SUPER's service model remained loaded. Downloaded model files were retained; no hardware settings, software versions or permanent services were changed. The Mac had about 7.2 GiB of swap in use immediately before its run and 13.7 GiB after the service stopped. I verified model unload and listener closure, but did not reset OS memory or background applications; those snapshots cannot isolate the cause of the swap increase.

## Summary

The remaining sections describe the original 2 and 5 November experiment. Its tables and conclusions are preserved as historical observations. The tables below are a record of those runs, not a buying guide. Read generation speed as the pace after generation begins. The old runs did not measure the wait before the answer starts, total task time, or wall power.

All reported ratios come from rounded saved values. Missing measurements stay missing. The [original raw results](results/) support the historical tables; the [measurement guide](MEASUREMENTS.md) explains the additional records used in the follow-up.

## Test setup

Three machines, one harness. The hardware details below come from my notes for each run; the JSONL rows record the GPU note and the Ollama version, not the full spec.

- **RTX 3080 12 GB** (gaming PC): Ryzen 9 3900X with 12 cores, 32 GB of DDR4-3200, Ollama 0.32.5. The run notes say “stock 390 W”; power draw was not recorded.
- **RTX 2070 SUPER 8 GB** (home server): 215 W power limit, Ryzen 5 5600GE (a 35 W part), Ollama 0.32.1 in a container capped at 4 CPU cores and 8 GB RAM plus 512 MB swap. Another process was holding about 0.4 GB of the card's VRAM during the run.
- **Apple M3 16 GB** (MacBook Pro 14-inch laptop): 8-core CPU (4 performance, 4 efficiency), 10-core GPU, 16 GB of unified memory shared by CPU and GPU, Ollama 0.40.14 from Homebrew with default settings, on AC power while I was lightly using it. Apple [publishes 100 GB/s memory bandwidth for this M3](https://support.apple.com/en-gb/117735); that's a spec, not something measured here.

The raw evidence is in [`results/`](results/), the harness in [`bench.py`](bench.py), and the task definitions in [`tasks.json`](tasks.json).

## Method

The harness requested temperature 0, seed 7, and up to 200 generated tokens for each speed prompt. A first request ensured each model was loaded; its API-reported load duration is listed separately. The harness used for these rows did not force an unload first, so the stored `cold_load_s` field is not a verified cold-start measurement. The harness default then makes three calls with a short hash-table prompt and three with a repeated filler prompt containing roughly 1.2–1.4 thousand input tokens. The run count is not stored in the JSONL. Under the three-call default, generation speed is the median of Ollama's per-call `eval_count / (eval_duration / 1e9)`; the duration is in nanoseconds. The tables use the latest timestamped row for each model on each GPU; reruns remain in the JSONL. Each of eight deterministic tasks was run once per saved speed row and checked by code. Ratios in this report are calculated from the rounded rates saved in the JSONL. The context sweep configured 2,048 through 32,768 tokens on the 3080, submitted a prompt occupying about 58–60% of each window, and made one timed generation call per setting.

“Allocation” below is Ollama's reported loaded size from `/api/ps`, in decimal GB. “GPU share” is its reported GPU-resident size divided by that loaded size, rounded to a whole percent. These are runtime allocation estimates, not direct measurements of weight size, layer placement, or GPU utilization. On the M3, 100% is Ollama's allocation report within a unified memory pool shared by CPU and GPU; it is not a discrete VRAM boundary or proof of exclusive GPU access. The main-table prompt-evaluation-rate field in the raw data is excluded: repeated identical prompts produced rates inconsistent with single-call long-prefill observations, and the JSONL lacks per-call timings needed to recover an uncached rate.

## Results

### RTX 3080 12 GB model comparison

Generation rates are medians under the harness's three-call default; the run count itself was not saved. First-request load duration and each task score come from single calls. “Long” denotes the roughly 1.2–1.4k-token prompt. Model names and values are taken from the latest row for each tag in [`results/*.jsonl`](results/).

| Model | Allocation GB | GPU share | Short tok/s | Long tok/s | Load s | Tasks |
|:--|--:|--:|--:|--:|--:|:--|
| mistral 7B | 5.0 | 100% | 145.3 | 139.6 | 24.2 | 7/8 |
| qwen3 14B | 9.6 | 100% | 78.3 | 76.4 | 13.5 | 8/8 |
| qwen2.5 14B Q4 | 9.5 | 100% | 71.7 | 69.7 | 11.3 | 7/8 |
| qwen2.5-coder 14B | 9.5 | 100% | 71.4 | 69.9 | 21.6 | 8/8 |
| gpt-oss 20B MoE | 14.0 | 74% | 62.9 | 63.5 | 24.1 | 8/8 |
| qwen2.5 14B Q3 | 7.9 | 100% | 62.0 | 60.7 | 11.8 | 8/8 |
| qwen3 30B-A3B instruct MoE | 19.2 | 55% | 42.6 | 48.3 | 24.7 | 8/8 |
| qwen3 30B-A3B thinking MoE | 19.2 | 55% | 41.4 | 42.2 | 23.5 | Not graded¹ |
| qwen2.5 14B Q6 | 13.1 | 80% | 14.1 | 13.8 | 15.6 | 7/8 |
| qwen2.5 14B Q8 | 16.7 | 63% | 6.2 | 5.9 | 19.1 | 7/8 |
| qwen3 32B dense | 21.6 | 48% | 3.1 | 3.2 | 22.6 | 8/8 |

¹ The thinking tag emits reasoning in its answer and cannot be fairly graded with these output-format checkers. Its stored 4/8 is omitted. The first three speed rows predate the explicit truncation flag, so their cutoff status is unknown.

### RTX 2070 SUPER 8 GB

The second run used the same harness and `card2` model group on 5 November 2026. The 14B rows report partial GPU allocation. The mistral allocation and GPU share were **not recorded**: the harness's `/api/ps` lookup missed the loaded `mistral:latest` name when the requested tag was `mistral`. That lookup is now fixed in `bench.py`; no value is inferred here.

| Model | Allocation GB | GPU share | Short tok/s | Long tok/s | Load s | Tasks |
|:--|--:|--:|--:|--:|--:|:--|
| mistral 7B | Not recorded | Not recorded | 77.6 | 75.8 | 4.0 | 7/8 |
| qwen2.5 7B | 4.7 | 100% | 75.7 | 75.7 | 6.8 | 7/8 |
| qwen2.5 14B Q3 | 8.3 | 77% | 1.1 | 1.1 | 18.1 | 8/8 |
| qwen2.5 14B Q4 | 10.0 | 64% | 0.7 | 0.7 | 24.9 | 7/8 |

### Apple M3 16 GB unified

The third run used the same `card2` model group on 5 November 2026. The laptop was in light interactive use, and its 100% GPU shares are Ollama's reports within shared unified memory. Allocation is not a measurement of bytes read per generated token.

| Model | Allocation GB | GPU share | Short tok/s | Long tok/s | Load s | Tasks |
|:--|--:|--:|--:|--:|--:|:--|
| mistral 7B | 5.0 | 100% | 19.2 | 18.1 | 5.9 | 7/8 |
| qwen2.5 7B | 4.8 | 100% | 19.1 | 18.9 | 3.9 | 7/8 |
| qwen2.5 14B Q3 | 7.9 | 100% | 7.8 | 7.8 | 7.8 | 7/8 |
| qwen2.5 14B Q4 | 9.5 | 100% | 8.0 | 8.0 | 8.4 | 7/8 |

### Head to head: shared tags across three machines

The short-generation rates below compare the latest row for each shared tag on each machine. The 2070 SUPER and M3 requests used `mistral`, which resolves to `mistral:latest` in Ollama; the 3080 row stores `mistral:latest`. Model digests were not saved, so matching tags do not prove identical model bytes. A dash means the tag was not measured on that machine.

| Model | RTX 3080 12 GB share | RTX 3080 12 GB tok/s | RTX 2070 SUPER 8 GB share | RTX 2070 SUPER 8 GB tok/s | Apple M3 16 GB unified share | Apple M3 16 GB unified tok/s |
|:--|--:|--:|--:|--:|--:|--:|
| mistral 7B | 100% | 145.3 | Not recorded | 77.6 | 100% | 19.2 |
| qwen2.5 7B | — | — | 100% | 75.7 | 100% | 19.1 |
| qwen2.5 14B Q3 | 100% | 62.0 | 77% | 1.1 | 100% | 7.8 |
| qwen2.5 14B Q4 | 100% | 71.7 | 64% | 0.7 | 100% | 8.0 |

### Context sweep

These are single-call measurements. Prompt tokens are the actual input counts recorded by Ollama. The MoE sweep used the *thinking* tag, which is distinct from the instruct model in the main comparison.

| Model | Window | Prompt tokens | Allocation GB | GPU share | Gen tok/s | API prompt tok/s² |
|:--|--:|--:|--:|--:|--:|--:|
| qwen2.5 14B Q4 | 2,048 | 1,221 | 9.1 | 100% | 70.6 | 2,583 |
| qwen2.5 14B Q4 | 8,192 | 4,786 | 10.3 | 100% | 66.4 | 2,388 |
| qwen2.5 14B Q4 | 16,384 | 9,560 | 12.4 | 85% | 18.4 | 1,731 |
| qwen2.5 14B Q4 | 32,768 | 19,108 | 15.7 | 66% | 3.8 | 1,113 |
| qwen3 30B-A3B thinking MoE | 2,048 | 1,202 | 19.0 | 56% | 51.8 | 907 |
| qwen3 30B-A3B thinking MoE | 8,192 | 4,767 | 19.6 | 53% | 47.4 | 1,563 |
| qwen3 30B-A3B thinking MoE | 16,384 | 9,541 | 20.4 | 51% | 44.0 | 1,701 |
| qwen3 30B-A3B thinking MoE | 32,768 | 19,089 | 22.1 | 48% | 36.9 | 1,560 |

² `prompt_eval_count / (prompt_eval_duration / 1e9)` from the one generate call at each setting. Cache state and raw prompt-evaluation durations were not saved; treat these as API-reported observations, not a validated uncached prefill benchmark.

## A closer look at the numbers

**Quantization ladder and the memory boundary on the 3080.** The Q4, Q6, and Q8 tags belong to the qwen2.5 14B instruct family. As reported allocation rises from 9.5 to 13.1 to 16.7 GB and GPU share falls from 100% to 80% to 63%, short-prompt generation falls from 71.7 to 14.1 to 6.2 tokens/s. The Q3 variant fits at 7.9 GB but generates at 62.0 tokens/s. Quantization changes compute as well as memory use, so these measurements show a sharp association with spill, not a clean causal estimate for memory alone.

**Context-window spill.** With the Q4 14B tag, the reported allocation crosses the 12 GB card boundary between the 8k and 16k settings. Shorter settings generated near 70 tokens/s; the 16k and 32k settings generated 18.4 and 3.8 tokens/s. Input length, KV-cache size, and GPU share all changed together. The MoE thinking tag remained partly outside GPU memory throughout its sweep and changed from 51.8 to 36.9 tokens/s across the four settings. This does not predict performance for arbitrary documents or the separate instruct tag.

**MoE and dense models near half fit.** The instruct 30B-A3B MoE and dense 32B tags have similar reported allocation shares (55% and 48%) but very different generation rates (42.6 and 3.1 tokens/s). MoE activates a subset of its parameters per token, which is a plausible reason for the difference. Architecture, quantization, model implementation, and generated output also differ; this dataset cannot assign a fraction of the 13.7× gap to any one cause.

**The 7B speed ratio resembles the published bandwidth ratio, with missing placement data.** The shared mistral tag generated at 145.3 versus 77.6 tokens/s, a **1.87×** 3080/2070S ratio. Memory bandwidth is how many gigabytes per second the chip can read from its memory; generating each token means reading most of the model's weights, so it often sets the speed. Published peak bandwidth is **912 GB/s** for [one RTX 3080 12 GB board's specification](https://www.gigabyte.com/uk/Graphics-Card/GV-N3080GAMING-OC-12GD/sp) and **448 GB/s** for the [RTX 2070 SUPER specification](https://www.nvidia.com/content/nvidiaGDC/gb/en_GB/geforce/graphics-cards/rtx-2070-super.html), a **2.04×** ratio. The JSONL does not record which 3080 board was tested; 912 GB/s is the 3080 12 GB's published figure, not a measured one. The 3080 row reports 100% GPU share, but the 2070S mistral row lacks a placement reading. This is a suggestive numerical comparison, not a verified in-VRAM bandwidth scaling result; different kernels, clocks, model bytes, and host load also matter. In these 2 and 5 November records, the fully allocated qwen2.5 7B on the 2070S has no matching 3080 run. The separate 9 November follow-up adds a 3080 measurement under a different protocol.

**Partial allocation behaves very differently across these systems.** The 3080's Q6 14B row reached **14.1 tok/s at 80%** reported GPU share, while the 2070S's Q3 14B row reached **1.1 tok/s at 77%**. These are different quantizations as well as different hosts. The 2070S Q4 row reached **0.7 tok/s at 64%**. The low rates recur in both short and long prompts, with narrow stored generation min/max ranges, so they do not look like a single mistimed call. The 2070S container's CPU and RAM limits, small swap, and shared VRAM could affect the spill path, but this run cannot isolate which factor caused the difference. Reported GPU share is not a measure of CPU work or host-memory traffic.

**The M3 changes the shared-tag comparison.** On qwen2.5 14B Q4, the M3 reported its 9.5 GB allocation at 100% GPU share and generated **8.0 tok/s**, versus **0.7 tok/s** at 64% share for the 10.0 GB allocation on the RTX 2070 SUPER: **11.4×**. This tests the observed rates for these complete systems, not the effect of unified memory alone. Conversely, the discrete cards were several times faster on the shared 7B tags: mistral was **4.0×** faster on the 2070 SUPER and **7.6×** faster on the 3080 than on the M3; qwen2.5 7B was **4.0×** faster on the 2070 SUPER than on the M3, with no 3080 row in those historical records. The M3's Q3 14B tag reported a smaller 7.9 GB allocation yet generated **7.8 tok/s**, slightly below Q4's **8.0 tok/s** at 9.5 GB. That ordering is unexpected from size alone and remains unexplained by these rows.

**Multiplying allocation by speed does not measure bandwidth.** As an illustrative size-times-rate calculation (not a bound), multiplying reported allocation by short-generation rate gives about **92–96 GB/s** for the M3's 4.8–5.0 GB 7B rows at about 19 tok/s, and **76 GB/s** for the 9.5 GB Q4 row at 8.0 tok/s. These products are at or below [Apple's published 100 GB/s M3 bandwidth](https://support.apple.com/en-gb/117735). Allocation includes more than weights and is not a measured number of bytes fetched per token; actual memory traffic, cache reuse, compute time, and competing system use are unknown. This compares numerical scales only; it neither validates the rates independently nor diagnoses a bandwidth limit.

## Limitations of these benchmarks

The three biggest caveats first: the machines differ in more than their memory, every result comes from one session, and the 8 tasks are far too few to rank how smart a model is. The details: these are three machine configurations without a controlled cross-machine trial. The 3080 host has a different CPU, more RAM, and Ollama 0.32.5; the 2070 SUPER host has a 4-core/8-GB container cap, Ollama 0.32.1, and another process using VRAM. The M3 used macOS and a different backend with newer Ollama 0.40.14; the laptop was in light interactive use. Host load and clocks were not logged. The 215 W limit is a setting, not measured power. The harness default gives three calls per speed condition, while each context point, first-request load duration, and quality task has one; the speed-run count was not saved in the raw rows. Model order was not randomized; there are no runs across days, confidence intervals, power measurements, or direct offload traces. The model tags are not pinned by digest, and the unqualified qwen2.5 14B tag's Q4 label comes from the project's ladder rather than a quantization field in the JSONL. The 2070 SUPER mistral row has no allocation reading. The filler prompt is repetitive and the eight tasks are too small to rank general usefulness. The first three 3080 speed rows do not record whether task answers hit their token caps. The prompt-rate issue described in Method prevents any claim about main-table long-prompt prefill speed.

## What I want local and frontier models to do

I want a hybrid workflow where I can work with sensitive material locally, then use frontier models for harder coding and research with context I deliberately choose to share. I’m trying to keep control of the handoff.

A practical example would be searching private notes locally, then turning a difficult coding problem into a small example without the private data before asking a frontier model for help. I would review that example myself. A local summary could still contain sensitive information; running the summarizer locally does not make its output safe to send.

These tests are only the local-inference part of that idea. I have not measured a complete hybrid workflow, validated automatic redaction, audited a routing application, or compared local and frontier models on the same coding tasks. Nothing in these results proves that data stays on the machine. That depends on the application, its tools, logging and network access as well as the model.

## What I would test with two Halos

I’m interested in AMD Ryzen AI Halo systems for local AI development. My current machines let me investigate smaller local models and memory limits. I want to find out whether more local capacity helps with useful tasks, and whether two systems are better used together or independently.

I would compare one Halo, two independent servers completing a fixed queue, and a two-Halo cluster. First I would use the same model and format where it fits, so I can measure the cost of distributing it. Then I would attempt a larger model that needs both units and check whether its answers justify the wait. That second comparison tests additional capacity and model usefulness, not hardware scaling for the same workload.

I would save per-request timings and outputs, use fixed coding and structured-data tasks with independent checks, repeat the key conditions on separate days, and document failures and recovery. I would measure wall energy only with suitable equipment. I have not tested AMD hardware and do not know its performance in advance.

The 9 November run improved model identification and per-call evidence on two of my current machines. The remaining baseline work is a non-overlapping run, a suitable window for the 2070 SUPER, better background-load control and separate-day repetitions. The [experiment plan](ROADMAP.md) keeps those gaps visible.

## Further reading

If you want to understand the "why" behind these numbers, these are the sources I'd start with:

- Ollama API: [`/api/ps`](https://docs.ollama.com/api/ps) is where "GPU share" (`size_vram`) comes from, and [`/api/generate`](https://docs.ollama.com/api/generate) documents the speed counters (`eval_count`, `eval_duration`).
- [Ollama FAQ](https://docs.ollama.com/faq): how Ollama splits a model between GPU and CPU, plus the flash-attention and KV-cache settings planned for the next run.
- [A guide to LLM inference and performance (Baseten)](https://www.baseten.co/blog/llm-transformer-inference-guide/): why generating text is usually limited by memory bandwidth, not raw compute, with the arithmetic worked out.
- [Mastering LLM techniques: inference optimization (NVIDIA)](https://developer.nvidia.com/blog/mastering-llm-techniques-inference-optimization/): prefill vs decode, the KV cache, and why decoding is memory-bound.
- [LLM inference performance engineering (Databricks)](https://www.databricks.com/blog/llm-inference-performance-engineering-best-practices): the same idea from another angle, plus time to first token and batching.
- [Mixture of Experts explained (Hugging Face)](https://huggingface.co/blog/moe): why a 30B MoE can run like a much smaller model.
- [GGUF and its quantization types (Hugging Face)](https://huggingface.co/docs/hub/gguf) and the [llama.cpp quantize guide](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md): what Q3_K_M, Q4_K_M, Q6_K and Q8_0 actually store, and what each costs in quality.
- [Qwen3 release notes](https://qwenlm.github.io/blog/qwen3/): the 30B-A3B MoE and the dense 32B used here, and the thinking mode that broke the graders.
- Hardware specs used for the bandwidth comparison: [Apple M3 MacBook Pro 14-inch](https://support.apple.com/en-gb/117735), [RTX 3080 12 GB](https://www.gigabyte.com/uk/Graphics-Card/GV-N3080GAMING-OC-12GD/sp), [RTX 2070 SUPER](https://www.nvidia.com/content/nvidiaGDC/gb/en_GB/geforce/graphics-cards/rtx-2070-super.html).

## License

This report, benchmark records and derived measurement summaries are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit the llmbench contributors, link to the source and license, and indicate changes; cite the repository commit and result filename for measurements. Code and configuration files use the MIT License. See the [project overview](README.md) for the code/data licensing split.
