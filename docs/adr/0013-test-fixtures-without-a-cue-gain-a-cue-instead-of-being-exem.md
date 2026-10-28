---
ticket: 382
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0013. Test fixtures without a cue gain a cue instead of being exempted

## Context

AGENT_OK ('Advises on things.') and the block-scalar fixture ('Does the alpha thing across two lines.') have no cue and would fail the new check.

## Options

- Add a cue to the fixtures
- Weaken the check for those cases

## Decision

Add a cue to both fixtures, as the owner confirmed.

## Why

Owner-confirmed decision 3, and it does not weaken the check.

## Consequences

None outside scripts/test_check_frontmatter_contract.py.

## How to reverse

Remove the added words from the fixtures.
