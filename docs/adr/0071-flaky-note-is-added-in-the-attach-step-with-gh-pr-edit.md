---
ticket: 414
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0071. Flaky note is added in the attach step with gh pr edit

## Context

A flaky result must add a note to the PR body; the PR is opened by stageFinish before attach runs.

## Options

- gh pr edit --body in the attach step
- Tell the finish agent to write the note into the body

## Decision

The attach step appends the note to the existing PR body with gh pr edit.

## Why

Attach already holds the result and runs after the PR exists; both actions share one failure-is-logged boundary.

## Consequences

Attach agent needs gh pr edit permission in the same call.

## How to reverse

Move the note into the finish prompt.
