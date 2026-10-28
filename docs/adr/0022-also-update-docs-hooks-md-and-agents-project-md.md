---
ticket: 393
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-28
---

# 0022. Also update docs/hooks.md and agents/PROJECT.md

## Context

Both files name merge-deny.sh and its test; a new script and test would otherwise be undocumented and unmapped.

## Options

- Add one sentence and one mapping entry
- Leave docs untouched

## Decision

Add one sentence and one mapping entry

## Why

Keeps the source-to-test mapping accurate; small docs-only change.

## Consequences

Two extra files in the diff beyond the ticket's four.

## How to reverse

Revert those two edits.
