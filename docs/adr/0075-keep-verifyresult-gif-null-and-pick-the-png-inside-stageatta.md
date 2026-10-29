---
ticket: 427
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0075. Keep verifyResult.gif null and pick the PNG inside stageAttach

## Context

The ticket needs a PNG fallback when there is no GIF. The report line 'GIF: built and attached' and tests vb1-vb5 read verifyResult.gif.

## Options

- Compute the fallback in stageAttach and leave verifyResult.gif null
- Store the chosen PNG in verifyResult.gif

## Decision

Compute the fallback in stageAttach and leave verifyResult.gif null

## Why

This matches owner decision 1 (the script picks the PNG), does not change the report text or the vb tests, and keeps the GIF/PNG distinction.

## Consequences

With a PNG attached, the ADR report line still says 'GIF: not built' or 'not attached', and that is correct for the GIF but does not mention the PNG. This is not touched in this ticket.

## How to reverse

Change the report text in ship.js around line 771 to show a PNG when it is attached.
