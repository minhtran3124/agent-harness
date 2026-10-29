---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0091. ship.js edited despite #461 out-of-scope line

## Context

The #461 out-of-scope line names ship.js, but #462 lists ship.js and tests/workflows/harness.js in its files. The finding is in the UAT code that #462 owns.

## Options

- Edit ship.js under #462's file list
- Skip with a Boundary decision

## Decision

Edit ship.js and tests/workflows/harness.js under #462's file list.

## Why

The union file set names both files, and the finding is in #462's own UAT stage.

## Consequences

None for #461, which did not change.

## How to reverse

Revert commit 8278cd8.
