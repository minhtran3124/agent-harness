---
ticket: 382
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-28
---

# 0009. Edit five skill/agent descriptions to add a 'Use when' clause

## Context

The new cue check fails 5 existing descriptions (autopilot, diagnosing-bugs, finishing-a-development-branch, setup, implementer). The epic says not to edit descriptions.

## Options

- Add a minimal 'Use when ...' clause to the 5 descriptions
- Exempt those 5 files in the checker
- Loosen the cue so they pass

## Decision

Add a minimal 'Use when ...' clause to each of the 5 descriptions, changing only the description line (autopilot trimmed to stay under the word ceiling).

## Why

Owner-confirmed decision 2; keeps the check strict with no allowlist.

## Consequences

Five descriptions change wording, which can affect how the model routes to those skills.

## How to reverse

Revert commits 86f5954 and 0728e78 and relax the check, or add an allowlist.
