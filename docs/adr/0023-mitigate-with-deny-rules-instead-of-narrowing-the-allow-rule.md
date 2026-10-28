---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-28
---

# 0023. Mitigate with deny rules instead of narrowing the allow rule

## Context

Bash(gh pr merge *) matches risky flags; permission patterns cannot exclude flags.

## Options

- Add deny rules for the three flags (deny beats allow)
- Replace the wildcard with an exact-form allow rule
- Only warn in SKILL.md

## Decision

Add deny rules for --admin, --auto and --delete-branch (both leading and trailing positions) in the same settings file, and add a one-sentence note to SKILL.md.

## Why

Keeps the ticket's allow rule unchanged while enforcing the safeguard; a warning alone would not stop pre-approval.

## Consequences

Merges using those flags still prompt. settings.local.json gets 6 extra deny entries.

## How to reverse

Revert commit f715ef9.
