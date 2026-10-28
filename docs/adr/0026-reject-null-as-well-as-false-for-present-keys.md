---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-28
---

# 0026. Reject null as well as false for present keys

## Context

has() treats a present key with null as present, so null permissions/allow/deny now also exit 2 (previously silently replaced).

## Options

- has()-based strict check
- only reject false

## Decision

has()-based strict check

## Why

Matches the documented exit-2 contract: a wrong-typed value is never silently overwritten.

## Consequences

A settings file with an explicit null for these keys now exits 2 instead of being rewritten.

## How to reverse

Revert the commit or add `and . != null` handling in the guard.
