---
ticket: 394
stage: plan
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0033. Branch of a different PR is never removed when a PR number is known

## Context

Whether cleanup after a merge may remove branches of other PRs.

## Options

- Clean only the merged PR's branch
- Keep sweeping all merged branches

## Decision

Clean only the branch of the PR just merged; the no-argument manual run keeps the full sweep.

## Why

Matches owner-confirmed decision 2 and removes the surprise deletion in the ticket.

## Consequences

Other merged branches stay until the user runs the script by hand.

## How to reverse

Drop the headRefName filter in the loop.
