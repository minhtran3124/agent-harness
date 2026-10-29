---
ticket: 462
stage: implement
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0081. Infrastructure failure of UAT does not fail the ticket

## Context

No config, app will not start, missing credentials, a null agent result or an agent exception.

## Options

- Treat as AC failure and run the fix agent
- Record a needs_review decision and continue

## Decision

A blocked or empty UAT result, or a thrown agent error, records a needs_review decision 'UAT not run for #n', leaves the ticket done, runs no fix, and the PR body says UAT did not run. No retry is added.

## Why

Advisor item 4: a start-up failure must not launch a code fix, and call() does not retry.

## Consequences

A run with a broken config passes UAT silently except for the decision and PR note.

## How to reverse

Change uatNotRun handling in stageUat.
