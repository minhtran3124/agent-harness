---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: review-fix)
date: 2026-10-28
---

# 0025. Preserve mode and symlinks with cp -p and readlink instead of writing in place

## Context

mktemp+mv turned the file mode into 0600, replaced a symlink with a regular file, and left a temp file if mv failed.

## Options

- Write in place with cat > file (not atomic)
- Resolve symlinks with a readlink loop, cp -p the old file onto the temp file, and use an EXIT trap

## Decision

Resolve symlinks with a readlink loop, cp -p the old file onto the temp file, and use an EXIT trap

## Why

It keeps the atomic rename and works on bash 3.2, macOS and Linux. readlink -f and chmod --reference are not portable.

## Consequences

A new file gets mode 0644. A symlink chain is followed up to 20 hops.

## How to reverse

git revert e8414ec
