---
ticket: 397
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0036. A skipped fix is always a boundary decision

## Context

The plan says a skipped fix gets needs_review true and a Boundary: prefix. A fix agent may skip a fix for a reason unrelated to the boundary.

## Options

- Prefix and flag only decisions the agent already titled Boundary:
- Prefix and flag every decision from a result with fix_status skipped

## Decision

Every decision from a result with fix_status skipped gets needs_review true and the Boundary: prefix if it lacks one.

## Why

Follows plan step 3 literally; a skipped fix is something the owner should see.

## Consequences

A fix skipped for a non-boundary reason that also returns a decision is shown under Needs your decision and in the Review section.

## How to reverse

Drop the skippedFix handling in takeDecisions in ship.js.
