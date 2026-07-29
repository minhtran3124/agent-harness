# Task-review A/B comparison

Environment is pinned across runs: `claude-fable-5`, Claude Code `2.1.220`, standard reasoning.
All raw outputs are preserved under `results/transcripts/`; fixture truth files remained outside
every reviewer prompt.

| Collection | Status | Reviewer dispatches | Median elapsed per fixture |
| --- | --- | ---: | ---: |
| `baseline.json` | dual-review baseline | 14 | 24.84s |
| `candidate.json` | rejected iteration 1 | 7 | 14.60s |
| `candidate-v2.json` | accepted iteration 2 | 7 | 13.32s |

Iteration 1 was rejected for a false-positive/unknown treatment of the Minor-only fixture and is
preserved with its hypothesis in `candidate-iteration-1.md`. Iteration 2 adds only an explicit
fixture-evidence boundary. It passes quality first (all required defects detected, no forbidden
verdict), then efficiency (one task-review dispatch per fixture and no median runtime regression).
