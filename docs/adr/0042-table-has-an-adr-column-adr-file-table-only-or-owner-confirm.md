---
ticket: 398
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0042. Table has an ADR column: ADR file, table only, or owner-confirmed

## Context

The ticket asks for title, decision and why in the table, and that an owner-confirmed row says so.

## Options

- Title, decision, why, plus a column for the ADR status
- Only title, decision, why, with owner-confirmed appended to the why

## Decision

Columns Ticket, Title, Decision, Why, ADR; the last holds owner-confirmed, ADR file or table only.

## Why

A reviewer sees at a glance which rows have a file to read.

## Consequences

The PR body Decisions section is the existing ADR link list followed by this table.

## How to reverse

Change decisions_table in write_adrs.py.
