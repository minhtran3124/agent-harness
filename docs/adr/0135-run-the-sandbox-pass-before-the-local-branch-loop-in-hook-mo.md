---
ticket: 478
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0135. Run the sandbox pass before the local branch loop, in hook mode only

## Context

A sandbox worktree holds the branch, so `git branch -d` and the existing worktree-remove step would act on it. A sandbox in clone mode has no local branch in the main repo.

## Options

- Separate pass before the loop over the merged head branches
- Inside the loop, after the local-tip check
- Delegate everything to the sandbox script

## Decision

A separate pass before the loop, over the merged headRefs from `$only`, so it works even without a local branch or tip match and frees the branch for `git branch -d`.

## Why

It keeps the sandbox safety logic in one place and does not depend on the local-tip check.

## Consequences

A manual no-argument run does not clean sandboxes; that is the existing sweep and the owner said no full sweep.

## How to reverse

Move the call into the loop or delete the pass.
