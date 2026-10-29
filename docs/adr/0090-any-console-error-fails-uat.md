---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0090. Any console error fails UAT

## Context

The UAT schema returns console_errors as a number, but nothing checked it. The finding says console errors can still pass.

## Options

- Treat any console error greater than 0 as an AC failure
- Log console errors only

## Decision

Treat console_errors greater than 0, or an AC scenario with FAIL, as an AC failure, whatever passed_ac says. The fix prompt now lists the console error count.

## Why

The finding asks that console errors and FAIL rows cannot pass.

## Consequences

A UAT run with console noise now triggers one fix round, and then blocks the ticket if it persists.

## How to reverse

Remove the console_errors clause in uatOk in ship.js.
