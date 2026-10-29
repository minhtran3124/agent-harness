---
ticket: 413
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0068. Issue comment is made by a small cheap agent call

## Context

ship.js cannot run shell commands; the failure report must go to the issue as a comment.

## Options

- Separate cheap agent (haiku) runs gh issue comment
- Verify agent comments itself
- Skip the comment and only use reason

## Decision

A separate cheap agent labeled verify-comment:<n> posts the comment, not in local mode; a comment failure is logged and does not change the blocked result.

## Why

The verify agent only runs steps and reports (owner decision 3); the ticket demands a comment.

## Consequences

One more agent call on the blocked path only.

## How to reverse

Fold the comment into the stageFinish or remove the call.
