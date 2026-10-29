---
ticket: 437
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0077. Place the skip rule as the first line of Start config

## Context

Skip rule must be pinnable by a text test and read before steps 1 to 5.

## Options

- Put the rule in the type table
- Put the rule as the first line of Start config and Login

## Decision

Put the rule as the first line under Start config, stating it also covers Login; keep the type table rows unchanged.

## Why

Smallest word cost, and the agent reads it right before the steps it gates.

## Consequences

Test pins the phrase 'never read, create or commit' in that section.

## How to reverse

Move the sentence elsewhere in SKILL.md and adjust the grep in the test.
