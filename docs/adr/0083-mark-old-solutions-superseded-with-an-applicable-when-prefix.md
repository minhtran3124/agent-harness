---
ticket: 464
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0083. Mark old solutions superseded with an applicable_when prefix and a superseded_by field

## Context

The ticket says to mark two solution docs superseded by the ticket-464 ADR, which does not exist yet and has no number.

## Options

- Set supersedes on the ADR later
- Prefix applicable_when and add superseded_by now

## Decision

Prefixed applicable_when with 'SUPERSEDED by the ticket #464 ADR' and added a superseded_by frontmatter line; INDEX rebuilt.

## Why

The index shows applicable_when, so the marker is visible; the ADR number is unknown until the later stage.

## Consequences

The later ADR stage may replace the placeholder with the real ADR number.

## How to reverse

Remove the prefix and the superseded_by line, rebuild the index.
