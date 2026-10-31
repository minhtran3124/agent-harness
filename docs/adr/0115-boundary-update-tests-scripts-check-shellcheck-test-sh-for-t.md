---
ticket: 531
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-31
---

# 0115. Boundary: update tests/scripts/check-shellcheck.test.sh for the new shellcheck file

## Context

That test pins the exact shellcheck file list and its count (9). Adding scripts/check-tag-version.sh to scripts/check-shellcheck.sh, which the ticket names, would fail it. The test file is not in the ticket's file list.

## Options

- Update the pinned list and count to 10
- Skip adding the script to the shellcheck list

## Decision

Update the pinned list and count to 10 in tests/scripts/check-shellcheck.test.sh

## Why

The ticket requires the shellcheck wiring; the test only mirrors the list, so no assertion is weakened.

## Consequences

One test file outside the named list is touched; it must be in the PR.

## How to reverse

Revert the test edit and drop the script from scripts/check-shellcheck.sh.
