---
ticket: 464
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0099. Delete agents/README.md and agents/ only if nothing else needs them

## Context

The ticket allows deleting agents/README.md and the agents/ folder 'if nothing else needs them'. AGENTS.md:12 references the folder, and lint-doc-truth.sh lints the repo's own agents/*.md.

## Options

- Delete agents/ entirely
- Keep agents/README.md

## Decision

Check for remaining readers first. If none remain beyond AGENTS.md and the lint comments, delete agents/ and update AGENTS.md lines 12 and 19. Otherwise keep README.md only.

## Why

The ticket leaves this open, and the repo's own agents/ files are not shipped by the plugin.

## Consequences

The lint comment and the frontmatter exception for PROJECT*.md get simplified.

## How to reverse

git restore agents/README.md.
