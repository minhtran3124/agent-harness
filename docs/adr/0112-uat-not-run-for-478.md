---
ticket: 478
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-29
---

# 0112. UAT not run for #478

## Context

The UAT stage could not check the running app: No verify.config.json found. It is missing at .../sandbox-per-ticket/t478/verify.config.json and at the root of the uat-478 worktree. The UAT skill forbids inferring or writing a config, so no app was started.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 478 by hand.
