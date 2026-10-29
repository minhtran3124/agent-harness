---
ticket: 405
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0058. Do not add the script to run-tests.sh

## Context

Ticket asks only for CI, lintCmd and the test; run-tests already covers lint-skill-bash.

## Options

- Add an L1 step to run-tests.sh
- Leave run-tests.sh alone

## Decision

Leave run-tests.sh alone; the new test in tests/scripts/ is picked up by glob.

## Why

Keeps the change minimal; lintCmd for autopilot is lint-doc-truth.sh per owner, and CLAUDE.md names the script for manual or extra use.

## Consequences

The autopilot lintCmd will not run shellcheck unless a later ticket adds it.

## How to reverse

Add an L1 block calling bash scripts/check-shellcheck.sh to run-tests.sh.
