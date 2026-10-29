---
ticket: 474
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0123. Young sandbox with no PR shows 'in progress'

## Context

The ticket lists four states (running, PR open, merged, abandoned). A sandbox with no PR, not running and 7 days old or younger fits none of them.

## Options

- show 'in progress'
- show unknown

## Decision

Show 'in progress'. Unknown stays for gh failures or an unreadable created_at.

## Why

Unknown means clean skips the sandbox because the state could not be read. A young sandbox with no PR is a known state.

## Consequences

--run and --older can select 'in progress' sandboxes.

## How to reverse

Change the fallback in sb_classify.
