---
ticket: 398
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0043. Existing tests use medium confidence by default so the new filter keeps their files

## Context

The default test decision was high confidence and needs_review false, which the new filter drops. Tests that count written files would break.

## Options

- Change the default test decision to medium confidence and give each a distinct context
- Rewrite each test with explicit fields

## Decision

Default dec() is now medium confidence with a per-title context; tests that wrote two same-title decisions now use different tickets.

## Why

Keeps the old tests' intent (numbering, slug collisions, overwrite refusal) without weakening them.

## Consequences

None for production code.

## How to reverse

Revert scripts/test_write_adrs.py changes to dec().
