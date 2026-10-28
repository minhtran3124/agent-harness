---
ticket: 383
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0015. Describe the frontmatter-contract check by what it actually verifies

## Context

Ticket frames both commands as documentation checks for solutions, but on origin/feat/dogfood-352 scripts/check_frontmatter_contract.py validates skill and agent frontmatter (name, description, trigger cue), not docs/solutions records; only rebuild_solution_index.py --check enforces applicable_when.

## Options

- Describe each check by its real scope
- Imply both check solution records

## Decision

Describe each check by its real scope; applicable_when enforcement is attributed only to the index check.

## Why

Accurate docs; the owner-confirmed decision only requires both commands named.

## Consequences

README has two short bullets with different scopes.

## How to reverse

Edit the Checks section wording.
