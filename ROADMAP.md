# What I want to test next

The first runs were on 2 and 5 November 2026. They gave me useful questions, but not a controlled answer to all of them.

## First rerun complete on two machines

The revised harness saves model digests, per-call timings, full responses, session IDs, source hashes and failures. Context settings now repeat too. Offline fixtures check the collection path. The original result files remain unchanged. The 9 November follow-up completed matching 7B/14B conditions on the 3080 and M3; the 2070 SUPER and separate-day repetitions remain outstanding.

## First, repeat the comparison properly

Run shared models on the three machines with matching digests and settings. Save five calls per condition on three different days. Run host conditions sequentially so local inference does not overlap the shared controller’s remote measurements. Rotate model order and record background load. Match software versions where possible and explain where they differ. Compare both the wait for the answer and its generation pace.

## Then, explain the slow 2070 SUPER result

Change one thing at a time: competing VRAM use, container CPU cap, RAM cap and swap. The old run changed too many things at once to blame only the card's memory.

## Then, ask whether the answer was useful

Build a frozen set of structured extraction, incident-summary and small code-fix tasks with independent expected outcomes. Include missing evidence and contradictory inputs. Measure correctness, false reassurance, retries and time to completion. The current eight smoke tasks are not enough, and another model's preference is not ground truth.

## Larger memory and two machines

A Halo evaluation would extend the same investigation: one unit, two independent servers, and two units sharing a model. First compare the same model and format where it fits. Then measure what a larger model adds to task completion. A model loading successfully is not evidence that it is a good daily tool.

## The hybrid workflow I want to build

Keep sensitive source material local, and use frontier models for harder coding and research with explicitly reviewed context. Test the routing application, tools, logs and network behavior before making a privacy claim. Local inference and automatic redaction are not proof that a payload is safe to share. This workflow has not been evaluated by the benchmark.

## Experiments after that

- Separate uncached prefill from prefix-cache reuse with a verified protocol.
- Measure wall energy with a meter; a configured wattage is not measured consumption.
- Capture continuous host load, clocks and allocation rather than only post-call snapshots.
- Hold input length fixed while varying the context limit, then vary input length separately.
- Compare supported backends with the same model bytes and disclose implementation differences.

## Publication

Keep raw originals and failed attempts. Review new sessions before including them in a comparison. Publish the method, limitations and usable reproduction steps with every claim. The current report generator deliberately keeps the historical experiment separate from schema 2 sessions.

Keep private infrastructure, employers, credentials and review conversations out of public files. Publication and outreach are separate decisions from running the experiment.
