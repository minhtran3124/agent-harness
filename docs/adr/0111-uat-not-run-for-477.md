---
ticket: 477
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-29
---

# 0111. UAT not run for #477

## Context

The UAT stage could not check the running app: No verify config was found. The t477/verify.config.json directory is missing (ls: No such file or directory). The worktree uat-477 (detached at ac3f3c7) has no verify.config.json at its root either. The skill forbids inferring or writing a config, so the app was not started.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 477 by hand.
