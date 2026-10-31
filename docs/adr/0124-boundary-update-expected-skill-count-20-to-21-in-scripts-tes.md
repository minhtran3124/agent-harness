---
ticket: 539
stage: implement
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-31
---

# 0124. Boundary: update expected skill count 20 to 21 in scripts/test_audit_skill_prompts.py

## Context

test_real_repository_matches_expected_surface_shape hard-codes the number of skills. A 21st skill makes it fail, and AC4 needs ALL GREEN. The test file is not in the ticket's file list.

## Options

- Change the expected count to 21
- Leave the test failing

## Decision

Changed the single assertion from 20 to 21.

## Why

Adding a skill changes the count by design. This is not a weakened test.

## Consequences

One line changed in a test file outside the named list.

## How to reverse

Revert commit 91d87a2a.
