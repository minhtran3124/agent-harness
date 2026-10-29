---
ticket: 474
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0122. Skip PR-open sandboxes in clean --older

## Context

The owner decision says running and unknown sandboxes are always skipped. It does not say what --older does with a sandbox that has an open PR.

## Options

- --older removes PR-open sandboxes too
- --older skips PR-open sandboxes; --run still removes them when named

## Decision

--older skips sandboxes with an open PR. --run ID can still remove one by name.

## Why

Open PR means live work. Age alone is a weak reason to delete it, and a dry run lets the owner see the plan first.

## Consequences

A stale sandbox with an open PR needs --run or a merge before clean removes it.

## How to reverse

Drop the `state != 'PR open'` check in the older branch of clean.
