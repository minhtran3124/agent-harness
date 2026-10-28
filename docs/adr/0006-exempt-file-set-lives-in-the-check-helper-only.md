---
ticket: 381
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0006. Exempt-file set lives in the --check helper only

## Context

Owner says README.md is exempt from the applicable_when requirement but stays in the index; INDEX.md and critical-patterns.md are already skipped by build().

## Options

- Separate exempt set in the check helper (README.md added there only)
- Change build() to skip README.md as well

## Decision

Separate exempt set in the check helper; build() unchanged

## Why

Keeps README.md in the index as owner confirmed, and leaves INDEX.md output byte-identical.

## Consequences

Two places name skip lists (build skip set and check exempt set); small duplication.

## How to reverse

Move the set to a shared constant or remove README.md from the exempt set.
