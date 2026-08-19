# verify-row-lint-precision — Summary

Lane: high-risk
Confidence: high
Reason: `scripts/` hard gate — edits `check_verify_rows.py` (validation logic) and `run-tests.sh` (the gate's scope). Warn-tier under `ci-strict-gate.sh`, but it is gate precision, so it carries high-risk evidence.
Flags: weakening-validation, existing behavior
Affects: L1 verify-row lint — false-positive class + grandfathering scope
Input-type: harness fix
Route: tiny → direct fix (root cause fully diagnosed from a reproduced CI failure)
Escalate: no (options presented to the user; "fix checker + grandfather" chosen)

### Intent

CI `tests (ubuntu-latest)` failed on PR #207 (`simplify` → `main`) with 7 verify-row lint
violations. Root-cause them and make the lint report only real defects, without rewriting
already-shipped evidence records.

## What changed

Three fixes, no spec records touched.

1. **Verify table now terminates.** `check_summary_text` broke its scan only on a `#`
   heading. A `**Mutation-tested**` block is bold text, not a heading, so the scan bled
   past the Verify table into the following 2-column mutation table and reported its rows
   as malformed 5-column Verify rows. Once the header is seen, the first non-table line
   now ends the table.
2. **A quoted `|` is data, not a shell pipe.** Rule 1b fired on any `|` left in the
   command after unescaping, including one inside a Python string literal
   (`'|| true'`). New `_has_shell_pipe()` strips quoted spans first. Applied at both
   rule-1b sites (Verify rows and SC-table rows).
3. **Grandfathering survives a change of base ref.** `run-tests.sh` intersects the
   changed-file set with `git diff af869a9...HEAD` — the commit that revived the lint.

### Rationale

The lint was wired 2026-07-17 (`7034d30`) but did not actually compare anything until it
was revived 2026-08-08 (`af869a9`). All four offending specs landed inside that dead
window. `check_verify_rows.py` promises it "does not retroactively police already-shipped
specs", but the only mechanism enforcing that is the changed-file set — which means
"new" only while the base ref is the integration branch. On a release PR the base is
`main`, so all 56 accumulated specs look new and the promise silently breaks.

Of the 7 reported violations, 4 were checker defects (3 table-bleed, 1 quoted-pipe) and 3
were real rule-2 breaches in specs written before enforcement existed. Fixing the checker
addresses the false positives on their merits; the cutoff restores the documented
grandfathering for the 3 real ones rather than editing shipped evidence records.

### Alternatives considered

- **Rewrite the 3 real rows** (move `bash scripts/run-tests.sh` into prose). Rejected:
  edits shipped evidence records for specs that never had a chance to comply, and leaves
  the scoping bug to resurface on the next release PR.
- **Grandfather by `status: shipped`.** Rejected: `gh-129-run-state-e2e` and
  `strict-gate-scripts-warn` have a SUMMARY but no PLAN, so they carry no status marker —
  the mechanism would miss exactly the files it needed to cover.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| checker unit tests | `python3 -m pytest scripts/test_check_verify_rows.py -q --no-header --no-cov` | 0 | 21 passed (14 existing + 7 new regressions) | |
| lint syntax | `bash -n scripts/run-tests.sh` | 0 | | |
| false positives gone | `python3 scripts/check_verify_rows.py specs/strict-gate-scripts-warn/SUMMARY.md specs/durable-run-state/PLAN.md` | 0 | the 4 false positives no longer report | |
| real breaches still caught | `python3 scripts/check_verify_rows.py specs/gh-129-run-state-e2e/SUMMARY.md` | 1 | rule 2 still fires when the file is in scope | |

Mutation-tested, per `docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md`:

| Mutation | Result |
| --- | --- |
| revert the table-termination break | `test_scan_stops_at_end_of_verify_table` fails |
| revert `_QUOTED` stripping in `_has_shell_pipe` | 2 quoted-pipe tests fail |

Full suite (`bash scripts/run-tests.sh` → ALL GREEN, 575 pytest + every bash suite) run by
hand and by the CI `tests` job. Kept out of the table on purpose — the 60s cap is the rule
this very lint enforces.

### Not auto-verified

- That `af869a9` is the correct cutoff for every pre-existing spec — *traceability*. It is
  the commit that revived the lint, verified by its message and by re-running the filter,
  but no gate checks that a future spec cannot slip behind it.
- That the 3 grandfathered rule-2 rows are harmless — *traceability*. They are excluded
  from linting, not repaired; `ci-strict-gate.sh` would still time out if it ever re-ran
  those rows on a changed high-risk SUMMARY.
- That quoted-span stripping handles every shell quoting form — *truth* for the tested
  cases only. Nested/escaped-quote edge cases are not covered.

### Rollback

- `git revert <sha>` — restores the previous checker and the unfiltered changed set.

### Harness-Delta

- backlog → `compound`: a gate whose scope is derived from a base ref silently changes
  meaning when the base ref changes. The dead-lint window (2026-07-17 → 2026-08-08) is a
  second instance of "green can mean skipped" — the lint was wired and reported nothing.
