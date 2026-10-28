---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0052. Dedupe keeps lowest confidence; owner_confirmed needs all items

## Context

F7: dedupe kept the highest-confidence duplicate, so a low-confidence or non-owner-confirmed duplicate could be dropped, and a shared context string could merge different decisions.

## Options

- Keep lowest confidence, owner_confirmed only if all merged items are
- Keep highest confidence but OR needs_review and owner_confirmed
- Stop merging on shared context

## Decision

Keep the lowest-confidence item (ties to first), keep needs_review as OR, and set owner_confirmed false unless every merged item is owner-confirmed.

## Why

Errs toward surfacing an ADR for human review instead of hiding a doubtful decision; a minimal change that keeps the merge rules (slug or context) intact.

## Consequences

Merged groups with mixed confidence now produce an ADR where before they might not; the old test asserting highest-confidence was inverted.

## How to reverse

git revert 04d996d
