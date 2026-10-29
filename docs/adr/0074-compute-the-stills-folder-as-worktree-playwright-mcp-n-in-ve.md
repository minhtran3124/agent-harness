---
ticket: 426
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0074. Compute the stills folder as <worktree>/.playwright-mcp/<n> in verifyTicket

## Context

buildGif already builds this path inline, and the verify result needs it as dir.

## Options

- Compute dir once in verifyTicket and pass it to buildGif
- Use the first still's dirname from the agent report

## Decision

Compute dir once from impl.worktree and t.n, reuse it for buildGif and the returned object.

## Why

It is deterministic, does not rely on the agent's stills list (which may be empty), and keeps the path the same as the one the GIF stage uses.

## Consequences

A small signature change to buildGif (an optional dir argument) or a local const; behaviour is unchanged.

## How to reverse

Inline the path again.
