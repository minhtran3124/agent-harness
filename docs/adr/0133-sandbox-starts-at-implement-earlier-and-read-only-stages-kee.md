---
ticket: 477
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0133. Sandbox starts at implement; earlier and read-only stages keep a light worktree

## Context

Research, design and plan only read code, and the ticket branch does not exist before the plan is done.

## Options

- Light detached worktree via newWt for research, design, plan, verify-base, review, merge, suite, fix, ADR
- Put every stage in the sandbox

## Decision

Provision after plan and before implement; only implement, verify (head, retry), finish and UAT use the sandbox.

## Why

Read-only stages need no environment; fewer ports held and less setup time.

## Consequences

out.worktrees still has light entries; sandboxes are listed separately in out.sandboxes.

## How to reverse

Provision before the intent stage and point those stages at the sandbox dir.
