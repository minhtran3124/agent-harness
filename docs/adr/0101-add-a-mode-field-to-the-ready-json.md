---
ticket: 473
stage: intent
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0101. Add a mode field to the ready JSON

## Context

Callers such as ship.js cleanup differ per mode (git worktree remove versus rm -rf).

## Options

- Leave JSON unchanged
- Add "mode":"clone|worktree"

## Decision

Add a mode field, keeping the existing fields in place.

## Why

Lets callers choose cleanup; existing consumers read fields by name.

## Consequences

A small public-output addition.

## How to reverse

Remove the field.
