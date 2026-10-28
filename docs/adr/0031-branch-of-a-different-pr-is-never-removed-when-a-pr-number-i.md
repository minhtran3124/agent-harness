---
ticket: 394
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0031. Branch of a different PR is never removed when a PR number is known

## Context

Ticket acceptance asks to decide whether cleanup may remove a branch of a PR other than the one just merged.

## Options

- Clean only the merged PR's branch
- Keep the sweep of all merged branches and document it

## Decision

Clean only the branch of the PR just merged; the no-argument manual run keeps the full sweep.

## Why

Matches owner-confirmed decision 2 and removes the surprise deletion seen in the ticket.

## Consequences

Other merged branches stay until the user runs the script by hand.

## How to reverse

Drop the headRefName filter in the loop.
