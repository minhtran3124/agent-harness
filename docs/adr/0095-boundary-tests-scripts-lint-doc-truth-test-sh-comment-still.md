---
ticket: 464
stage: implement
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0095. Boundary: tests/scripts/lint-doc-truth.test.sh comment still mentions skills/xia2/PROJECT.md

## Context

The acceptance grep for PROJECT.md in tests/ hits a historical code comment in a file the ticket does not list.

## Options

- Leave it
- Edit the comment

## Decision

Left unchanged because the file is not on the ticket's list.

## Why

Boundary rule: unlisted files are not edited. It is a comment about an old xia2 path, not a reader of agents/PROJECT.md.

## Consequences

The literal acceptance grep also shows this comment (and the test names/assertions in setup-contract and init-structure tests that assert the files are gone).

## How to reverse

Reword the comment in a follow-up.
