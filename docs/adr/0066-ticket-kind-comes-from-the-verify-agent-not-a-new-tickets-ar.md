---
ticket: 413
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0066. Ticket kind comes from the verify agent, not a new tickets arg

## Context

The base check applies to FE and end-to-end tickets only, but the ticket says no new field in the tickets args.

## Options

- Verify agent reads the Verify: row, returns kind (BE|FE|FE+BE|docs) in VERIFY_SCHEMA; ship.js decides the base check
- Add t.type to tickets args
- Infer from changed file extensions in ship.js

## Decision

Verify agent returns kind; ship.js runs the base check when kind is FE or FE+BE.

## Why

Matches ticket decision 2 and the skill's own type table; the retry, flaky and base-check decisions stay in ship.js.

## Consequences

One extra field in VERIFY_SCHEMA; a misclassified kind skips or adds a base check.

## How to reverse

Add a kind field to tickets args and read it in ship.js instead.
