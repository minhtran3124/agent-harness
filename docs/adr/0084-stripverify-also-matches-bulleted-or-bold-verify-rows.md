---
ticket: 462
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0084. stripVerify also matches bulleted or bold Verify rows

## Context

The design regex was /^\s*Verify:/; a row written as '- Verify:' or '**Verify:**' would leak to UAT.

## Options

- Exact design regex
- Allow an optional bullet and bold marker

## Decision

Use /^\s*(?:[-*>]\s*)?(?:\*\*|__)?Verify:/. Mid-sentence mentions still stay; the stripped line count is logged.

## Why

Blindness is the point of the phase; a bulleted row must not slip through.

## Consequences

A legitimate bulleted line starting with Verify: is also stripped (logged).

## How to reverse

Narrow VERIFY_ROW in ship.js.
