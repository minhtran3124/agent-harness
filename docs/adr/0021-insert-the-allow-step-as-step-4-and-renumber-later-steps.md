---
ticket: 393
stage: plan
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: plan)
date: 2026-10-28
---

# 0021. Insert the allow step as step 4 and renumber later steps

## Context

The ticket says the new step goes after the deny rules; later steps shift to 5 and 6. A grep of the repo found no other references to setup step numbers.

## Options

- Insert as step 4 and renumber
- Append as the last step

## Decision

Insert as step 4 and renumber

## Why

Matches the ticket wording and groups both permission steps.

## Consequences

Old-install and ignore-specs become steps 6 and 5.

## How to reverse

Move the paragraph and renumber.
