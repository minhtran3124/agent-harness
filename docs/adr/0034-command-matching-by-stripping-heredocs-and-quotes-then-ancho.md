---
ticket: 394
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0034. Command matching by stripping heredocs and quotes, then anchoring at command position

## Context

The hook must tell a real merge command from text that mentions it, using bash 3.2 safe tools.

## Options

- Anchored regex after removing heredoc bodies and quoted strings
- Full shell parser

## Decision

Remove heredoc bodies and quoted strings, then match only at the start or after &&, ;, | or env assignments.

## Why

Simple, testable, no new dependency; fails closed.

## Consequences

Forms like bash -c "gh pr merge 7" do not trigger cleanup; run the script by hand.

## How to reverse

Loosen the anchor in the match step.
