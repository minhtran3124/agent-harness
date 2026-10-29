---
ticket: 473
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0120. Mark clones with .git/harness-sandbox-source for reuse detection

## Context

A clone's origin is the real URL, so reuse cannot be matched to the main repo by remote.

## Options

- Compare origin URLs
- Marker file in the clone's .git holding the source repo path
- Only check that .git exists

## Decision

Write the source repo's absolute path to .git/harness-sandbox-source; reuse only on a match, otherwise exit 1.

## Why

Reliable and invisible to git status.

## Consequences

Hand-made clones at that path are not reused.

## How to reverse

Drop the marker and match another way.
