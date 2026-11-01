---
ticket: run
stage: review-fix
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: review-fix)
date: 2026-10-31
---

# 0135. Boundary: F4 doc and ship.js updates are outside the ticket #545 file set

## Context

F4 asks to amend README, docs/workflows.md, HARNESS.md, setup/SKILL.md, AGENTS.md, ship.js:41 and ADRs 0109 and 0113 so they no longer say agents never merge into base. The ticket's file set names only merge-guard.sh, hooks.json, three tests, CLAUDE.md, behavior.md, docs/hooks.md and ADRs 0108 and 0109.

## Options

- Skip and flag as a boundary issue
- Edit the out-of-set files anyway

## Decision

Skip the fix and change nothing.

## Why

The rules say a fix touching a file outside the set must be skipped. Editing ship.js would also touch workflow behavior, which the ticket puts out of scope (merges by a workflow or subagent into base).

## Consequences

The stale 'agents never merge into base' wording remains in those files until a follow-up ticket widens the file set.

## How to reverse

Open a follow-up ticket that lists those files, or add them to the #545 file set, then rerun the fix stage.
