---
ticket: 462
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0085. UAT fix gets its own phase label and runs serially

## Context

fixAgent hard-codes phase 'Review'.

## Options

- add an optional phase parameter to fixAgent, default 'Review'
- copy fixAgent as uatFixAgent

## Decision

Add an optional phase parameter to fixAgent (default 'Review') and pass 'UAT'.

## Why

Avoids duplicating the fix prompt; the existing callers keep their behaviour.

## Consequences

A small signature change in a private helper; intent-fix and review fixes are unchanged.

## How to reverse

Revert the parameter.
