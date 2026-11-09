# llmbench

I’m trying to work out what AI I can run on hardware I already own, what I can trust it to do, and when I still need a more capable model.

I started with an RTX 3080, an RTX 2070 SUPER and an Apple M3. I kept the measurements and the wrong answers. The useful question for me is whether a model can finish a task correctly in a reasonable amount of time.

**[Read the benchmark report](REPORT.md)** · [Check the evidence](EVIDENCE.md) · [See what I want to test next](ROADMAP.md)

## What I found

In the 9 November follow-up, I tested matching Qwen2.5 7B and 14B model files on the 3080 and M3. The short-prompt generation medians were:

| Machine | 7B | 14B |
|:--|--:|--:|
| RTX 3080 12 GB | 125.5 tokens/s | 71.9 tokens/s |
| Apple M3 16 GB | 18.8 tokens/s | 9.3 tokens/s |

Each condition had five calls per speed prompt and eight basic task checks. All four scored 7/8 and missed the same train-time question. Faster output did not make that answer correct.

These are observations from one overnight session. Software versions differed, the Mac had background load and swap in use, and parts of the runs overlapped on the Mac that also timed the remote requests. I skipped the 2070 SUPER to avoid interrupting an existing workload. This is not an isolated hardware comparison or a general model-quality ranking.

The earlier 2 and 5 November runs cover all three machines. Their [original tables](RESULTS.md) and [raw records](results/) are preserved separately. Those runs did not save model digests or individual speed-call records, so they support fewer checks than the follow-up.

## Why I’m doing this

I’m exploring a hybrid AI workflow. I want to handle sensitive material locally, and use frontier models for the harder coding and research work when I choose to share the necessary context.

For example, a local model could help me search or summarize private notes. For a harder coding question, I could send a small, reviewed example with the private details removed to a frontier model. I want control over what leaves my machine.

That is the direction I’m working toward. This benchmark measures local inference speed and a small set of tasks. It does not test a cloud-routing system, prove that sensitive information cannot leave, or show that a local model can reliably remove every private detail. A local model is only one part of privacy: the application, tools, logs and network behavior matter too. I would still need to check any material before sharing it externally.

## Why two Halos would be useful

I’m interested in AMD Ryzen AI Halo systems for local AI development. I want to compare one Halo, two working independently, and two sharing a model. The second unit lets me test whether clustering earns its extra complexity, or whether splitting the work between two servers is more useful.

I would first compare the same model where it fits, then attempt a larger model that needs both systems. I have not tested Halo hardware, and these NVIDIA and Apple results do not predict its performance. The [next-test plan](ROADMAP.md) explains the comparisons and the gaps I still need to close.

## Quick start

To run the benchmark yourself, follow the [setup and usage guide](USAGE.md). The [measurement guide](MEASUREMENTS.md) explains the fields and their limits; the [contribution guide](CONTRIBUTING.md) explains how to share a run.

Use the “Read the benchmark report” link above for GitHub’s readable Markdown view. For the offline HTML edition, clone or download this repository and open `report.html` in a browser. GitHub displays HTML files as source; this repository does not currently provide a hosted report page.

## How I handle the evidence

I keep raw originals, failed attempts and wrong answers. New runs get their own records. I distinguish generation speed from the wait for an answer, and reported allocation from measured hardware utilization. The eight tasks are basic checks, not evidence that a model can safely do someone’s job.

Private network details, credentials and review conversations do not belong in the reader-facing files. The [evidence guide](EVIDENCE.md) explains what is included and what remains private. Running an experiment does not automatically publish its results.

## License and attribution

Code and configuration files, including `ladders.json`, use the [MIT License](LICENSE). The report, historical tables, benchmark records and derived measurement summaries use [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). These terms describe reuse; they do not mean that private files have been published.

When reusing the licensed report or results, credit the llmbench contributors, link to the source and license, and indicate changes. Cite the commit and result filename so the measurement can be found. Model weights retain their respective licenses.
