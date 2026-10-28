---
ticket: 382
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0011. Trigger cue is a word-bounded, case-insensitive match for use or when

## Context

The ticket text says the cue is 'Use when' or 'when'. Owner-confirmed decision 1 says a bare strict 'when' fails 14 of 22 descriptions.

## Options

- Require the literal phrase 'Use when'
- Require the word 'when' only
- Match \b(use|when)\b case-insensitively

## Decision

Match \b(use|when)\b with re.IGNORECASE, as the owner confirmed.

## Why

Owner-confirmed. It accepts 'Use this agent to ...', 'Use only after ...' and 'Use when ...', which are existing house phrasing, and still rejects words such as reuse, user and whenever through the word boundary.

## Consequences

The check is deliberately loose: it proves a routing cue word is present, not that the description routes well. A description that says 'use' in a non-cue sense would pass.

## How to reverse

Change the CUE regex in scripts/check_frontmatter_contract.py and the matching tests.
