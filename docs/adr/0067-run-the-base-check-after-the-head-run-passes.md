---
ticket: 413
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0067. Run the base check after the head run passes

## Context

The ticket does not fix the order of head run and base check.

## Options

- Head first (with retry), then base only if head passes
- Base first, then head

## Decision

Head run (with its retry) first, then the base check only when the head run passed and kind is browser.

## Why

A ticket that fails twice on head is blocked anyway, so the base worktree and run are saved; the base check only matters when head passes.

## Consequences

A blocked-by-failure ticket never reports on the weak-test check.

## How to reverse

Move the base call before the head call in stageVerify.
