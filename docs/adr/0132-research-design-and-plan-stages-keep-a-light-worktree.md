---
ticket: 477
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0132. Research, design and plan stages keep a light worktree

## Context

The ticket lists implement, verify, review and UAT as sandbox stages. Research, design and plan only read code, and their output goes to specs/.

## Options

- Light detached worktree via trimmed newWt
- Put them in the ticket sandbox too

## Decision

Keep research, design and plan, plus merge, suite, fix and ADR stages, on trimmed light worktrees. The sandbox starts at implement.

## Why

These stages need no environment, and the sandbox branch does not exist before the plan is done. Provisioning earlier would hold ports for longer.

## Consequences

The 'worktrees' list in the result still has entries; the sandboxes are listed separately.

## How to reverse

Provision before the intent stage and point these stages at the sandbox dir.
