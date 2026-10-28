---
ticket: 397
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0037. Decisions carry a boundary flag in the ADR input

## Context

buildBody needs to tell boundary decisions apart; the flag is stored on each decision object that also goes to write_adrs.py and the artifact stage.

## Options

- Add a boundary field to the stored decision
- Match the title prefix in buildBody only

## Decision

Add boundary: boolean to stored decisions, as the plan says.

## Why

The plan names it. write_adrs.py reads only named keys, so the extra field is ignored there.

## Consequences

The artifact and ADR stages see one extra key.

## How to reverse

Remove the boundary property in takeDecisions and test the title prefix in buildBody.
