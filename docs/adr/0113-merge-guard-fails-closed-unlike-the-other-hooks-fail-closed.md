---
ticket: run
stage: intent-fix
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-30
---

# 0113. Merge guard fails closed, unlike the other hooks (fail-closed merge guard)

## Context

All other harness hooks fail open. The merge guard blocks gh pr merge and gh api .../merge unless the PR base is feat/*. Owner decision D requires fail-closed behavior when the base cannot be read.

## Options

- Fail open like other hooks
- Fail closed once a merge command is seen; exit 0 fast for non-merge Bash calls

## Decision

Fail closed after a merge command is detected (unreadable base, no gh, no jq, no PR number, bad JSON all deny with exit 2); non-merge calls exit 0 fast.

## Why

A guard that fails open on doubt would let an auto merge into main through; the owner confirmed fail-closed.

## Consequences

A broken gh or jq environment blocks merges until the owner merges by hand in a terminal; the guard does not cover the owner's own terminal merges.

## How to reverse

Change the deny paths in plugins/harness/hooks/merge-guard.sh to exit 0.
