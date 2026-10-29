---
ticket: 474
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0124. CLOSED PR counts as no PR

## Context

gh pr view can return CLOSED, which the ticket does not cover.

## Options

- treat CLOSED as none
- add a closed state

## Decision

Treat CLOSED as none, so an old sandbox with a closed PR is abandoned.

## Why

A closed unmerged PR is no live work.

## Consequences

No new state or column value.

## How to reverse

Add a CLOSED case in sb_pr_state.
