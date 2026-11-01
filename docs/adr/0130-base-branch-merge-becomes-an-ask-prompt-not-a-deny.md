---
ticket: 545
stage: intent
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-31
---

# 0130. Base-branch merge becomes an ask prompt, not a deny

## Context

The ticket changes a hard rule: the hook denies every merge into main today.

## Options

- Keep deny and only hand back a ! command
- Emit permissionDecision ask for one plain gh pr merge <n>

## Decision

Emit ask for one plain gh pr merge <n> into base. Deny stays for every other path.

## Why

The owner's Yes in the prompt is the approval and the agent cannot produce it. This is the ticket's proposed change.

## Consequences

An agent can merge into main after the owner confirms one PR. This changes a hard rule in CLAUDE.md and parts of ADR 0108 and 0109, so a human reviews the PR.

## How to reverse

Restore the deny branch in judge() in merge-guard.sh and revert the doc wording.
