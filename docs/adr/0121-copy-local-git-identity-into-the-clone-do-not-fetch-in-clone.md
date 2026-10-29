---
ticket: 473
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0121. Copy local git identity into the clone; do not fetch in clone mode

## Context

git clone does not carry the main repo's local user.name/email, and --remote in worktree mode triggers a fetch.

## Options

- Do nothing
- Copy local user.name and user.email when set; use --remote only for the URL and skip fetch

## Decision

Copy local identity when set; in clone mode --remote only selects the URL source and nothing is fetched.

## Why

Commits inside the sandbox work, and the clone is built from committed local content as the owner asked.

## Consequences

Clone mode ignores remote freshness.

## How to reverse

Remove the config copy or add a fetch.
