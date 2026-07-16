# hook-bug-fixes — Summary

Lane: high-risk
Confidence: high
Reason: Edits two hooks/* scripts (hard gate, high-blast) — authorized by the human's "until done" directive after both bugs were surfaced and flagged for approval. Both fixes are one-line, test-covered, and reversible.
Flags: none (hard gate: hooks/*)
Input-type: harness improvement

## What changed

Two bugs the phase-1/2 test suite exposed, both now fixed with the failing test flipped to a
passing regression guard:

1. `hooks/commit-quality-gate.sh:136` — `OUTPUT=$(pytest …) || true; RESULT=$?` captured the
   exit status of `true`, so a failing targeted test suite could never block a commit (same
   defect class fixed in auto-test, 78b28a0). Removed `|| true`.
2. `hooks/risk-corroboration.sh:71` — the high-blast path regex `(^|/)hooks/` false-positived
   on any `*/hooks/` subtree (notably `tests/hooks/`), needlessly forcing test-only commits to
   high-risk. Anchored to `^hooks/` + `(^|/)\.claude/hooks/` — matches the real harness hook
   dirs, not test files.

### Rationale

These are the two bugs the test investment was meant to catch; fixing them is what makes the
suite fully green (zero xfail) and removes the recurring lane inflation on test commits.
Neither changes documented behavior — both make the documented behavior actually hold.

### Alternatives considered

- Leave commit-gate as-is (tests are advisory anyway) — rejected: the hook's stated contract
  is to block on failure; silently never blocking is worse than not having the check.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Commit-gate blocks on failing test | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | 12 passed (was 11 + 1 xfail) |
| Corroboration regex precise | `bash tests/hooks/risk-corroboration.test.sh` | 0 | 12 passed incl. tests/hooks/ no-false-positive + .claude/hooks/ positive |
| Full suite, zero xfail | `bash scripts/run-tests.sh` | 0 | 73 bash + 85 python, ALL GREEN |
| Clone resync | `bash scripts/deploy-harness.sh` | 0 | fixed hooks active in .claude/ |

### Rollback

- `git revert 9e4d349` — reverts both one-line hook fixes + their test assertions together.

### Harness-Delta

- fix-direct — closes the two bugs surfaced by the phase-1/2 suite; the tests-as-regression
  pattern (xfail → real assertion on fix) is now demonstrated end to end.
