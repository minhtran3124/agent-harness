---
ticket: 478
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0136. Run the sandbox pass before the branch loop, in hook mode only

## Context

A sandbox worktree holds the branch, so git branch -d would fail while it exists; a clone-mode sandbox has no local branch to match.

## Options

- Separate pass before the loop over merged head branches
- Inside the loop after the local-tip check
- Delegate everything to the sandbox script

## Decision

Separate pass before the loop over the merged headRefs in $only, skipping keep branches, ignoring the script exit code.

## Why

Keeps sandbox safety logic in one place and does not depend on the local-tip check.

## Consequences

A manual no-argument run does not clean sandboxes, consistent with the owner's no full sweep rule.

## How to reverse

Move the call into the loop or delete the pass.
