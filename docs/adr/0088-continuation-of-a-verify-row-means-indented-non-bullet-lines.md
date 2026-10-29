---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0088. Continuation of a Verify row means indented non-bullet lines

## Context

The old rule skipped every non-blank line after a Verify row, removing tight AC bullets.

## Options

- Skip only indented non-bullet lines
- Skip until blank line (old)

## Decision

Skip only indented, non-list-item lines after the Verify row

## Why

Keeps the existing multi-line Verify test working while preserving tight AC lines

## Consequences

An unindented wrapped Verify continuation would now leak into the UAT prompt

## How to reverse

Revert the condition in stripVerify
