---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0093. Keep console errors non-blocking in uatOk

## Context

The finding also says a non-numeric console_errors becomes NaN and is accepted. Existing test u5d and the code comment say console errors never fail a ticket whose ACs pass.

## Options

- Block on console errors
- Keep console errors non-blocking and fix only passed_ac

## Decision

Keep console errors non-blocking and fix only passed_ac.

## Why

Blocking on console errors would contradict the documented design and test u5d, and unrelated noise would fail tickets.

## Consequences

A non-numeric console_errors is still ignored. It is only used for the display count in the fix prompt.

## How to reverse

Add a console_errors check to uatOk and update test u5d.
