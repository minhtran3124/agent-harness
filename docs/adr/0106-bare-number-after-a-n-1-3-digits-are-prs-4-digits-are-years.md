---
ticket: 514
stage: intent
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-30
---

# 0106. Bare number after a #n: 1-3 digits are PRs, 4 digits are years

## Context

The ticket assumes this rule so '(#15, 2024)' keeps passing while '(#15, 999)' is validated.

## Options

- 1-3 digit bare numbers are PR numbers, 4 digits are years
- validate all bare numbers
- ignore all bare numbers

## Decision

1-3 digit bare numbers after a #n in a citation group are validated as PR numbers; 4-digit numbers are ignored as years.

## Why

Matches the owner's assumed rule and the existing year test; a PR number of 1000+ would be missed, which is acceptable for this repo.

## Consequences

A PR numbered 1000 or higher cited as a bare number is not validated.

## How to reverse

Change the digit-count bound in the token grammar in check_release_summary.py.
