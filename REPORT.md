# Local LLM inference on two NVIDIA cards and an Apple M3

Technical report · Measurements from 2 and 5 November 2026

## The short version

I'm not a lab. I wanted to know what normal hardware can actually do with free, open AI models, so I ran the same tests on three machines I already had: my gaming PC (RTX 3080, 12 GB), an older card in my home server (RTX 2070 SUPER, 8 GB) and my laptop (Apple M3, 16 GB). Here's what came out:

- **If the model fits in the GPU's memory it's fast. If it doesn't, it falls off a cliff.** The same 14B model ran at 71.7 tokens/s when it fit on the 3080, and 6.2 when a bigger version of it only 63% fit.
- **My laptop beat a real GPU, 11.4x.** The 14B didn't fit on the 8 GB card and crawled at 0.7 tokens/s. The M3 ran it at 8.0, most likely because its memory is shared, so the whole model fit. The report explains why I can't prove that's the only reason.
- **When everything fits, the real GPUs win easily.** The 3080 ran mistral 7B 7.6x faster than the laptop.
- **MoE models look like a cheat code for small cards.** A 30B mixture-of-experts model ran at 42.6 tokens/s with half of it spilled out of the GPU. A normal 32B, also about half spilled, ran at 3.1. The two models differ in more than MoE, so this is the next thing I want to test properly.
- **Long conversations eat memory too.** The 14B went from 66 tokens/s at an 8k context window to 3.8 at 32k, as the bigger window pushed more of it out of the GPU (the prompt got longer too, and each setting was one call).
- **The 8 small tasks are a sanity check, not an IQ test.** Every graded model got 7 or 8 out of 8.

So: memory size decides whether you can run a model at all, and once it fits, memory speed seems to set the pace. Everything below is the careful version, with every number tied to the raw data and every caveat spelled out.

### Words used in this report

| Word | What it means here |
|:--|:--|
| Token | A chunk of text the model reads or writes; its size depends on the text and the model's tokenizer. |
| tok/s | Tokens generated per second during generation; this does not include the wait for the first token. |
| VRAM | The GPU's own memory. Very fast, but small: 8 GB and 12 GB on the two cards here. |
| Unified memory | On Apple chips the CPU and GPU share one pool of memory. The OS and other applications also need space in the laptop's 16 GB. |
| GPU share / spill | When a model doesn't fit in VRAM, Ollama puts the rest in normal system RAM and the CPU runs that part. "GPU share" is how much Ollama says landed on the GPU. |
| 7B, 14B, 32B | Billions of parameters, the numbers a model learned. Parameter count alone does not rank quality or determine runtime memory use. |
| Quantization (Q3, Q4, Q6, Q8) | Storing those numbers with fewer bits so the model is smaller. Q4 is about 4 bits each. Fewer bits generally reduce storage; the quality cost depends on the model and task. |
| MoE (mixture of experts) | A model split into many "expert" parts, where only a few run for each token. 30B-A3B means 30B parameters in total and about 3B active per token. |
| Context window | How much text the model can hold at once, prompt plus answer. Bigger windows need more memory. |
| KV cache | The model's working memory of the conversation so far. It grows with the context window. |
| Ollama | The free tool I used to download and run the models. |

## Summary

- On the Apple M3 16 GB unified-memory laptop, qwen2.5 14B Q4 generated **8.0 tokens/s** at **100%** reported GPU share, **11.4×** the 2070 SUPER's 0.7 tokens/s at 64% share. The shared 7B tags ran about **4.0×** faster on the 2070 SUPER than on the M3, while mistral ran **7.6×** faster on the 3080. These are whole-system comparisons, not isolated memory effects.
- A Q4 14B model generated **71.7 tokens/s** with its 9.5 GB reported allocation fully in GPU memory. Q6 and Q8 variants of the same model generated **14.1** and **6.2 tokens/s** as their reported GPU shares fell to 80% and 63%.
- On the RTX 2070 SUPER 8 GB host, qwen2.5 14B Q3 generated **1.1 tokens/s** at **77%** reported GPU share; Q4 generated **0.7 tokens/s** at **64%**. Both tags ran much faster when fully resident on the RTX 3080 12 GB host. The hosts differ in CPU and memory limits, software version, and GPU load, so this is a system comparison.
- In a context sweep of the Q4 14B model, generation fell from **66.4 tokens/s** at an 8,192-token window (100% reported GPU allocation) to **18.4** at 16,384 (85%) and **3.8** at 32,768 (66%). These are one-call observations at each setting.
- A 30B-A3B mixture-of-experts (MoE) instruct model generated **42.6 tokens/s** at 55% reported GPU allocation. A dense 32B model generated **3.1 tokens/s** at 48%. The observed ratio is **13.7×**; the two model families differ in several ways, so it is not an isolated MoE effect.
- Eight small, code-checked tasks yielded scores between **7/8 and 8/8** for the graded models in the main table. Each task was attempted once in each selected row. These scores are a functional smoke test, not a general quality ranking.
- A separate, privately documented classifier trained on one car's telemetry reportedly reached **0.832 ROC-AUC** and **24.1% precision in the highest-risk 1% of held-out windows**. It predicts conditions preceding counter-recorded misfires, not a failing part; its reported CPU training time is about two minutes. These car results cannot be independently checked from this repository.

