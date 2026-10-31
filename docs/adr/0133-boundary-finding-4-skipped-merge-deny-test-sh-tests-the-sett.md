---
ticket: run
stage: intent-fix
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-31
---

# 0133. Boundary: finding 4 skipped, merge-deny.test.sh tests the settings script, not the hook

## Context

Finding 4 asks for a case in tests/scripts/merge-deny.test.sh for each deny path of the hook (--auto, wrapped merge, gh api, GraphQL, gh alias, doubt paths). That file and merge-allow.test.sh test the setup scripts merge-deny.sh and merge-allow.sh, which merge permission rules into settings.json. They never run merge-guard.sh.

## Options

- Add hook cases to merge-deny.test.sh
- Keep the hook cases in tests/hooks/merge-guard.test.sh, which already has them

## Decision

Left merge-deny.test.sh unchanged. tests/hooks/merge-guard.test.sh already covers --auto, wrapped merges, gh api, GraphQL, gh alias and the doubt paths.

## Why

The wording of AC4 names the wrong test file. Adding hook cases there would test a different script and duplicate coverage. The AC5 line says merge-allow.test.sh must stay unchanged.

## Consequences

AC4 is met in tests/hooks/merge-guard.test.sh, not in the file the ticket names. A reviewer can read this as a mismatch with the ticket text.

## How to reverse

Add a small case to merge-deny.test.sh that runs merge-guard.sh for each deny path.
