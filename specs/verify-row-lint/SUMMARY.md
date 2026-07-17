# verify-row-lint — Summary

Lane: high-risk
Confidence: high
Reason: Edits scripts/run-tests.sh (CI entrypoint / contract) and adds an enforced lint that can block PRs — high-risk by judgment. Not a strict-gate hard-gate path (no settings/hooks/render_plan/templates), so ci-strict-gate does not mechanically fire; lane declared on judgment. Direction unambiguous (user: build the verify-row lint from the backlog).
Flags: high-blast (run-tests.sh CI contract)
Affects: scripts/check_verify_rows.py (new lint), scripts/run-tests.sh (wiring), improvement-backlog ratchet row
Input-type: harness improvement

### Intent

"build the verify-row lint from the backlog" — mechanize the critical /compound learning `verify-row-must-be-pipe-free-and-under-60s`: a lint that fails a SUMMARY `### Verify` command cell containing a pipe or a full-suite/build invocation.

### What changed

New `scripts/check_verify_rows.py` — parses each `### Verify` table (escape-aware split on the delimiter, like verify_summary) and flags: (1) an unescaped pipe that splits a row into the wrong column count; (2) an escaped/surviving pipe in the command; (3) a full-suite/build invocation (`run-tests.sh` when EXECUTED, `make … test`, `tox`, "full suite"). Wired into `run-tests.sh` L1 and into PYTESTS. Scope is deliberately **changed-SUMMARYs-only** (`git diff origin/main -- specs/*/SUMMARY.md`): it lints new/edited rows and grandfathers the 36 shipped specs that already carry full-suite rows — matching ci-strict-gate's changed-SUMMARY model. 9-case pytest incl. the grep-argument false-positive guard (a command greping *for* run-tests.sh is not flagged).

### Rationale

This closes the ratchet from the compound doc: the mistake was hit 7× in one session (6 pipe cell-splits + 1 strict-gate timeout). Catching it at `run-tests.sh` L1 fails fast at authoring time instead of after a blocked CI strict gate. Changed-files scope avoids a retroactive failure on 36 shipped SUMMARYs (churn with no benefit) while still fencing every new one.

### Alternatives considered

- Scan all specs/*/SUMMARY.md (as the backlog row suggested): rejected — 36 shipped specs carry full-suite rows; whole-repo enforcement would red CI immediately for zero benefit (those specs are done).
- Fix all 36 legacy rows: rejected — large unrelated churn.
- Fold into ci-strict-gate only: rejected — that fires only on hard-gate diffs; a docs-only SUMMARY edit would slip through. run-tests.sh L1 runs on every PR.

### Deviations

- Rule 3 — deviated from the backlog's suggested "scan every specs/*/SUMMARY.md" wiring to changed-files-only, for the retroactive-failure reason above. Recorded here.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| lint pytest (9 cases incl. FP guard) | `python3 -m pytest scripts/test_check_verify_rows.py -q --no-header -p no:cacheprovider` | 0 | detector proven |
| flags a real full-suite Verify row | `python3 scripts/check_verify_rows.py specs/phase2-wave2/SUMMARY.md` | 1 | legacy dogfood |
| passes a clean SUMMARY | `python3 scripts/check_verify_rows.py specs/techstacks-decoupling/SUMMARY.md` | 0 | pipe-free + no full-suite |
| grep-argument run-tests.sh NOT flagged (FP guard) | `python3 -m pytest scripts/test_check_verify_rows.py -k grep_argument -q --no-header -p no:cacheprovider` | 0 | covered by pytest |
| wired into run-tests.sh (PYTESTS + L1) | `bash -c 'n=$(grep -c check_verify_rows scripts/run-tests.sh); test "$n" -ge 2'` | 0 | test + L1 block |
| this SUMMARY is itself clean (dogfood) | `python3 scripts/check_verify_rows.py specs/verify-row-lint/SUMMARY.md` | 0 | eats its own dog food |

### Rollback

- `git revert <commit>` — removes the lint, the wiring, and the test; run-tests.sh returns to its prior L1. No data/schema migration; additive check only.

### Harness-Delta

- 36 shipped SUMMARYs carry full-suite Verify rows (latent — they'd time out only if re-verified under a strict gate). Grandfathered by the changed-files scope; a future cleanup could sweep them, but it is not worth the churn now.
