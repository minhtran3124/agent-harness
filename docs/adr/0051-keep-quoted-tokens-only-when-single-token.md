---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0051. Keep quoted tokens only when single-token

## Context

Quoted strings were deleted entirely, hiding quoted PR numbers and API paths

## Options

- Keep all quoted content
- Keep only quoted strings with no whitespace or separators
- Leave as is

## Decision

Keep only quoted strings with no whitespace or separators

## Why

Keeping all quoted text would let messages like --body "closes 7" be read as the PR number or an echo of the merge phrase match

## Consequences

Multi-word quoted strings are still ignored, so a quoted multi-word command is not detected

## How to reverse

Revert commit a7ae02c
