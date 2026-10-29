---
ticket: 477
stage: design
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: design)
date: 2026-10-29
---

# 0131. UAT in a multi-ticket run detaches the ticket sandbox to finalRef

## Context

UAT tests the merged result (finalRef). In a multi-ticket run finalRef is the integration branch, which the ticket sandbox (on the ticket branch) does not contain. The UAT rerun after a fix must also see the fix.

## Options

- Run UAT in the ticket sandbox after fetch and git checkout --detach finalRef
- Keep a light worktree for UAT and give it the sandbox port and DB
- Provision a second sandbox for UAT

## Decision

UAT and the rerun run in the ticket sandbox, first fetching and detaching it to finalRef. In a single-ticket run finalRef equals the ticket branch, so no checkout change happens.

## Why

UAT keeps the ticket's installed environment, port and DB, and needs no second provisioning. Detaching leaves the ticket branch ref untouched.

## Consequences

The sandbox HEAD is detached after UAT in a multi-ticket run; a later clean refuses a dirty sandbox but not a detached one. If the integration branch changes dependencies, the sandbox install may be stale; UAT then reports blocked or fails and the owner sees it.

## How to reverse

Give UAT its own light worktree again via newWt(wtName, null, finalRef) and drop the sandbox from uatAgent.
