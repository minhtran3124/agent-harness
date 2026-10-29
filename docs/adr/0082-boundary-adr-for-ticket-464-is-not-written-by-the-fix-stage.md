---
ticket: run
stage: intent-fix
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-29
---

# 0082. Boundary: ADR for ticket #464 is not written by the fix stage

## Context

Finding 1 asks for a file under docs/adr/. The stage rules say never write ADR files and return decisions[] instead, and docs/adr/ is not in the ticket's file set. The solution entries already say the ADR is 'written by the ship workflow's ADR stage'.

## Options

- Write docs/adr/0080 in this stage
- Skip and return the decision so the final ADR stage writes it

## Decision

Skipped writing the ADR file. Record in the final ADR stage: ticket #464 removed techstacks/ and agents/PROJECT.md. Project rules now come from the repo's own CLAUDE.md, CLAUDE.local.md and .claude/rules, read through the single rulesCommon(repoDir) text in ship.js. This supersedes techstacks-project-owned-stack-profiles and scaffold-template-instance-parity.

## Why

The stage rules forbid writing ADR files here, and docs/adr/ is outside the allowed file set. The ADR stage writes it from decisions[], which fixes the dangling '#464 ADR' references.

## Consequences

The pointers in docs/solutions/INDEX.md and the two solution entries resolve only after the ADR stage runs.

## How to reverse

Write the ADR by hand in docs/adr/ if the ADR stage does not run.
