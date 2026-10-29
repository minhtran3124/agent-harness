---
ticket: 398
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0041. Treat context 'n/a' as empty when merging duplicates

## Context

ship.js fills a missing context with the string 'n/a'. Matching on identical context would merge unrelated decisions that both lack a context.

## Options

- Treat 'n/a' like an empty context (never matches)
- Compare contexts literally

## Decision

Treat 'n/a' as empty; only identical non-empty real contexts merge.

## Why

Matches the owner rule that an empty context never matches; avoids false merges.

## Consequences

Two decisions with a missing context merge only if their title slugs match.

## How to reverse

Remove the n/a check in _context_key in write_adrs.py.
