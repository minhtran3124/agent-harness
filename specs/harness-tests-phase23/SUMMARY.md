# harness-tests-phase23 — Summary

Lane: high-risk
Confidence: high
Reason: Additive test infra only, but staged `tests/hooks/*.test.sh` paths trip risk-corroboration's `(^|/)hooks/` high-blast regex (the very false-positive fixed next) → lane raised to corroborate the gate honestly. Human directed the work ("until done").
Flags: none (corroboration false-positive on tests/hooks/)
Input-type: harness improvement

## What changed

Phase 2: contract tests for the seven remaining hooks (branch-guard, check-untracked-py,
ruff-on-edit, blast-radius-check, render-plan-on-write, scope-gate, state-breadcrumb) plus a
settings-wiring smoke test (settings.json ↔ .claude/settings.json derivation, every command
resolves to an executable). Phase 3: wired the repo's existing-but-unrun pytest suites
(`scripts/test_check_plan_format.py`, `skills/visual-planner/test_render_plan.py` — 85 tests)
into `run-tests.sh` as an L2 layer, and added feature-intake behavioral canaries
(`skills/feature-intake/tests/` — lane + confidence/escalation fixtures, run manually/nightly
since they are LLM-judged).

### Rationale

Phase 1 covered the 3 riskiest hooks; full coverage closes the gap. The two existing pytest
files were dead weight — nothing ran them — so wiring them in is pure recovered value. The
feature-intake canaries follow the xia2 document-as-test convention rather than forcing
flaky LLM eval into per-commit CI.

### Alternatives considered

- Skip the markdown canaries, attempt live `claude -p` assertions in CI — rejected: cost +
  non-determinism; xia2 already establishes the manual-canary pattern for prompt skills.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Full suite | `bash scripts/run-tests.sh` | 0 | 73 bash cases (1 xfail) + 85 python; ALL GREEN |
| New hook suites | `bash tests/hooks/{branch-guard,check-untracked-py,blast-radius-check,scope-gate,state-breadcrumb,ruff-on-edit,render-plan-on-write}.test.sh` | 0 | 29 cases |
| Wiring smoke | `bash tests/scripts/settings-wiring.test.sh` | 0 | derivation consistent |
| L2 recovered tests run | `run-tests.sh` L2 section | 0 | 85 passed, 1 skipped |

### Rollback

- `git revert 0532224` (additive files only)

### Harness-Delta

- backlog — same risk-corroboration `(^|/)hooks/` false-positive as phase 1; fixed in the
  immediately following commit, which flips this lane's need back to normal for future
  test-only additions.
