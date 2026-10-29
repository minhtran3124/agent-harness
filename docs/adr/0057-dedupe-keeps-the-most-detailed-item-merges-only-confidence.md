---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0057. Dedupe keeps the most detailed item, merges only confidence

## Context

Dedupe kept the whole lowest-confidence item, so an n/a placeholder duplicate could replace a detailed high-confidence decision.

## Options

- Keep the most detailed item and set its confidence to the group's lowest
- Field-by-field merge preferring non-placeholder text

## Decision

Keep the most detailed item (count of non-n/a fields; tie goes to lower confidence, then first) and set its confidence to the lowest in the group.

## Why

Smallest change that stops placeholder text replacing real text and keeps the doubtful-duplicate signal; existing tie behaviour is unchanged.

## Consequences

Merged ADR text comes from one item, not a blend. The decision-record SKILL.md merge rule was reworded to match.

## How to reverse

git revert 71d637c
