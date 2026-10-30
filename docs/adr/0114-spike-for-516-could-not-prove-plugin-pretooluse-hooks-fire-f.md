---
ticket: run
stage: intent-fix
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-30
---

# 0114. Spike for #516 could not prove plugin PreToolUse hooks fire for Workflow agents; allow rule not wired

## Context

Owner decision E: prove in the run that plugin PreToolUse hooks fire for Workflow agents (marker-file stub exiting 2, default agent and harness:* agent, hook cwd); if not provable, record a needs_review decision and do not wire the allow rule. The spike could not run in the run environment; no marker-file evidence exists, and docs/workflows.md records this in one sentence.

## Options

- Wire the merge allow rule anyway
- Do not wire the allow rule; setup step 4 only names the guard and ticket PRs stay human-merged

## Decision

Do not wire the allow rule; /harness:setup only names the guard, and ticket PRs stay human-merged until the spike is proven.

## Why

Without proof the guard fires inside Workflow agents, an allow rule would remove the only prompt before a merge. This is the fallback the owner named.

## Consequences

Auto-merge of ticket PRs into the integration branch is not enabled by setup; the owner must run the spike (stub guard, default agent and harness:* agent, note hook cwd) in a live session to enable it.

## How to reverse

After a live spike passes, let setup offer merge-allow.sh with the guard text.
