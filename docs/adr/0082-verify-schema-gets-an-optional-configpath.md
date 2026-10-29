---
ticket: 462
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0082. VERIFY_SCHEMA gets an optional configPath

## Context

UAT must use the config path verify actually used, not a hard-coded one.

## Options

- Hard-code impl.worktree/verify.config.json
- Add optional configPath to VERIFY_SCHEMA with the hard-coded path as fallback

## Decision

Verify agents report configPath (optional); verifyTicket returns it, falling back to ${impl.worktree}/verify.config.json. If that file does not exist the UAT skill reports BLOCKED, which becomes a not-run decision.

## Why

Advisor item 3. Additive and optional, so what verify checks is unchanged.

## Consequences

The verify output contract grows by one optional field.

## How to reverse

Remove configPath from VERIFY_SCHEMA and the verify prompt.
