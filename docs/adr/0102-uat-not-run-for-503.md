---
ticket: 503
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-30
---

# 0102. UAT not run for #503

## Context

The UAT stage could not check the running app: No verify.config.json found at t503/verify.config.json or at the root of the uat-503 worktree. The repo is a skill framework with no running app, and the uat skill forbids inferring or writing a config. The recipe file exists and the worktree was created.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 503 by hand.
