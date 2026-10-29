---
ticket: 474
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-29
---

# 0103. UAT not run for #474

## Context

The UAT stage could not check the running app: No verify config found. Neither t474/verify.config.json nor verify.config.json at the root of the uat-474 worktree exists. The UAT skill forbids inferring or writing a config.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 474 by hand.
