---
ticket: 479
stage: implement
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0113. Boundary: tests/scripts/check-shellcheck.test.sh hardcodes 9 shellcheck files

## Context

Adding plugins/harness/hooks/sandbox-reminder.sh raises the hook plus script count checked by scripts/check-shellcheck.sh from 9 to 10. tests/scripts/check-shellcheck.test.sh line 24 asserts exactly 9, so bash scripts/run-tests.sh now fails that one case.

## Options

- Edit line 24 of tests/scripts/check-shellcheck.test.sh from 9 to 10 (or derive the count from the globs)
- Leave it and fail the full suite

## Decision

Not edited; the file is outside the ticket's named files. A one-line change to the expected count (9 to 10) is needed before the full suite can pass.

## Why

The ticket boundary forbids touching files it does not list. Leaving it would break CI, so the change needs to be approved or folded into the boundary.

## Consequences

Until that line is updated, run-tests.sh and CI fail on this one case.

## How to reverse

Not applicable; nothing was changed.
