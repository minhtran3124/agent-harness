# p3-hook-fixes — Summary

Lane: high-risk
Confidence: high
Reason: Touches hooks/* (hard-gate high-blast file) — gate confirmed by the human ("continue for P3" after the gate was surfaced); scope is a one-line bug fix plus a recorded no-change decision.
Flags: none (hard gate only)
Input-type: harness improvement

## What changed

Fixed `hooks/auto-test-on-change.sh`: `OUTPUT=$(pytest …) || true; RESULT=$?` captured the
exit status of `true`, so the hook reported `[AUTO-TEST] PASSED` even when pytest failed.
Removed the `|| true` (the script has no `set -e`; the guard was both unnecessary and the
bug). Decision recorded: keep `risk-corroboration.sh`'s warn-on-missing-Lane default.

### Rationale

Verified live before fixing: a `def test_boom(): assert False` file run through the hook
printed PASSED. The audit's original claim (line-16 `||` vs `&&`) was disproven by truth
table + live test — the skip gate is correct De Morgan form; the real defect was the
status capture. Hook stays dormant (not registered) — unchanged.

### Decision — risk-corroboration strict default

KEEP the warn-on-missing-Lane default (no code change). Why: the hook header documents it
as a deliberate choice for fresh installs (nothing to corroborate against; a hard block on
first manual commit teaches users to delete the hook); P1 already aligned the docs with
this behavior; `RISK_CORROBORATION_STRICT=1` remains the per-repo hardening knob. The
declared-lane-below-high-risk case still blocks — that is the load-bearing promise.

### Alternatives considered

- Flip strict to default with an opt-out env — rejected for hostile first-contact UX in
  consuming projects; revisit if the trust ledger shows missing-Lane commits recurring.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Line-16 gate truth table | 4-case bash check (tests-py / app-py / tests-txt / conftest) | 0 | gate correct — audit claim disproven |
| Bug reproduced pre-fix | failing test via hook → printed `PASSED` | 0 | confirms `\|\| true` masked status |
| Failing test reports FAILED | hook + venv (pytest 9 + pytest-cov), `assert False` | 0 | `FAILED (exit code 1)` |
| Passing test reports PASSED | hook + venv, `assert True` | 0 | `PASSED` |
| Non-test file silent skip | `app/main.py` via hook | 0 | no output |
| Syntax | `bash -n hooks/auto-test-on-change.sh` | 0 | |

Environment notes from testing (not fixed — out of approved scope, hook is dormant):
the hook needs `python` on PATH (exit 127 otherwise) and pytest-cov for `--no-cov`
(usage-error 4 otherwise). Real FastAPI targets have both; flag if ever registering
the hook in a non-Python or non-pytest-cov repo.

### Rollback

- `git revert 78b28a0` (single hook file; hook is dormant — no registration change)

### Harness-Delta

- fix-direct — the audit subagent's line-16 finding was wrong; adversarial verification of
  findings before reporting (already standard in /correctness-review) would have caught it.
