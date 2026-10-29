---
ticket: 410
stage: intent
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0059. Auto mode: drafted Verify: row is a needs_review decision

## Context

In auto mode CONFIRM resolves itself

## Options

- Record the draft as a decision with needs_review true and append it to confirmed text
- Record with needs_review false

## Decision

Record with needs_review true and append the text to the ticket's confirmed text

## Why

Owner-confirmed answer 2; the row sets what verify checks, so a human should review it

## Consequences

An ADR is written and shown in the PR table

## How to reverse

Change the auto-mode bullet in SKILL.md
