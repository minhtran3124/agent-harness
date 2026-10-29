---
ticket: 397
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0035. Steps 1-3 committed together

## Context

Steps 1, 2 and 3 all edit only ship.js and share the boundaryOf helper and the boundaries state, so splitting them into separate commits would have left intermediate commits with unused code.

## Options

- One commit per step
- One commit for steps 1-3

## Decision

One commit for steps 1-3, then one each for the tests and the docs.

## Why

The three steps are one change to one file and were verified together.

## Consequences

Three commits instead of five.

## How to reverse

git revert 423f34a
