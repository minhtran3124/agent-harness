---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0054. needs_review wins over owner_confirmed

## Context

owner_confirmed suppressed the ADR file even when needs_review was true. The table then said owner-confirmed while the PR section had no entry for a decision flagged for review.

## Options

- needs_review always yields an ADR file and an ADR file table row
- keep suppression and show owner-confirmed with a needs-review marker in the table

## Decision

needs_review always yields an ADR file; owner_confirmed only skips the file when needs_review is false.

## Why

A decision flagged for review must not be hidden. This keeps the file, the table and the PR section consistent with the smallest change.

## Consequences

The owner-confirmed marker appears only for decisions without a file. The ship.js prompt text 'Such a decision gets no ADR file' is now slightly broader than the behaviour. Because ship.js sets needs_review false for restated owner answers, this rarely matters.

## How to reverse

git revert 3935e7d
