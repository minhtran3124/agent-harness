---
ticket: 397
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0040. Boundary decisions are identified by a 'Boundary: ' title prefix and a boundary flag

## Context

buildBody must list only boundary-rule decisions, not every needs_review decision; implement-stage decisions cannot be marked by a skipped fix.

## Options

- Title prefix 'Boundary: ' required by the prompt, plus ship.js sets boundary: true and the prefix when a fix returns skipped
- Add a boundary field to the DECISION schema
- List every needs_review decision

## Decision

Use the title prefix and a ship.js-set boundary flag; no schema change.

## Why

Covers implement, review-fix and intent-fix with one mechanism, and avoids changing the shared DECISION contract.

## Consequences

An agent that forgets the prefix on an implement-stage decision is not listed in the top section; a skipped fix is always listed.

## How to reverse

Remove the prefix filter in buildBody and takeDecisions.
