---
ticket: 477
stage: intent
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0110. New ADR 0100 supersedes only part of ADR 0002

## Context

ADR 0002 decision 1 says each agent creates its own worktree. The owner confirmed that a new ADR supersedes only that part and 0002 gets a 'superseded in part' note.

## Options

- New ADR 0100 plus a note on 0002
- Edit 0002's decision in place

## Decision

Return an ADR decision for 0100 (needs_review true because it changes a recorded earlier decision) and add the note to 0002 in this ticket.

## Why

This keeps the history of 0002 and matches the owner's instruction.

## Consequences

Decisions 2 to 6 of 0002 stay in force.

## How to reverse

Revert the note and the ADR.
