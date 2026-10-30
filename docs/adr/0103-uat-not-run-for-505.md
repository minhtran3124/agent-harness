---
ticket: 505
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-30
---

# 0103. UAT not run for #505

## Context

The UAT stage could not check the running app: No verify.config.json exists at t505/verify.config.json or at the root of the uat-505 worktree. The change is a workflow script and tests, with no app to start, and the uat skill forbids inferring or writing a config.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 505 by hand.
