---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0140. Teardown tolerates a missing .sandbox.env

## Context

clean sourced .sandbox.env unconditionally before each teardown line, so a sandbox without it could never be cleaned.

## Options

- Source .sandbox.env only if present and run teardown anyway
- Refuse the sandbox with a clearer message
- Make teardown transactional with rollback

## Decision

Source .sandbox.env only if present and run teardown anyway

## Why

Smallest change that unblocks cleaning; a failing teardown still refuses the sandbox as before.

## Consequences

Teardown commands that need SANDBOX_* variables will fail visibly if the file is gone, and still refuse the sandbox.

## How to reverse

Revert commit 0a8ed31.
