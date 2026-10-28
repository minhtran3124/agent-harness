---
ticket: 398
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0046. No workflows/README.md edit; rule stated in SKILL.md and docs/adr/README.md only

## Context

The ticket names workflows/README.md, which does not exist on origin/feat/harness-v5-fixes.

## Options

- Create workflows/README.md
- State the rule only in SKILL.md and docs/adr/README.md

## Decision

Follow owner-confirmed decision 1: two places, no new file.

## Why

Owner-confirmed answer; I confirmed the file is absent with git ls-tree on origin/feat/harness-v5-fixes (no match for workflows/README.md in the grep over that tree listing).

## Consequences

None beyond the two docs.

## How to reverse

Add the file later.
