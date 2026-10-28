---
ticket: 393
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0019. Test file mirrors merge-deny.test.sh, with exit 3 skipped

## Context

The owner decided the missing-jq case is skipped and noted, like merge-deny.test.sh. That test only skips the whole suite when jq is absent and has no exit 3 case.

## Options

- Skip-with-note only, as in merge-deny.test.sh
- Fake a PATH without jq to test exit 3

## Decision

Skip-with-note only, as in merge-deny.test.sh

## Why

Owner-confirmed decision 3.

## Consequences

Exit 3 is covered only by reading the script.

## How to reverse

Add a PATH-stripped test case later.
