---
ticket: run
stage: review-fix
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-31
---

# 0117. Boundary: F2 fix touches process.md and a test, both outside the named file set

## Context

Finding F2 says step 6 of plugins/harness/skills/tickets/references/process.md uses a fuzzy `gh issue list --search` for duplicate detection. It should fetch issue bodies and compare the `source:` line exactly. Otherwise a re-run can create duplicates. The ticket's file list names SKILL.md, feature.md, bug.md, docs.md, skills/README.md, CHANGELOG.md, VERSION and plugin.json. It does not name process.md or any test file.

## Options

- Skip and flag as a boundary issue
- Edit process.md and add a test anyway

## Decision

Skip and change nothing

## Why

The stage rules say a fix that touches a file outside the named set must change nothing and return a Boundary decision. Both process.md and the test the fix requires are outside that set.

## Consequences

Re-running the tickets skill can still create duplicate issues until process.md step 6 is fixed. The owner should add process.md and a test file to the ticket's file set and re-run this fix.

## How to reverse

Add process.md and a test file to the ticket's named files, then re-run the fix stage.
