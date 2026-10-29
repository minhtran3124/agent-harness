---
ticket: 477
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0107. Reject args.sandbox clone combined with local mode; use origin inside a clone

## Context

In clone mode the ticket branch exists only inside the clone and the clone's only remote is origin. The merge stage and finalRef worktrees of repoDir cannot see that branch in local mode, and prompts using the project remote (github here) fail inside a clone.

## Options

- Allow clone with local and keep the project remote name
- Throw in validateArgs for clone + local, and use origin and origin/<branch> for every command that runs inside a sandbox
- Do not support clone mode

## Decision

validateArgs throws when sandbox is clone and local is true. One helper (SB_REMOTE, sbRef) makes implement, verify, finish and UAT prompts use origin in clone mode. The end-of-run log says clones are removed by hand because clean skips them.

## Why

Follows the advisor review; checked against provision-sandbox.sh (clone remote origin, clean skips non-worktrees).

## Consequences

A new args rule: sandbox clone cannot be used with local. If a ticket AC needed clone with local, this contradicts it.

## How to reverse

Remove the validateArgs check and the SB_REMOTE helper; use remote everywhere.
