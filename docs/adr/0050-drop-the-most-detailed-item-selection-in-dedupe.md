---
ticket: run
stage: intent-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-29
---

# 0050. Drop the most-detailed-item selection in dedupe

## Context

Owner rule for #398 is 'keep the highest confidence, ties to the first'; the code additionally preferred the most detailed item so an n/a placeholder never replaced real text.

## Options

- Follow the owner rule exactly (highest confidence, ties to first)
- Keep detail preference as the primary key and highest confidence as the tie-break

## Decision

Follow the owner rule exactly and remove the _detail helper.

## Why

The owner-confirmed rule names no detail criterion; adding one contradicts it.

## Consequences

A high-confidence duplicate with placeholder n/a fields can be kept over a detailed low-confidence one.

## How to reverse

Revert commit cd71fed.
