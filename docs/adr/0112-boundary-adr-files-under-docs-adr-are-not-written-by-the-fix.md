---
ticket: run
stage: intent-fix
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-30
---

# 0112. Boundary: ADR files under docs/adr/ are not written by the fix stage

## Context

Intent review asked for an ADR for the fail-closed guard (H) and a record of the spike outcome (E). Rules say never write ADR files, and docs/adr/ is not in the ticket's file list.

## Options

- Write docs/adr files in this commit
- Return needs_review decisions so the final ADR stage writes the files

## Decision

Return needs_review decisions (below); change nothing in the branch.

## Why

needs_review is the only mechanism that creates an ADR file, and the boundary forbids touching docs/adr/. docs/hooks.md already cites 'ADR: fail-closed merge guard', which the ADR stage will produce from the decision below.

## Consequences

The cited ADR exists only after the final ADR stage runs.

## How to reverse

Add the ADR files by hand under docs/adr/.
