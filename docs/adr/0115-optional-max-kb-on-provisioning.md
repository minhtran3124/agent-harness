---
ticket: 472
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0115. Optional --max-kb on provisioning

## Context

The owner set the 5 MB limit; audit already has --max-kb.

## Options

- Fixed 5120 KB
- Default 5120 KB with an optional --max-kb flag

## Decision

Default 5120 KB with an optional --max-kb flag

## Why

This keeps parity with audit, and tests can use a tiny limit without writing 5 MB files.

## Consequences

One extra optional flag in the usage line.

## How to reverse

Remove the flag and hard-code 5120.
