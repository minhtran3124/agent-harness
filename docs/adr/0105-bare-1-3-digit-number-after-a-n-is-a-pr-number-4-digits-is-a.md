---
ticket: 514
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-30
---

# 0105. Bare 1-3 digit number after a #n is a PR number; 4+ digits is a year

## Context

Ticket gap 2: '(#15, 999)' must fail but '(#15, 2024)' must pass.

## Options

- 1-3 digits is a PR, 4+ is a year
- ignore all bare numbers

## Decision

1-3 digit bare numbers after the first #n in a group are validated as PRs; 4+ digits ignored.

## Why

Matches the owner-stated assumed rule.

## Consequences

A PR number of 1000 or more cited bare would be ignored.

## How to reverse

Change the len(digits) <= 3 check in citations().
