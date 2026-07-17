# evals/ — skill & workflow behavioral evals

Fixture-based **behavioral** evals for the harness's prompt-driven parts — distinct from the
deterministic code tests under `tests/` (shell hook/script suites) and `scripts/test_*.py`
(python unit tests). Those prove the *mechanical* pieces work with green checkmarks; the evals
here measure *skill judgment*, which is non-deterministic and scored against labeled ground truth.

| Split | What it evals | Contents |
|---|---|---|
| `skills/` | A single skill's output quality | `review-chain/` — `/correctness-review` + `/intent-review` catch-rate on planted defects |
| `workflow/` | A workflow stage's decision | `intake-classifier/` — `/feature-intake` lane/confidence/hard-gate accuracy |

## Shared model

Every eval here follows the same honesty discipline (see each subdir's `README.md`):

- **Labeled fixtures** — `request.md`/`intent.md` + `diff.patch` (where relevant) + `truth.md`.
- **Blind runs** — the skill is executed by a subagent that never sees `truth.md`.
- **Claim discipline** — a number is a claim about *these fixtures and this skill only*, not the
  full chain or real-world rate (`not_observed != absent`).
- **First run is the record** — fixtures are not re-run until they pass; misses are reported plainly.
- **Auto-score, manual-run** — scoring is deterministic and scripted (e.g.
  `scripts/score_intake_eval.py`); the LLM runs are triggered manually, not in CI.

## Not here

Deterministic tests live elsewhere and run in CI via `scripts/run-tests.sh`:
`tests/hooks/*.test.sh`, `tests/scripts/*.test.sh`, and `scripts/test_*.py`.
