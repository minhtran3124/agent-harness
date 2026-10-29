---
ticket: 462
stage: research
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: research)
date: 2026-10-29
---

# 0086. Reuse the request text fetched by intent review for UAT

## Context

requestText fetches the raw body through an agent; a second fetch costs an agent call per ticket.

## Options

- call requestText again for UAT
- cache the text from stageIntentReview and reuse it

## Decision

Cache the request text in a closure variable and reuse it for UAT.

## Why

Avoids an extra agent call and keeps the body identical for both stages.

## Consequences

requestText results are kept in memory for the run.

## How to reverse

Call requestText again in stageUat.
