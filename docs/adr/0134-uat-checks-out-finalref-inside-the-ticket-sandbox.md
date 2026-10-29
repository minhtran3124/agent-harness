---
ticket: 477
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0134. UAT checks out finalRef inside the ticket sandbox

## Context

UAT tests the merged result. In a multi-ticket run finalRef is the integration branch, not the ticket branch.

## Options

- Fetch and checkout --detach finalRef in the sandbox, also for the rerun
- Provision a separate sandbox for UAT

## Decision

UAT runs in the ticket sandbox after git fetch and checkout --detach finalRef; the rerun does the same so it sees the fix.

## Why

Reuses the existing port and DB; no extra sandbox.

## Consequences

The uat-rerun-n worktree name goes away.

## How to reverse

Restore newWt for UAT and its rerun.
