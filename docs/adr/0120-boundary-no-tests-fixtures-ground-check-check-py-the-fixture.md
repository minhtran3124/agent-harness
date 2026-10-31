---
ticket: 523
stage: implement
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-30
---

# 0120. Boundary: no tests/fixtures/ground-check-check.py; the fixture checks live in the runner test

## Context

Plan step 1 named an extra checker file tests/fixtures/ground-check-check.py, which is not in the boundary file list.

## Options

- Add the extra file (outside the boundary)
- Put the same checks in scripts/test_compare_symbol_checkers.py (inside the boundary)

## Decision

Did not create tests/fixtures/ground-check-check.py. The claim count, label set and name-presence checks are in scripts/test_compare_symbol_checkers.py (FixtureTests), and run with the suite.

## Why

The file is outside the ticket's file list; the test file is inside it and is collected by run-tests.sh, so the check runs in CI.

## Consequences

Step 1's Done-when command is covered by python3 -I scripts/test_compare_symbol_checkers.py instead.

## How to reverse

Move FixtureTests into a standalone script if a separate checker is wanted.
