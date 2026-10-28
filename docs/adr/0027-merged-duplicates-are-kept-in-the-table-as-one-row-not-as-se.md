---
ticket: 398
stage: intent
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0027. Merged duplicates are kept in the table as one row, not as several

## Context

The owner defined the merge for ADR files; the ticket says the table lists all 6 decisions of the test case, which contains 2 near-duplicates.

## Options

- Table lists the deduped decisions (one row per merged group)
- Table lists every raw decision, including the merged-away ones

## Decision

Dedupe first, then filter and table the same deduped list; the test states the expected row count explicitly.

## Why

Repeated rows are the noise the ticket removes; the acceptance line 'lists all 6' is read as all distinct decisions, and the ambiguity is named in the test.

## Consequences

The 6-decision test shows 5 rows. If the owner wants 6 rows the table step must take the raw list.

## How to reverse

Pass the raw decisions instead of the deduped list to decisions_table.
