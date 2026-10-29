---
ticket: 473
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-29
---

# 0102. UAT not run for #473

## Context

The UAT stage could not check the running app: No verify.config.json exists. It is missing at /home/minhtran/Documents/minh.tran/projects/.ship-agent-harness-simplify/sandbox-per-ticket/t473/verify.config.json and at the root of the uat-473 worktree. The uat skill forbids inferring, writing or committing a config. Ticket #473 is a shell-script change with no running app, so a browser UAT does not apply.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 473 by hand.
