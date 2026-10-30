---
ticket: 516
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-30
---

# 0111. Auto-merge does nothing by default: no allow rule is wired and hook firing for workflow agents is unproven

## Context

The spike (E) could not prove that plugin PreToolUse hooks fire for Workflow agents. Setup step 4 only names the guard. In the committed ship.js, stageMerge's `gh pr merge` call is likely to be denied by permissions.

## Options

- Do not wire the allow rule; the ticket PRs stay human-merged until the owner allows them or the spike proves the hook fires
- Wire the allow rule anyway

## Decision

Do not wire the allow rule. By default every ticket PR ends as a human merge. The PR body must say that auto-merge is inactive out of the box.

## Why

Without proof that the guard fires for workflow agents, an allow rule would remove the only protection against a merge into base. A denied merge is a safe outcome.

## Consequences

The headline feature (auto-merge into feat/<slug>) has no effect until hook firing is proven. The gate and the human-merge decisions still work.

## How to reverse

After the spike passes, add the allow rule to /harness:setup step 4 and the docs.
