---
ticket: 473
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0119. Share one post-creation sync step; #472 auto-copy not built here

## Context

The ticket says clone copies manifest files plus the #472 auto-copy set, but on github/feat/sandbox-per-ticket the script header says provisioning follows the manifest alone and no auto-copy exists.

## Options

- Implement auto-copy in this ticket
- Share the existing post-creation step so #472 applies to both modes when it lands
- Clone-only copy logic

## Decision

Share the existing post-creation step; copy manifest files only for now.

## Why

Stays in scope and avoids duplicating logic #472 will change.

## Consequences

Until #472 merges, clone mode copies manifest copy files only.

## How to reverse

Move the sync into a per-mode function.
