# intake-classifier-eval — Summary

Lane: normal
Confidence: high
Reason: New additive eval subsystem under evals/ + a deterministic scorer script with its own unit tests; no auth/authz/data-loss/public-contract/high-blast file touched (scripts/ scorer is not a high-blast path).
Flags: multi-domain
Affects: none
Input-type: harness improvement
Route: /writing-plans (>3 steps / >2 files) -> direct build (additive, reversible) -> auto-score run
Escalate: no

### Intent

> "Tôi muốn build evalution cho skill và cả workflow để chứng mình nó hoạt động đúng."
> Scoped via clarification to: **feature-intake classifier eval first**, runner style
> **auto-score + manual-run** (deterministic scorer script; the skill is run via blind
> subagents when triggered, not in CI). Extend the review-chain fixture/claim-discipline
> pattern to the intake router.

## What changed

Added `evals/workflow/intake-classifier/` — a labeled-fixture eval that measures whether
`/feature-intake` assigns the correct **lane / confidence / hard-gate** for a request.
Each fixture is `{request.md, truth.md}`; a deterministic scorer (`scripts/score_intake_eval.py`,
unit-tested) parses the classification a blind subagent emitted and scores lane accuracy,
hard-gate-respect rate, and confidence match against `truth.md`. Ran one blind baseline.

### Rationale

feature-intake is the router the whole workflow hinges on and its output (10-flag checklist +
hard gates → lane) is the most mechanically-checkable skill, so it yields a real accuracy number
— unlike pure LLM-judgment skills. Auto-score/manual-run mirrors the existing review-chain
honesty model (blind runs, claim discipline, first-run-is-the-record) without paying token cost
on every CI run.

### Alternatives considered

- Full-auto CI-gated eval. Rejected (for now): running an LLM skill on every CI is token-costly and non-deterministic → flaky gate.
- Start with review-chain expansion or end-to-end workflow eval. Deferred: intake is the highest-leverage, most measurable single target; the other two build on the same fixture/scorer pattern later.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| scorer unit tests | `python3 -m pytest scripts/test_score_intake_eval.py -q --no-header --no-cov` | 0 | deterministic scorer logic |
| scorer runs on baseline | `python3 scripts/score_intake_eval.py --run evals/workflow/intake-classifier/results/baseline` | 0 | emits scorecard, exit 0 |

### Rollback

- `git revert <sha>` (fully additive — new dir + two scripts; no existing file behavior changed)

### Harness-Delta

- backlog — `scripts/test_score_intake_eval.py` is run via the Verify row + manually, but is **not**
  wired into `scripts/run-tests.sh` `PYTESTS` (so CI does not run it yet). Wiring it in edits a
  **high-blast file** (`run-tests.sh` is on the hard-gate list) → that step needs a **high-risk**
  lane + human confirmation and is intentionally deferred out of this normal-lane spec. Follow-up:
  add the filename to `PYTESTS` under high-risk ceremony.
