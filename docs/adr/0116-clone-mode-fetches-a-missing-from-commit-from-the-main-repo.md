---
ticket: 473
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0116. Clone mode fetches a missing --from commit from the main repo by sha

## Context

git clone --local copies branches and tags. A ref that exists only as a remote-tracking ref or a detached commit in the main repo may be absent from the clone.

## Options

- Fail if the clone lacks the commit
- Run a local fetch of the sha from the main repo, then check out

## Decision

If the clone lacks the commit, run 'git fetch <repo> <sha>' from the main repo (a local fetch, not a network fetch), then check out.

## Why

Keeps --from working for any ref committed in the main repo, as the owner-confirmed decision requires, without touching the network.

## Consequences

A clone can hold one extra fetched object set. Nothing in the main repo changes.

## How to reverse

Delete the 'cat-file -e ... || git fetch' line in the clone branch.
