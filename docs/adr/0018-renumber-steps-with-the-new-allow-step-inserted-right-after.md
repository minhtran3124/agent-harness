---
ticket: 393
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0018. Renumber steps with the new allow step inserted right after step 3

## Context

The ticket says the new step goes 'after the deny rules'. Inserting it as step 4 shifts the ignore-specs and old-install steps to 5 and 6.

## Options

- Insert as step 4 and renumber the later steps
- Append as the last step (step 6)

## Decision

Insert as step 4 and renumber the later steps

## Why

Matches the ticket wording 'after the deny rules' and groups both permission steps.

## Consequences

Nothing else in the repo is known to reference step numbers; the plan stage will grep for 'step 4' and 'step 5' references before editing.

## How to reverse

Move the paragraph and renumber back.
