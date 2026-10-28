---
ticket: 383
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0016. Place the checks in a new README section and a pointer in the compound skill's index paragraph

## Context

Owner said full detail in README, short pointer in SKILL.md under 600 words.

## Options

- New 'Checks' section in README, 2-3 sentences in SKILL.md after the rebuild command
- Inline in the schema block only

## Decision

New 'Checks' section in README plus the schema comment; short pointer in SKILL.md.

## Why

Keeps SKILL.md small (525 words now) and README as the single detail source.

## Consequences

None outside the two files.

## How to reverse

Revert the two files.
