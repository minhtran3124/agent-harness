---
ticket: 414
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0069. Attach stage uses the PR comment body 'Verify evidence for #n: <result>'

## Context

gh pr comment needs a body alongside --attach.

## Options

- Short fixed body
- Embed the verify report

## Decision

Short fixed body naming the ticket and result; the flaky note is appended to the PR body with gh pr edit.

## Why

Keeps the comment small; the full report is already on the issue when verify fails.

## Consequences

The PR shows the GIF and a one-line result.

## How to reverse

Edit the stageAttach prompt in ship.js.
