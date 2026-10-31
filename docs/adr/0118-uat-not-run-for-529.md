---
ticket: 529
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-31
---

# 0118. UAT not run for #529

## Context

The UAT stage could not check the running app: No verify.config.json found at /home/minhtran/Documents/agilityio/.ship-agent-harness/529-ship-stage-ledger/t529/verify.config.json or at the root of the worktree /home/minhtran/Documents/agilityio/.ship-agent-harness/529-ship-stage-ledger/uat-529. The uat skill forbids inferring or writing a config. The ticket also has no browser-visible surface: it changes ship.js ledger writes and docs.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 529 by hand.
