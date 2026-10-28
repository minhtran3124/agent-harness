---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: review-fix)
date: 2026-10-28
---

# 0024. Reuse exit code 2 for wrong-typed permissions

## Context

The finding says jq exited 5, outside the documented exit codes.

## Options

- Reuse exit 2 (settings file invalid, untouched)
- Add a new exit code 4

## Decision

Reuse exit 2 and extend its documentation in the script header and SKILL.md

## Why

Same meaning as the existing code (the settings file is unusable, file untouched), so callers need no new handling.

## Consequences

Exit 2 now covers both non-JSON-object files and wrong-typed permissions/allow/deny.

## How to reverse

Change the exit code in the new guard in merge-allow.sh and update the header, SKILL.md and test.
