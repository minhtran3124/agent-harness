---
ticket: 500
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-30
---

# 0101. UAT not run for #500

## Context

The UAT stage could not check the running app: No verify.config.json found at t500/verify.config.json or at the root of the uat-500 worktree. The UAT skill forbids inferring or writing a config. The ticket is also a workflow-script and docs change with no web app to start.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 500 by hand.
