---
ticket: 413
stage: implement
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0065. Boundary: docs/workflows.md phase 6 renamed from Verify to Testing

## Context

The doc listed the full-suite phase as 'Verify', which clashes with the new verify stage; the script already names that phase Testing (#412). docs/workflows.md is a listed file.

## Options

- Leave the stale name
- Rename it to Testing

## Decision

Renamed the phase 6 line to Testing in docs/workflows.md.

## Why

Avoids two different things called Verify in the same doc; matches ship.js.

## Consequences

Doc wording only.

## How to reverse

Revert that one line.
