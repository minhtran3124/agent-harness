---
ticket: 394
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0003. State check before cleanup in hook mode

## Context

The ticket asked for `gh pr view <n> --json state,headRefName`.

## Options

- use headRefName whatever the state
- require state MERGED

## Decision

Require state MERGED; otherwise exit 0 silently. The existing merged-tip check in the loop is unchanged.

## Why

The task plan says to use headRefName only if the state is MERGED.

## Consequences

A `gh pr merge` that only queues an auto-merge (PR still open) cleans nothing.

## How to reverse

Remove the MERGED check in the hook.
