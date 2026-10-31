---
ticket: run
stage: fix
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-30
---

# 0116. Marker for to-be-created paths and symbols: text marker (new), not a schema field

## Context

Ground-check must not fail a plan or design that names files or symbols it will create. The ticket's open question asks whether to use a schema field or a text marker.

## Options

- Schema field on the plan/design
- Text marker '(new)' after the path or symbol, parsed by ground-check.sh

## Decision

Use the text marker '(new)', implemented in plugins/harness/scripts/ground-check.sh and described in skills/README.md.

## Why

The input is markdown written by agents; a text marker needs no schema change to templates or ship.js and the checker reads it directly.

## Consequences

Authors must write (new) after each path or symbol they will create; an unmarked missing claim fails the ground stage.

## How to reverse

Replace the (new) parsing in ground-check.sh with a schema field and update templates/specs/design.md and plan.md.
