---
ticket: run
stage: fix
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-30
---

# 0117. Boundary: ADR file under docs/adr/ is written by the ADR stage, not the fix stage

## Context

The intent review gap asks for an ADR in this diff. The run rules say fix stages never write ADR files and one stage at the end writes them from decisions[].

## Options

- Write docs/adr/NNNN-*.md in the fix commit
- Return the decision in decisions[] and let the ADR stage write it

## Decision

Skip writing the ADR file; return the text-marker choice as a needs_review decision so the ADR stage writes it.

## Why

The rule 'Never write ADR files' applies; the ticket's file list also says docs/adr/ is written by the ADR stage.

## Consequences

The ADR appears when the ADR stage runs; the fix commit has no docs/adr change.

## How to reverse

Add the ADR by hand if the ADR stage does not write it.
