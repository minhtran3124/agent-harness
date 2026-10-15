# Intent: red/green check applies to every bug-fix Input-type spelling

Author: Minh Tran
Status: approved

## Problem

`scripts/verify_summary.py` `_red_green_issue` applies the red/green check only when the
`Input-type:` header, trimmed and lower-cased, equals exactly `bug fix`. A bug-fix SUMMARY that
writes the value another way skips the check silently, even under `REQUIRE_RED_TEST=1`, and gets
no warning:

- `Input-type: bug-fix`
- `Input-type: bugfix`
- `Input-type: bug fix (harness)`

The gate fails open on the very runs it exists for. Existing SUMMARYs already use free-form
`Input-type` values (`harness fix`, `docs correction`, `plan execution (…)`,
`Harness improvement`). `_resolve_lane` in the same file uses a prefix match, not exact equality.

## Proposed outcome

A bug-fix SUMMARY gets the red/green check whether its `Input-type` is written `bug fix`,
`bug-fix`, `bugfix`, or `bug fix` followed by extra text. Values that are not bug fixes are
unaffected.

## Affected users and systems

- `scripts/verify_summary.py` (`_red_green_issue`) and its tests in
  `scripts/test_verify_summary.py`.
- Agents and consumer repos that write a bug-fix SUMMARY.

## Constraints

- Advisory by default. Nothing that passes today may start to block unless `REQUIRE_RED_TEST=1`
  is set.
- Every existing `specs/*/SUMMARY.md` whose `Input-type` is not a bug fix keeps the same
  `verify_summary.py` result.
- Do not match `bug fixes` or other words that only start with `bug` (assumed).

## Out of scope

- Normalising every other `Input-type` value.
- The other advisory findings from PR #301.

## Open questions

- Q1: Match a leading `bug[ -]?fix` token, the way `_resolve_lane` matches the lane, or warn when
  the value is not one of the template's options? (assumed: the token match)

## What success looks like

- `verify_summary.py --lane` on a SUMMARY with `Input-type: bug-fix`, `bugfix` or
  `bug fix (harness)` and no red/green rows prints the red/green warning, and exits 1 under
  `REQUIRE_RED_TEST=1`.
- The same command on a SUMMARY with `Input-type: harness fix` or `bug fixes` prints no red/green
  message.
- `scripts/test_verify_summary.py` passes.

## Original request

/feature-intake https://github.com/minhtran3124/agent-harness/issues/302

Issue #302 — "verify_summary: Input-type bug-fix or bugfix skips the red/green check silently":

Follow-up from PR #301 (E5, failing-test-first). This is an advisory correctness finding (score 50), recorded in `specs/failing-test-first/SUMMARY.md` under `### Advisory Findings`.

## Problem

`scripts/verify_summary.py` `_red_green_issue` applies the red/green check only when the `Input-type:` header, trimmed and lower-cased, equals exactly `bug fix`. A bug-fix SUMMARY that writes the value another way skips the check silently, even under `REQUIRE_RED_TEST=1`, and gets no warning:

- `Input-type: bug-fix`
- `Input-type: bugfix`
- `Input-type: bug fix (harness)`

The gate fails open on the very runs it exists for. Existing SUMMARYs already use free-form `Input-type` values (`grep -rhn '^Input-type:' specs/*/SUMMARY.md`: `harness fix`, `docs correction`, `plan execution (…)`, `Harness improvement`). `_resolve_lane` in the same file uses a prefix match, not exact equality.

## Proposed outcome

A bug-fix SUMMARY gets the red/green check whether its `Input-type` is written `bug fix`, `bug-fix`, `bugfix`, or `bug fix` followed by extra text. Values that are not bug fixes are unaffected.

## Affected users and systems

- `scripts/verify_summary.py` (`_red_green_issue`) and its tests in `scripts/test_verify_summary.py`.
- Agents and consumer repos that write a bug-fix SUMMARY.

## Constraints

- Advisory by default. Nothing that passes today may start to block unless `REQUIRE_RED_TEST=1` is set.
- Every existing `specs/*/SUMMARY.md` whose `Input-type` is not a bug fix keeps the same `verify_summary.py` result.
- Do not match `bug fixes` or other words that only start with `bug` (assumed).

## Out of scope

- Normalising every other `Input-type` value.
- The other advisory findings from PR #301.

## Open questions

- Q1: Match a leading `bug[ -]?fix` token, the way `_resolve_lane` matches the lane, or warn when the value is not one of the template's options? (assumed: the token match)

## What success looks like

- `verify_summary.py --lane` on a SUMMARY with `Input-type: bug-fix`, `bugfix` or `bug fix (harness)` and no red/green rows prints the red/green warning, and exits 1 under `REQUIRE_RED_TEST=1`.
- The same command on a SUMMARY with `Input-type: harness fix` or `bug fixes` prints no red/green message.
- `scripts/test_verify_summary.py` passes.
