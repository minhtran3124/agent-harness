---
ticket: 398
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0048. Dedupe does not carry owner_confirmed over from merged items

## Context

Merge rules cover confidence and needs_review but not owner_confirmed.

## Options

- Keep the kept item's own owner_confirmed value
- Set owner_confirmed if any merged item has it

## Decision

Keep the kept item's own value.

## Why

Carrying it over could hide a decision from review; needs_review carry-over already protects the reviewer.

## Consequences

A merged group can still produce an ADR if the kept item is not owner_confirmed.

## How to reverse

Add an any() over the group in dedupe.
