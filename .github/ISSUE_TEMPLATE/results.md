---
name: Submit my results
about: Share a results PR and the machine details needed to interpret it
title: ''
---

Please submit the generated summaries and event journal by pull request under `results/<label>-<date>-v2.jsonl` and `results/<label>-<date>-v2.events.jsonl`; link the PR here. See [CONTRIBUTING.md](../../CONTRIBUTING.md) for the commands and submission steps. If you need help opening a PR, say where you got stuck.

## Result files

- Results PR:
- Summary and event JSONL filenames (context and speed modes use the same pair):
- Repository commit and run date:

## Machine and software

- GPU/SoC model and GPU count:
- VRAM per GPU, or total unified memory:
- CPU and system RAM:
- Container/VM CPU, RAM and swap limits (if any):
- OS and version:
- GPU driver version (or not applicable):
- Ollama server version:
- Power limit in watts (stock/changed/unknown), laptop power mode and AC/battery:
- Background CPU/GPU use and VRAM already occupied:

## Run

Paste the exact command below, using localhost in place of any private server address.

```sh

```

- Model tags, manifest digests, session IDs, and per-condition run count:
- Non-default Ollama settings or changes to the harness, model groups or tasks:
- Were models already loaded?
- Failed/skipped models or context windows, interruptions and error messages:
- Any identifying metadata redacted before submission:

## Before submitting

- [ ] I followed CONTRIBUTING.md to stage only the reviewed result files; new runs are ignored by Git by default.
- [ ] I included the raw JSONL and all completed rows, without changing measurements.
- [ ] I checked labels, notes and logs for private addresses, names, employer details and credentials.
- [ ] I supplied the machine/run details above, or marked unavailable values as unknown.
- [ ] I agree to publish these results under CC BY 4.0 as described in CONTRIBUTING.md.
