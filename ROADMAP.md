# Roadmap

Where llmbench is, what's next, and the ideas I haven't decided on yet, in the order I actually plan to do them.

## What one week got done (2 to 5 November 2026)

I started with one question: what can a normal 12 GB gaming card really do with open models? A week later:

| PR | What it added |
|:--|:--|
| #1 | The harness (`bench.py`), 8 tasks checked by code, and the first run on the RTX 3080 |
| #2 | Quantization ladder, context sweep and MoE spill tests: a half-fitting 30B MoE ran 13.7x faster than a half-fitting dense 32B |
| #3 | The sandbox: a local chat page to talk to and compare the models |
| #4 | The technical report (`REPORT.md` and `report.html`), and I threw out a number that turned out to be wrong |
| #5 | Two more machines (RTX 2070 SUPER 8 GB and Apple M3 16 GB): the laptop beat the older GPU 11.4x on a model that didn't fit on the GPU |

That's 3 machines, 15 model tags and 4 quantization levels, all from one script that never logs into the box it's testing. GPT reviewed the PRs, and every number in the report was checked against the raw JSONL.

## Next: make the numbers harder to argue with (this week and next)

These fix the things the report's Limitations section admits to. Most of them are small harness changes.

1. **Merge the stack (#1 to #5)** once I've read it.
2. **Pre-public scrub. Done 5 Nov.** Results store a machine label (`rtx3080`, `rtx2070s`, `m3`), never a host address; your own host goes in the git-ignored `bench.local.json`. The private idea notes live outside git.
3. **Save what the report wishes it had.** Store the run count, every call's own timing, and the model digest (so "same tag" really means the same file). Use one Ollama version on all three machines.
4. **Rerun the shared models on all 3 machines** with those fixes, twice on different days. That turns "one afternoon" into "repeatable".
5. **Solve the 2070 SUPER mystery.** Why does a 14B at 77% on the GPU crawl at 1.1 tok/s there, when the 3080 does 14.1 at 80%? Change one thing at a time: the container CPU cap, the RAM cap, swap, the other process using VRAM.

## Then: push the card (the "my card finna die" part)

6. **Power sweep, 250 / 320 / 390 W.** Measure joules per token. My bet: almost no speed lost at 250 W. It also answers whether this hurts the card (it won't, it's way gentler than gaming).
7. **KV-cache quantization and flash attention.** Ollama can store the conversation memory at 8 bits (`OLLAMA_KV_CACHE_TYPE=q8_0`). That could push the 16k context cliff further out on the same card. One server setting on the PC, then rerun the context sweep.
8. **"Biggest model that's still usable" per machine.** Pick a bar (say 10 tok/s, faster than you can read) and find the largest model each machine clears. That's the chart normal people actually want.
9. **Time to first token.** How long you wait before the answer starts. For chat it matters more than tok/s.

## After that: is it actually useful?

Speed is half the story. These test if a local model can do real work.

10. **Real-workload replay**. Run my real kinds of tasks (summarize, classify, pull out fields, small code fixes) on the local models and grade them against a frontier model. Headline: "X% of my work could stay on a 12 GB card."
11. **Alert triage**. Can a 14B sort my home alert board the way the logged decisions did? The number that matters is how often it says "all clear" when it shouldn't.
12. **Long-context quality.** The `needle` task already hides one fact in filler text, but only at one short length. Repeat it at 8k, 16k and 32k, with the fact at the start, middle and end. A model that runs at 32k context but forgets the middle isn't really running at 32k.
13. **Cascade router**. Try local first and send it up to a frontier model only when the local one isn't sure. Measure what share stays local.

## Going public

14. **Write-up on ahk02x.dev.** A plain-English note in Writing plus a Projects card, done on a site branch and merged when I say so.
15. **Results page fed by the daily publish job.** Charts first, method linked, raw JSONL downloadable. No new infrastructure.
16. **Let other people run it.** `bench.py` already runs from anywhere over HTTP. Add a "send me your JSONL" path so other people's cards show up next to mine. That's what turns this from my homework into an actual benchmark.
17. **Hardware ask.** Only after the page has a few weeks of results on it, and after checking the gifts and outside-work rules. The pitch: 12 GB is the wall, and 128 GB of unified memory is the next experiment ([REPORT.md, last section](REPORT.md)).

## Ideas, not decided

- **Ollama vs llama.cpp** on the same card and model. How much is the hardware and how much is the software?
- **Speculative decoding.** A small "draft" model guesses ahead and the big one checks it. That could make the 3080's 14B noticeably faster.
- **"Will it fit?" calculator.** Enter your VRAM and a model and get back whether it fits and a rough tok/s, built from these measurements, not marketing numbers. Good traffic page.
- **Same test, used cards.** Old 3060 12 GB and 3090 24 GB cards are cheap. Is a used 24 GB card the best value for local AI?
- **The car data as a real workload.** A local model explaining the misfire classifier's output in plain words, checked against the database by code.
- **Nemesis**. A frontier model tries to trick a local model that's guarding something. Count the rounds it holds.

## Rules that don't change

- Same prompts, temperature 0, fixed seed, load time never mixed into tok/s.
- Tasks are graded by code, not by another model, unless the page says so clearly.
- A number I can't back up with the raw data gets dropped, not rounded into something nicer.
- Nothing public names private tools, employers, LAN addresses or the gated frontier models.
- Don't fine-tune on frontier-model outputs without reading their terms first.
