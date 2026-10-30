---
ticket: 511
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-30
---

# 0104. Match rule also accepts Refs #n

## Context

The owner-confirmed rule keeps a PR only on title #n or Closes/Fixes/Resolves #n. PRs #384 and #385 only say 'Refs #381' and 'Refs #382', so the rule alone cannot meet the required Verify result (#384, #385 found).

## Options

- Strict rule (Closes/Fixes/Resolves only), Verify fails
- Add Refs to the keyword list
- Accept any #n mention

## Decision

Add Refs to the keyword list.

## Why

Needed to satisfy the owner's Verify outcome; Refs #n is an explicit reference, and unrelated PR #361 (bare '393' without #) is still rejected.

## Consequences

A PR that only references an issue with Refs is attributed to it in the tickets mapping; integration PR #387 also matches.

## How to reverse

Remove Refs from fact-list-schema.md and the test assertion.
