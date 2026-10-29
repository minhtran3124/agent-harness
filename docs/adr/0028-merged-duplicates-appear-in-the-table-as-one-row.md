---
ticket: 398
stage: plan
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0028. Merged duplicates appear in the table as one row

## Context

The owner defined the merge for ADR files; the ticket says the table lists all 6 decisions of the test case, which contains 2 near-duplicates.

## Options

- Table lists the deduped decisions (one row per merged group)
- Table lists every raw decision, including merged-away ones

## Decision

Dedupe first, then filter and table the same deduped list; the test states the expected row count (5) explicitly.

## Why

Repeated rows are the noise the ticket removes; 'all 6' is read as all distinct decisions.

## Consequences

The 6-decision test shows 5 rows. If the owner wants 6 rows the table step must take the raw list.

## How to reverse

Pass the raw decisions to decisions_table instead of the deduped list.
