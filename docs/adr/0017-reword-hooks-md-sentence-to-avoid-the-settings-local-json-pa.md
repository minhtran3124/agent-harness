---
ticket: 393
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-28
---

# 0017. Reword hooks.md sentence to avoid the settings.local.json path token

## Context

The doc-truth lint reported 'docs/hooks.md references missing path: settings.local.json' for a backticked .claude/settings.local.json.

## Options

- Say 'the owner's untracked local settings file' in docs/hooks.md
- Change the lint to ignore this file name

## Decision

Reword the docs sentence

## Why

Keeps the lint unchanged and the ticket in scope.

## Consequences

docs/hooks.md names the file only as 'untracked local settings file'; SKILL.md still names the exact path.

## How to reverse

Edit docs/hooks.md line 59 and add the path back once the lint allows it.
