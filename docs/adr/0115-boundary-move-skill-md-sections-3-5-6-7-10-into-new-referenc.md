---
ticket: 539
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-31
---

# 0115. Boundary: move SKILL.md sections 3, 5, 6, 7, 10 into new references/process.md

## Context

The ticket's verbatim SKILL.md is 1009 words. scripts/audit_skill_prompts.py enforces a 600-word ceiling, which failed the run-tests test_real_repository_matches_expected_surface_shape. The ticket's file list names only feature.md, bug.md and docs.md under references/.

## Options

- Move whole sections to a new references/process.md and leave one-line pointers
- Cut the SKILL.md text in place to 600 words

## Decision

Created plugins/harness/skills/tickets/references/process.md holding Split, Self-check, Duplicates, Labels and Re-run verbatim. SKILL.md keeps pointers and a few trimmed default-behavior sentences, ending at 600 words.

## Why

The repo's deletion-test doc says to move branch-only blocks to references/. This keeps the rule text whole instead of shortening condition sentences. The ticket's Notes say to follow what the lint scripts report.

## Consequences

The skill now has a fourth reference file, which the ticket's file tree does not list.

## How to reverse

Inline process.md back into SKILL.md and cut words some other way, or raise the ceiling for this skill.
