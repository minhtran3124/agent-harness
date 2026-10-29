---
ticket: 473
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0117. Clone mode shares the manifest-sync step; #472 auto-copy is not built here

## Context

The ticket and owner answer say clone copies manifest copy files plus the #472 auto-copy set, but github/feat/sandbox-per-ticket has no auto-copy (the script header says provisioning follows the manifest alone) and #472 is still open.

## Options

- Implement auto-copy inside this ticket
- Share one post-creation sync step so #472 applies to both modes when it lands
- Add clone-only copy logic

## Decision

Share one post-creation sync step; implement manifest copy only for now.

## Why

Keeps this ticket in scope and avoids duplicating logic that #472 will change.

## Consequences

Until #472 merges, clone mode copies only manifest copy files.

## How to reverse

Move the sync into a function per mode.
