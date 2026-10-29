---
ticket: 394
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0032. Command matching by stripping heredocs and quotes, then anchoring at command position

## Context

The hook must tell a real merge command from text that mentions it, using bash 3.2 safe tools only.

## Options

- Anchored regex over the command after removing heredoc bodies and quoted strings
- Full shell parser (not available in bash 3.2)

## Decision

Remove heredoc bodies and quoted strings, then match 'gh pr merge <n>' or 'gh api .../pulls/<n>/merge' only at the start or after &&, ;, | or env assignments.

## Why

Simple, testable, no new dependency; fail-closed (no match means no cleanup).

## Consequences

An unusual form such as 'bash -c "gh pr merge 7"' will not trigger the cleanup; the user can run the script by hand.

## How to reverse

Loosen the anchor in the match function.
