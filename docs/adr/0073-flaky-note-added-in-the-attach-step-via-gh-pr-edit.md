---
ticket: 414
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0073. Flaky note added in the attach step via gh pr edit

## Context

The PR exists only after stageFinish; a flaky result must add a note to its body.

## Options

- gh pr edit in the attach agent
- Finish prompt writes the note

## Decision

The attach agent appends the note with gh pr edit.

## Why

Attach holds the result and runs after the PR exists; one failure boundary covers both actions.

## Consequences

Attach agent needs gh pr edit in the same call.

## How to reverse

Move the note into the finish prompt.
