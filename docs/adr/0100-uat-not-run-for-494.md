---
ticket: 494
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-29
---

# 0100. UAT not run for #494

## Context

The UAT stage could not check the running app: No verify.config.json exists at the given config path (.../clean-worktrees-sweep-config/t494/verify.config.json) or at the root of the uat-494 worktree. The UAT skill forbids inferring or writing a config. The ticket changes a shell hook and docs, with no web app to start.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 494 by hand.
