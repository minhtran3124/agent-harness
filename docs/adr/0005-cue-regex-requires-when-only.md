---
ticket: run
stage: intent-fix
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-28
---

# 0005. Cue regex requires 'when' only

## Context

The request named the cue as 'Use when' / 'when'. The code accepted 'use' or 'when', and the comment justified that with 14 of 22 descriptions using 'Use ...' without 'when'.

## Options

- Require 'when' only
- Keep 'use' or 'when'
- Require the phrase 'Use when'

## Decision

CUE = \bwhen\b, case-insensitive. 'Use when' satisfies it, and so does a bare 'when'.

## Why

This matches the owner's wording, 'Use when / when'. Requiring the exact phrase 'Use when' would reject the bare 'when' form that the request allows.

## Consequences

Descriptions that only say 'Use ...' now fail.

## How to reverse

Change the CUE regex back to \b(use|when)\b.
