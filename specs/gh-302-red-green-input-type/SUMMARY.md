# gh-302-red-green-input-type — Summary

Lane: normal
Confidence: medium
Reason: bug fix in the evidence gate across two files (verify_summary.py + its tests); one flag (existing behavior); no manifest hard gate
Flags: existing behavior
Affects: scripts/verify_summary.py (`_red_green_issue`, lane-evidence gate)
Input-type: bug fix

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/gh-302-red-green-input-type/intent.md @ ef5a39cdd968ead45eb7dd2bea381f7e073673b0

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

### Intake notes

- Lane: normal — not tiny because the fix spans two files (code + test). No manifest hard gate: `scripts/` is not high-blast, and the change tightens validation instead of weakening it. `scripts/` is in the warn tier of `scripts/ci-strict-gate.sh`.
- Confidence: medium — Q1 has a documented safe default (leading `bug[ -]?fix` token match, like `_resolve_lane`); the success criteria fit only that reading. The `bug fixes` exclusion is an assumed default from the intent.
- Baseline: no existing `specs/*/SUMMARY.md` has an `Input-type` value that starts with `bug` (checked with `grep -rhn '^Input-type:' specs/*/SUMMARY.md`), so no current SUMMARY changes result.
- `rules/auto-correct-scope.md` names the check as "`Input-type: bug fix`". It stays accurate; it is not edited (out of scope, and a rule edit trips the `workflow-engine` signal).
- Branch `fix/gh-302-red-green-input-type` was cut from `sdlc` (the #301 base) before the intent commit, so the intent commit is not on a shared branch.
- This SUMMARY has `Input-type: bug fix`, so its own `### Verify` needs a `red`/`green` row pair (advisory by default).

## What changed

`_red_green_issue` in `scripts/verify_summary.py` now applies the red/green check when the trimmed,
lower-cased `Input-type` starts with a `bug fix`, `bug-fix` or `bugfix` token
(`_BUG_FIX_INPUT_RE = bug[ -]?fix(?![\w-])`), instead of only when it equals `bug fix`. Values such
as `bug fixes`, `bugfixes`, `bug fix-up`, `bugs fix` and `harness fix` still get no red/green
message. The scan test over existing `specs/*/SUMMARY.md` uses the same predicate as the checker.

### Rationale

The token match follows `_resolve_lane` in the same file and the intent's Q1 default. The
`(?![\w-])` lookahead keeps the match from widening to words that only start with `bug fix`. The
check stays advisory unless `REQUIRE_RED_TEST=1`, and no existing SUMMARY has an `Input-type`
that starts with `bug`, so no current result changes.

### Alternatives considered

- Warn when `Input-type` is not one of the template's options (intent Q1, other reading): rejected
  because existing SUMMARYs use free-form values (`harness fix`, `plan execution (…)`), so it
  would warn on many runs that are not bug fixes, against the intent's constraints.

### Deviations

- none

### Review findings (Minor, non-blocking)

- Task 1.1 review — `scripts/verify_summary.py` `_red_green_issue` docstring says "extra text allowed after it", but the regex rejects a word character or `-` right after the token (`bug fixes`, `bug fix-up`). Wording only; forwarded to final review.
- Task 1.1 review — `scripts/verify_summary.py:67` module comment still names only `Input-type: bug fix`. Out-of-date comment only; forwarded to final review.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| red | `python3 scripts/run_at_commit.py ee6da93 -- /tmp/harness-tests-venv/bin/python -m pytest -q scripts/test_verify_summary.py -k input_type` | 1 | 2 new spelling tests fail at the test-only commit | |
| green | `/tmp/harness-tests-venv/bin/python -m pytest -q scripts/test_verify_summary.py -k input_type` | 0 | 5 passed after the fix | SC-1 |
| full suite | `/tmp/harness-tests-venv/bin/python -m pytest -q scripts/test_verify_summary.py` | 0 | 93 passed, incl. the specs/*/SUMMARY.md scan | SC-2 |

### Not auto-verified

- Consumer repos receive the change only after a harness re-sync — reached traceability; not re-run because no consumer deploy is part of this change.

### Rollback

- `git revert 36d809f ee6da93`

### Harness-Delta

- none
