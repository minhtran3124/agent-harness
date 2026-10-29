---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0094. Edit ship.js although ticket #461 lists it as out of scope

## Context

Ticket #461's out-of-scope line names ship.js. Ticket #462 names ship.js and tests/workflows/harness.js in its file set, and the finding is a UAT stage defect.

## Options

- Skip as a boundary conflict
- Fix, since #462 owns ship.js

## Decision

Fix, since #462 owns ship.js.

## Why

The out-of-scope line limits what #461 changes. The fix touches only files in #462's set.

## Consequences

The change is limited to ship.js and tests/workflows/harness.js.

## How to reverse

Revert commit 0d7c790.
