---
ticket: 382
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-28
---

# 0010. Cue regex is a case-insensitive whole-word match for use or when

## Context

Bare 'when' fails 14 of 22 existing descriptions.

## Options

- \bwhen\b only
- \b(use|when)\b case-insensitive

## Decision

CUE = re.compile(r'\b(use|when)\b', re.IGNORECASE)

## Why

Owner-confirmed decision 1.

## Consequences

'reuse', 'whenever' and 'user' alone do not count as a cue.

## How to reverse

Edit the CUE constant in scripts/check_frontmatter_contract.py.
