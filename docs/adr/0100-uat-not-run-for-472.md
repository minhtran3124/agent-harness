---
ticket: 472
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-29
---

# 0100. UAT not run for #472

## Context

The UAT stage could not check the running app: No verify.config.json found. The prompt's path (.../sandbox-per-ticket/t472/verify.config.json) does not exist (the t472 directory is absent), and the worktree .../uat-472 (detached at github/feat/sandbox-per-ticket, ac3f3c7) has no verify.config.json at its root. The uat skill forbids inferring or writing a config, so no run was attempted.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 472 by hand.
