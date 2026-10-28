---
ticket: 383
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-28
---

# 0014. Qualify repo-only script path in compound SKILL.md

## Context

doc-truth lint rejects a plugin doc naming scripts/check_frontmatter_contract.py, which exists only in the harness repo, not the plugin.

## Options

- Add 'in the harness repo' near the path
- Drop the command from SKILL.md

## Decision

Add 'in the harness repo' near the path

## Why

Ticket requires both commands named in SKILL.md; the lint accepts that wording.

## Consequences

Consuming repos are told the second check is harness-repo only.

## How to reverse

Edit the sentence in plugins/harness/skills/compound/SKILL.md.
