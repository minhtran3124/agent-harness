# Task-review A/B — Opus 5 vs Opus 5.5 (2026-10-02)

Same sitting, `scripts/run_task_review_eval.py --mode candidate` (the consolidated reviewer
prompt), Claude Code `2.1.287`, repo HEAD `8ee2609`, all 7 fixtures. Both arms ran at
`--effort medium` through a wrapper passed as `--claude` (the runner records `reasoning` as a
label only and does not pass effort itself).

| Collection | Model | Required labels found | Forbidden labels (FP) | Median elapsed per fixture | Median reviewer tokens |
| --- | --- | --- | --- | ---: | ---: |
| `opus-5-5-ab-old.json` | `claude-opus-5` (pre-#244 `task-reviewer`) | 7/7 fixtures | none | 10.02 s | 337 |
| `opus-5-5-ab-new.json` | `claude-opus-5-5` (post-#244 `task-reviewer`) | 7/7 fixtures | none | 8.79 s | 304 |

Scored with `score_task_review_eval.py`'s `labels()` against each `truth.json`. The script's
`--compare` gates do not apply as-is (they expect a baseline-vs-candidate prompt A/B in one
environment; here the prompt is fixed and the model differs).

**Result:** no quality regression; the new binding is slightly faster and cheaper. n = 1 per
fixture. The `transcript` paths inside the JSON point to the run's scratch directory and were not
kept; each record's `outputs` field holds the full reviewer text.
