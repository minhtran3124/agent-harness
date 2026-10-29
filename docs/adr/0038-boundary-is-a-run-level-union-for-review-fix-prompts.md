---
ticket: 397
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0038. Boundary is a run-level union for review-fix prompts

## Context

Review-fix and intent-fix run once per run on the combined final branch, not per ticket, but out_of_scope and files come per ticket from the intent stage.

## Options

- Union of files and concatenated out_of_scope lines across all done tickets, labelled by ticket
- Run fixes per ticket

## Decision

Use the union, labelled by ticket number.

## Why

Fix stages already operate on the final merged branch; per-ticket fixing would change the pipeline shape.

## Consequences

A fix touching ticket A's file for a finding that belongs to ticket B is allowed; stricter attribution is not attempted.

## How to reverse

Replace the union with a per-ticket map in fixAgent.
