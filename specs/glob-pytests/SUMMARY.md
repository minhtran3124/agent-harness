# glob-pytests — Summary

Lane: normal
Confidence: high
Reason: test-collection change only; adds coverage, removes none; no hook, gate, or settings logic touched; reversible by revert.
Flags: none
Affects: scripts/run-tests.sh, tests/scripts/codex-capability-probe.test.sh
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> now, make the review the workflow script of current harness. I saw have a lot of scripts and not sure some one of them block or make slow down performance or even no need it

> ok, let do it

Follow-up to the review (and PR #251): wire in the unit tests that nothing ran, and settle the
two `check_task_review_*` scripts that only shipped-spec Verify rows referenced.

## What changed

- `scripts/run-tests.sh` collects pytest files with
  `find scripts runtime skills -name 'test_*.py'` instead of a hand-written `PYTESTS` list.
  The list had drifted: `test_check_task_review_contract.py`, `test_check_task_review_adoption.py`,
  `test_score_intake_eval.py` and `test_run_task_review_eval.py` (18 tests) ran nowhere in CI.
  Collected tests: 781 → 799. `evals/` stays excluded — its fixture repos hold tests meant to fail.
- `check_task_review_contract.py` / `check_task_review_adoption.py` are kept: their tests invoke
  them, so they are now exercised on every run instead of being dead code.
- `tests/scripts/codex-capability-probe.test.sh` asserted the literal filename
  `scripts/test_check_codex_capabilities.py` appeared in `run-tests.sh`; it now asserts the file
  exists and that `run-tests.sh` collects `scripts/test_*.py`.

### Rationale

A hand list fails open: a new test file is silently never run. Collection by glob fails closed.

### Alternatives considered

- Append the 4 files to the hand list: rejected — fixes today's drift, not the cause.
- Delete the two `check_task_review_*` scripts: rejected — they pass, cost <1 s, and guard the
  task-reviewer contract that `subagent-driven-development` depends on.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| runner syntax | `bash -n scripts/run-tests.sh` | 0 | | |
| runner collects by glob | `grep -qF "find scripts runtime skills -name 'test_*.py'" scripts/run-tests.sh` | 0 | | |
| previously-unrun tests pass | `python3 -m pytest -q -p no:cacheprovider scripts/test_check_task_review_contract.py scripts/test_check_task_review_adoption.py scripts/test_score_intake_eval.py scripts/test_run_task_review_eval.py` | 0 | 18 passed | |
| probe suite accepts the glob | `bash tests/scripts/codex-capability-probe.test.sh` | 0 | 40 passed | |

The full suite (`scripts/run-tests.sh`, CI-equivalent with `HARNESS_SKIP_SUITES` set and the
Codex contract run separately) passed locally: ALL GREEN, 799 pytest passed.

### Advisory Findings

- none

### Intent Findings

- none

### Not auto-verified

- No other caller depended on the literal `PYTESTS` list — reached traceability via a repo grep for `PYTESTS` and the old filenames in `tests/` and `scripts/`.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
