---
ticket: 545
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-31
---

# 0129. Ask only for the one-merge, plain-form case; mode allowlist

## Context

Which payloads may reach the prompt.

## Options

- Ask for any non-feat merge
- Ask only for one plain gh pr merge, the only merge in the command

## Decision

Ask only when ASKS==1 and total merge segments==1, form is `gh pr merge` with one PR, mode in default/acceptEdits/auto/bypassPermissions, no agent_id. gh api, several PRs, chains (even with a feat merge) and all other forms stay denied. Unknown base names (v5.0.0, hotfix/x) stay denied unless they are the repo default branch.

## Why

Matches AC2-AC4 and the out-of-scope lines (one PR at a time, no subagent merges).

## Consequences

gh pr view now always requests baseRefName,headRefOid and the output must be exactly two words with a 40-hex head, also for feat/* (a malformed answer is a deny as before). The test stub gh was extended accordingly. Old tests that expected deny for a plain merge into main were changed to expect ask (brace group, quoted --subject, quote-split gh word); same intent, new outcome.

## How to reverse

Revert the ASKS/MERGES block at the end of merge-guard.sh.
