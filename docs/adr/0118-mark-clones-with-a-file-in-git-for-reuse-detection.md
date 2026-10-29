---
ticket: 473
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0118. Mark clones with a file in .git for reuse detection

## Context

Re-running must reuse the sandbox, but a clone's origin is the real URL, so it cannot be matched to the main repo by remote.

## Options

- Compare origin URLs
- Store the source repo path in a marker file inside the clone's .git
- Check only that .git exists

## Decision

Write the source repo's absolute path to .git/harness-sandbox-source and reuse only when it matches.

## Why

Reliable and invisible to git status; a different folder or a worktree at that path exits 1.

## Consequences

Clones made by hand are not reused.

## How to reverse

Drop the marker and match another way.
