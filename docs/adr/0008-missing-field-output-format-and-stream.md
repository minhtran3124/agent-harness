---
ticket: 381
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0008. Missing-field output format and stream

## Context

Ticket requires --check to name the file; format is unspecified.

## Options

- One stderr line per file: 'solution-index: <path relative to docs/solutions> is missing applicable_when'
- Single aggregated line

## Decision

One stderr line per file with the path relative to docs/solutions

## Why

Greppable, matches the existing 'solution-index:' stderr prefix for failures.

## Consequences

Tests assert the relative path substring.

## How to reverse

Change the print format and the test substring.
