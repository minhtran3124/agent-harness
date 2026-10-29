---
ticket: 397
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0039. Needs your decision section lists boundary decisions via a flag on the decision record

## Context

The section must list needs_review decisions from the boundary rule, but decisions[] also holds unrelated needs_review entries (design forks, skipped review).

## Options

- List every needs_review decision
- List only decisions created by the boundary rule (marked by stage review-fix/intent-fix/implement and a boundary marker)

## Decision

List only boundary-rule decisions, identified by a boundary: true marker set by ship.js when a fix returns skipped with a needs_review decision.

## Why

Ticket text and owner decision 4 name only boundary decisions; other needs_review items already reach owners through ADRs.

## Consequences

Other needs_review decisions are not duplicated in the PR top section.

## How to reverse

Drop the boundary filter in buildBody.
