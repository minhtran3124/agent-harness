---
ticket: 393
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0020. Keep setup-contract 80-line cap, so the new step must be compact

## Context

setup-contract.test.sh enforces at most 80 lines and under 600 words; SKILL.md is 349 words today.

## Options

- Keep the caps and write a short step
- Raise the caps in the test

## Decision

Keep the caps and write a short step

## Why

The ticket requires staying under 600 words and raising a cap would weaken a test.

## Consequences

The step is about 6 to 8 lines.

## How to reverse

n/a