## Test setup

Three machines, one harness. The hardware details below come from my notes for each run; the JSONL rows record the GPU note and the Ollama version, not the full spec.

- **RTX 3080 12 GB** (gaming PC): Ryzen 9 3900X with 12 cores, 32 GB of DDR4-3200, Ollama 0.32.5. The run notes say “stock 390 W”; power draw was not recorded.
- **RTX 2070 SUPER 8 GB** (home server): 215 W power limit, Ryzen 5 5600GE (a 35 W part), Ollama 0.32.1 in a container capped at 4 CPU cores and 8 GB RAM plus 512 MB swap. Another process was holding about 0.4 GB of the card's VRAM during the run.
- **Apple M3 16 GB** (MacBook Pro 14-inch laptop): 8-core CPU (4 performance, 4 efficiency), 10-core GPU, 16 GB of unified memory shared by CPU and GPU, Ollama 0.40.14 from Homebrew with default settings, on AC power while I was lightly using it. Apple [publishes 100 GB/s memory bandwidth for this M3](https://support.apple.com/en-gb/117735); that's a spec, not something measured here.

The raw evidence is in [`results/`](results/), the harness in [`bench.py`](bench.py), and the task definitions in [`tasks.json`](tasks.json).

## Method

The harness requested temperature 0, seed 7, and up to 200 generated tokens for each speed prompt. A first request ensured each model was loaded; its API-reported load duration is listed separately. The harness does not force an unload first, so the stored `cold_load_s` field is not a verified cold-start measurement. The harness default then makes three calls with a short hash-table prompt and three with a repeated filler prompt containing roughly 1.2–1.4 thousand input tokens. The run count is not stored in the JSONL. Under the three-call default, generation speed is the median of Ollama's per-call `eval_count / (eval_duration / 1e9)`; the duration is in nanoseconds. The tables use the latest timestamped row for each model on each GPU; reruns remain in the JSONL. Each of eight deterministic tasks was run once per saved speed row and checked by code. Ratios in this report are calculated from the rounded rates saved in the JSONL. The context sweep configured 2,048 through 32,768 tokens on the 3080, submitted a prompt occupying about 58–60% of each window, and made one timed generation call per setting.

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

## Findings

**Quantization ladder and the memory boundary on the 3080.** The Q4, Q6, and Q8 tags belong to the qwen2.5 14B instruct family. As reported allocation rises from 9.5 to 13.1 to 16.7 GB and GPU share falls from 100% to 80% to 63%, short-prompt generation falls from 71.7 to 14.1 to 6.2 tokens/s. The Q3 variant fits at 7.9 GB but generates at 62.0 tokens/s. Quantization changes compute as well as memory use, so these measurements show a sharp association with spill, not a clean causal estimate for memory alone.

**Context-window spill.** With the Q4 14B tag, the reported allocation crosses the 12 GB card boundary between the 8k and 16k settings. Shorter settings generated near 70 tokens/s; the 16k and 32k settings generated 18.4 and 3.8 tokens/s. Input length, KV-cache size, and GPU share all changed together. The MoE thinking tag remained partly outside GPU memory throughout its sweep and changed from 51.8 to 36.9 tokens/s across the four settings. This does not predict performance for arbitrary documents or the separate instruct tag.

**MoE and dense models near half fit.** The instruct 30B-A3B MoE and dense 32B tags have similar reported allocation shares (55% and 48%) but very different generation rates (42.6 and 3.1 tokens/s). MoE activates a subset of its parameters per token, which is a plausible reason for the difference. Architecture, quantization, model implementation, and generated output also differ; this dataset cannot assign a fraction of the 13.7× gap to any one cause.

**The 7B speed ratio resembles the published bandwidth ratio, with missing placement data.** The shared mistral tag generated at 145.3 versus 77.6 tokens/s, a **1.87×** 3080/2070S ratio. Memory bandwidth is how many gigabytes per second the chip can read from its memory; generating each token means reading most of the model's weights, so it often sets the speed. Published peak bandwidth is **912 GB/s** for [one RTX 3080 12 GB board's specification](https://www.gigabyte.com/uk/Graphics-Card/GV-N3080GAMING-OC-12GD/sp) and **448 GB/s** for the [RTX 2070 SUPER specification](https://www.nvidia.com/content/nvidiaGDC/gb/en_GB/geforce/graphics-cards/rtx-2070-super.html), a **2.04×** ratio. The JSONL does not record which 3080 board was tested; 912 GB/s is the 3080 12 GB's published figure, not a measured one. The 3080 row reports 100% GPU share, but the 2070S mistral row lacks a placement reading. This is a suggestive numerical comparison, not a verified in-VRAM bandwidth scaling result; different kernels, clocks, model bytes, and host load also matter. The fully allocated qwen2.5 7B on the 2070S has no matching 3080 run.

**Partial allocation behaves very differently across these systems.** The 3080's Q6 14B row reached **14.1 tok/s at 80%** reported GPU share, while the 2070S's Q3 14B row reached **1.1 tok/s at 77%**. These are different quantizations as well as different hosts. The 2070S Q4 row reached **0.7 tok/s at 64%**. The low rates recur in both short and long prompts, with narrow stored generation min/max ranges, so they do not look like a single mistimed call. The 2070S container's CPU and RAM limits, small swap, and shared VRAM could affect the spill path, but this run cannot isolate which factor caused the difference. Reported GPU share is not a measure of CPU work or host-memory traffic.

**The M3 changes the shared-tag comparison.** On qwen2.5 14B Q4, the M3 reported its 9.5 GB allocation at 100% GPU share and generated **8.0 tok/s**, versus **0.7 tok/s** at 64% share for the 10.0 GB allocation on the RTX 2070 SUPER: **11.4×**. This tests the observed rates for these complete systems, not the effect of unified memory alone. Conversely, the discrete cards were several times faster on the shared 7B tags: mistral was **4.0×** faster on the 2070 SUPER and **7.6×** faster on the 3080 than on the M3; qwen2.5 7B was **4.0×** faster on the 2070 SUPER than on the M3, with no 3080 row. The M3's Q3 14B tag reported a smaller 7.9 GB allocation yet generated **7.8 tok/s**, slightly below Q4's **8.0 tok/s** at 9.5 GB. That ordering is unexpected from size alone and remains unexplained by these rows.

**Multiplying allocation by speed does not measure bandwidth.** As an illustrative size-times-rate calculation (not a bound), multiplying reported allocation by short-generation rate gives about **92–96 GB/s** for the M3's 4.8–5.0 GB 7B rows at about 19 tok/s, and **76 GB/s** for the 9.5 GB Q4 row at 8.0 tok/s. These products are at or below [Apple's published 100 GB/s M3 bandwidth](https://support.apple.com/en-gb/117735). Allocation includes more than weights and is not a measured number of bytes fetched per token; actual memory traffic, cache reuse, compute time, and competing system use are unknown. This compares numerical scales only; it neither validates the rates independently nor diagnoses a bandwidth limit.

## Limitations of these benchmarks

The three biggest caveats first: the machines differ in more than their memory, every result comes from one session, and the 8 tasks are far too few to rank how smart a model is. The details: these are three machine configurations without a controlled cross-machine trial. The 3080 host has a different CPU, more RAM, and Ollama 0.32.5; the 2070 SUPER host has a 4-core/8-GB container cap, Ollama 0.32.1, and another process using VRAM. The M3 used macOS and a different backend with newer Ollama 0.40.14; the laptop was in light interactive use. Host load and clocks were not logged. The 215 W limit is a setting, not measured power. The harness default gives three calls per speed condition, while each context point, first-request load duration, and quality task has one; the speed-run count was not saved in the raw rows. Model order was not randomized; there are no runs across days, confidence intervals, power measurements, or direct offload traces. The model tags are not pinned by digest, and the unqualified qwen2.5 14B tag's Q4 label comes from the project's ladder rather than a quantization field in the JSONL. The 2070 SUPER mistral row has no allocation reading. The filler prompt is repetitive and the eight tasks are too small to rank general usefulness. The first three 3080 speed rows do not record whether task answers hit their token caps. The prompt-rate issue described in Method prevents any claim about main-table long-prompt prefill speed.

## Training on the car data: what we did and its limits

The figures in this section are author-reported results from a separate private project. Its data, training script and metrics are not included here, so they cannot be verified against `results/*.jsonl` or reproduced with this harness. They are not evidence of GPU or LLM performance.

A separate project trained a scikit-learn classifier to predict whether the car's cumulative per-cylinder misfire counters would increment within the next two seconds, using the current engine state. At training time, the corpus held **843,299 samples from 376 drives** from one vehicle, sampled about every **274 ms**. Counter resets were removed. The split was by drive: **255 training** and **109 held-out** drives. Those add to 364. The training script excludes quarantined drives, drives without the misfire-counter channels, and drives with fewer than 40 usable samples; those filters are where the other 12 went (per-drive exclusion counts were not saved). The metrics file records **219,379 test windows**, **4,258 positive windows**, and a **1.94%** positive-window base rate. Overlapping two-second windows mean positive windows are not independent fault events; the project notes approximately **950** misfire events in the test drives.

Quick definitions: *held-out* drives were never shown to the model while training; *ROC-AUC* is how well it ranks risky moments above safe ones (0.5 is a coin flip, 1.0 is perfect); *average precision* is the same idea weighted toward the rare positives, where 0.019 would be guessing at this base rate. The full feature set achieved **0.832 ROC-AUC**, **0.119 average precision**, and **24.1% precision in its highest-risk 1% of held-out windows**. Removing knock channels left ROC-AUC at **0.832** and reduced top-1% precision to **22.4%**; rpm and throttle alone yielded **0.765 ROC-AUC** and **9.2%** top-1% precision. These are observations on one car's drive split, with labels derived from ECU counters rather than confirmed repairs or part failures. The top features indicate operating state, so the model predicts *when this engine tends to misfire*, not which component is failing. There is no evidence of cross-vehicle generalization.

Per-cylinder ignition timing has been broken since the logger's data path changed; gear, pedal, and lambda channels are only about **0.4%** populated. Those gaps limit fault attribution. The classifier trains on CPU in about **two minutes** and does not need a GPU. An LLM could help explain or summarize model outputs for a human, subject to factual checking; it is not the per-sample predictor or a substitute for mechanical diagnosis. Source: the car project's training script and its saved metrics (kept in a separate, private repository).

## What 128 GB of unified memory would let us test next

A 128 GB unified-memory system would permit controlled tests of larger model allocations and longer context windows without the same 8 GB or 12 GB GPU allocation boundaries. The M3 run shows that a 9.5 GB reported allocation can be fully allocated in a 16 GB shared pool while generating more slowly than the discrete cards on smaller tags; capacity and throughput need separate measurements. First, rerun the shared 7B and 14B tags on all three current machines with model digests, per-call GPU allocation capture, and the same Ollama version where possible. Repeat with the 2070 SUPER container's CPU/RAM limits and competing VRAM use varied one at a time; record CPU utilization, memory and swap traffic, GPU clocks, placement, end-to-end latency, and measured power. Log individual prompt and generation counts/durations, use an explicit cache protocol, repeat each point across sessions, and add real, shareable workloads with independent quality checks. Then use the larger memory pool to test whether capacity improves useful throughput and task completion; this report does not predict its speed, energy use, or suitability before measurement. The car classifier itself does not motivate the GPU request. The full plan, in order, is in [ROADMAP.md](ROADMAP.md).

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

This report and the results data are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit the llmbench contributors, link to the source and license, and indicate changes; cite the repository commit and result filename for measurements. See [README.md](README.md) for the code/data licensing split.
