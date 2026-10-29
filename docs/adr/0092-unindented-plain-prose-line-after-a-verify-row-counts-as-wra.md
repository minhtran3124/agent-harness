---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0092. Unindented plain-prose line after a Verify row counts as wrapped Verify text

## Context

The old rule ended a Verify row at the first unindented line, so soft-wrapped Verify text leaked into the blind UAT prompt.

## Options

- End the row only at a blank line
- Continue through deeper-indented lines and plain-prose lines; end at a bullet, heading or Label: line at the row's level

## Decision

Continue through deeper-indented lines and plain-prose lines; end at a blank line, bullet, heading or Label: line at the row's level.

## Why

It closes the leak while keeping tight AC bullets and 'AC2: ...' lines under a Verify row in the prompt.

## Consequences

An unlabelled plain-prose AC line directly after a Verify row, with no blank line, is stripped from the UAT prompt.

## How to reverse

Revert the stripVerify change in plugins/harness/workflows/ship.js.
