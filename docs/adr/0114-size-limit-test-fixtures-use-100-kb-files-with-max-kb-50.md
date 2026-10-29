---
ticket: 472
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0114. Size limit test fixtures use 100 KB files with --max-kb 50

## Context

classify_repo measures size with du -sk, which rounds a small file up to one 4K block. The planned 3000-byte file with --max-kb 1 therefore flags every small config file as over the limit.

## Options

- use a 100 KB file with --max-kb 50
- change the size measure to bytes

## Decision

The new tests use a 100 KB big.db with --max-kb 50. The size measure is unchanged.

## Why

A byte measure would change the audit output the existing tests pin. The plan allows no such change.

## Consequences

Because du rounds up, --max-kb below 4 flags every file. The existing audit test only passed with --max-kb 1 because the other files in its fixture were already covered.

## How to reverse

Switch du to a byte count in classify_repo and update the test fixtures.
