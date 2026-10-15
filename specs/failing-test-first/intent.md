# Intent: Failing-test-first protocol for bug fixes

Author: Minh Tran
Status: approved

## Problem

A bug fix can claim "done" with a test that passes after the fix but was never shown to fail
before it. Such a test may not exercise the bug at all, so it proves nothing about the fix. The
harness has no step that asks for a red test first, and no check that looks for one. Today intake
has no bug-fix input type either, so nothing marks a run as a bug fix.

## Proposed outcome

When intake classifies a request as a bug fix, the run must show a failing test before the fix
and the same test passing after it:

- Intake can record a bug fix as its input type (a new `Input-type` value). (assumed)
- The `### Verify` table in that run's `SUMMARY.md` holds a red row (the test fails before the
  fix, with the commit sha it ran at) and a green row (the same test passes after the fix).
- `scripts/verify_summary.py` checks for the red and green rows on bug-fix runs. The check is
  advisory first: it warns and exits 0, and an environment variable makes it blocking, like
  `REQUIRE_NOT_AUTO_VERIFIED=1`. (assumed: the variable name is chosen in design)
- `subagent-driven-development` tells the implementer of a bug-fix task to commit the failing
  test before the fix and record both rows.

## Affected users and systems

- Agents that run `feature-intake` and `subagent-driven-development` on a bug fix.
- `scripts/verify_summary.py`, and through it the commit-gate lane-evidence check that relays its
  advisories.
- Consumer repos that receive the harness on re-sync.

## Constraints

- Advisory by default. Nothing that passes today may start to block unless the opt-in variable
  is set.
- Runs that are not bug fixes are unaffected.
- Existing `SUMMARY.md` files in `specs/` must keep passing `verify_summary.py`.
- The check is traceability-tier: it verifies that the rows exist and are well-formed, not that
  the test really failed. State this as `Verifies:` / `Does not verify:` lines. (assumed)

## Out of scope

- A hook that blocks edits to test files during fix tasks (that is M2).
- Re-running the red row to prove it fails (a truth-tier check).
- Making the check blocking by default.

## Open questions

- Q1: How does a run become a "bug fix"? A new `Input-type: bug fix` value set at intake, or a
  separate flag? (assumed: a new `Input-type` value)
- Q2: What happens when a bug has no testable surface (a prose or config bug)? An explicit
  exemption line in `### Verify`, or does the check skip it? (assumed: an exemption line with a
  reason)
- Q3: How is a red row recognised: a non-zero `Exit` plus a sha in `Notes`, or a new column?
  (assumed: no new column; a marker in the existing columns, decided in design)

## What success looks like

- `verify_summary.py` on a bug-fix SUMMARY with no red row prints a warning and exits 0, and
  exits 1 when the opt-in variable is set.
- The same command on a bug-fix SUMMARY with red and green rows exits 0 with no warning.
- Every existing `specs/*/SUMMARY.md` gives the same `verify_summary.py` result as before.

## Original request

"what next item for sdlc?" — then, after I recommended E5 and asked "Should I start E5
(failing-test-first for bug fixes)? I'd begin with `feature-intake` on a new branch cut from
`sdlc`.", the reply: "yes"

E5 as written in `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6:
"**Failing-test-first protocol for bug fixes**: when `Input-type` is a bug fix, the `### Verify`
table must contain a red row (test fails before fix, with commit sha) and a green row after" —
Where: `skills/feature-intake`, `skills/subagent-driven-development`, `scripts/verify_summary.py`
(advisory first).
