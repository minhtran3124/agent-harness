---
ticket: 382
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0012. Cue-less description reports a separate message and only when the description is non-empty

## Context

The checker already reports missing and empty descriptions. A cue message on an absent or empty description would be noise.

## Options

- Report the cue failure also for missing or empty descriptions
- Report it only for non-empty descriptions

## Decision

Report the cue failure only when the description is non-empty, as one extra 'frontmatter: <rel> description has no trigger cue ...' line.

## Why

One cause gives one line, and the existing tests that assert on 'missing' and 'empty' messages stay unchanged.

## Consequences

None for other tickets.

## How to reverse

Move the cue check outside the non-empty branch in check().
