---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0056. Widen the skipped-fix needs-decision match to any needs_review decision

## Context

The deterministic skippedFix fallback was removed, so only a Boundary: titled decision flagged a skipped fix for the user.

## Options

- Match any decision with needs_review true or contradicts_confirmed or dangerous, plus the Boundary prefix
- Restore a deterministic skipped-fix fallback that flags every skipped fix

## Decision

Match any decision with needs_review true or contradicts_confirmed or dangerous, plus the Boundary prefix

## Why

It keeps test o2 (a skipped fix with a needs_review false decision is not forced to review) while stopping unprefixed review-needed decisions from being lost.

## Consequences

A skipped fix with a needs_review true decision now shows 'needs your decision: <title>' in the Review section.

## How to reverse

git revert 20bd679d02091124e21d34bf089dcec09f0f259d
