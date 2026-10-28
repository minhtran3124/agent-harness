---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0055. Docs drop the ticket-lists-tests rule

## Context

docs/workflows.md repeated the rule that tests and docs are in bounds only when the ticket lists them, which contradicts the proving-test exemption.

## Options

- Update docs to match the prompts
- Leave docs and change the prompts back

## Decision

Update docs to match the prompts

## Why

The run-level fix prompt already allows the proving test, and the finding calls for one rule everywhere.

## Consequences

Docs no longer say docs files are in bounds only when listed; the file set now limits production files only.

## How to reverse

git revert c0c120c
