---
ticket: 475
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-29
---

# 0104. UAT not run for #475

## Context

The UAT stage could not check the running app: No verify.config.json found. The prompt's path (.../sandbox-per-ticket/t475/verify.config.json) does not exist (t475 directory is absent), and the worktree root /home/minhtran/Documents/minh.tran/projects/.ship-agent-harness-simplify/sandbox-per-ticket/uat-475 has none either. Per the uat skill, no config is inferred or written.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 475 by hand.
