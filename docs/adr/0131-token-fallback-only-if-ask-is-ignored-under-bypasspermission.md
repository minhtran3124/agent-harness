---
ticket: 545
stage: intent
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-31
---

# 0131. Token fallback only if ask is ignored under bypassPermissions

## Context

The behavior of ask under bypassPermissions is unknown.

## Options

- Always add the UserPromptSubmit token fallback
- Add it only if the test shows ask is ignored under bypassPermissions

## Decision

Check first and add the fallback only if ask is ignored there.

## Why

This is the owner's instruction. It avoids a second approval path that an agent with Bash could forge.

## Consequences

If built, the fallback guards against mistakes and not against a hostile agent. The ADR records that limit.

## How to reverse

Remove the UserPromptSubmit hook and the token check.
