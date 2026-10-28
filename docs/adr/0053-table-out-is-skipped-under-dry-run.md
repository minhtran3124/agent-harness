---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0053. --table-out is skipped under --dry-run

## Context

--dry-run is documented as 'print the plan, write nothing', but --table-out was written anyway.

## Options

- Skip --table-out on --dry-run
- Keep writing the table on --dry-run and update the help text

## Decision

Skip --table-out on --dry-run and write it only after the overwrite checks pass.

## Why

This matches the documented dry-run contract and avoids leaving a table behind when the run exits 2.

## Consequences

A caller that needs the table from a dry run no longer gets it. I found no caller that does, but I did not search every script.

## How to reverse

git revert 9c44b17
