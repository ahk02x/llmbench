# Check the evidence

The report covers two sets of measurements. I keep them separate because the collector changed between them.

## Original runs: 2 and 5 November

The [original raw records](results/) and [historical tables](RESULTS.md) cover all three machines. They remain unchanged. Those records did not retain model digests or individual speed-call timings, so the missing details cannot be reconstructed from them.

## Follow-up: 9 November

The [derived counters and timeline](evidence/2026-11-09/summary.json) include the individual speed-call counters, timings, model identities and hashes of the complete raw files. The [exact ladder configuration](evidence/2026-11-09/ladders.json) contains the added overnight group. Those files support recomputing the speed summaries and seeing the overlapping condition windows.

The [collector used for that run](evidence/2026-11-09/bench.py) is preserved byte-for-byte so its hash can be checked. The task file is still [tasks.json](tasks.json). The root `bench.py` now also records malformed null-field responses as failures; that later fix did not change the saved measurements. Use the root collector for new runs. The archived copy is for inspection and needs its original task and ladder inputs to run.

I retained the full responses, task records and allocation snapshots privately, outside this repository. They are not part of this public release. From the public files, you can recompute the speed summaries, but you cannot independently check the task answers or every allocation claim. The hashes identify the private originals; they do not prove their contents or replace access to them.

## What I publish and what I keep private

This repository contains the report, the original 2 and 5 November records, the derived 9 November counters and the exact ladder configuration for that follow-up. I have a separate local review bundle with the complete follow-up records. That bundle is not included here. Operational logs, private endpoints, credentials and review conversations are excluded from this release.

New schema-2 result files and raw-evidence folders are ignored by Git by default. They can contain verbatim prompts, answers and notes. I review files explicitly before deciding what to publish; an ignore rule alone is not a privacy check.

The HTML report opens directly in a browser and does not need a running inference service. On GitHub, use the Markdown report; GitHub shows HTML files as source rather than hosting them as a website.

The 9 November records cover 72 measured calls across four conditions, plus warm-ups. There is no new 2070 SUPER measurement. There is no AMD measurement, validated hybrid routing system, uncached-prefill test, wall-energy measurement or separate-day repeatability result in this dataset.

## Reuse

The report, benchmark records and derived measurement summaries use [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code and configuration files use the [MIT License](LICENSE). Publication is a separate action; these terms do not imply that private files are publicly available.
