---
ticket: 518
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-30
---

# 0116. UAT not run for #518

## Context

The UAT stage could not check the running app: No verify.config.json found at /home/minhtran/Documents/agilityio/.ship-agent-harness/518-merge-guard-bypass/t518/verify.config.json or at the root of the uat-518 worktree. The uat skill forbids inferring, writing or committing a config. The ticket is a shell hook with no running app, so no browser check applies.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 518 by hand.
