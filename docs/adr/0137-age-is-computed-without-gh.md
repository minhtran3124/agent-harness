---
ticket: 479
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0137. Age is computed without gh

## Context

The provision-sandbox.sh list mode calls gh per sandbox to find the PR state, which would slow session start and need the network.

## Options

- Age only from created_at, with mtime as fallback
- Reuse provision-sandbox.sh list and skip sandboxes whose PR is open

## Decision

Age only from created_at, with mtime as fallback. The hook does not check PR state, and the wording says the sandboxes are old, not that they are abandoned.

## Why

The owner-confirmed spec names created_at and mtime only, and the hook must stay fast and offline. The clean --older command itself skips sandboxes with an open PR.

## Consequences

The count can include a sandbox with an open PR that the clean command would then skip.

## How to reverse

Add a PR-state filter in the hook later.
