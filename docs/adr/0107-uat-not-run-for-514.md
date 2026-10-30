---
ticket: 514
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-30
---

# 0107. UAT not run for #514

## Context

The UAT stage could not check the running app: No verify.config.json found at the given path (t514/verify.config.json) or at the root of the uat-514 worktree. The skill forbids inferring or writing one. The ticket is also a CLI/script checker with no running app or browser surface.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 514 by hand.
