---
ticket: 516
stage: design
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: design)
date: 2026-10-30
---

# 0110. No gh pr merge allow rule, because hook firing for Workflow agents is unproven

## Context

Spike (E) had to prove that plugin PreToolUse hooks fire for Workflow agents before an allow rule could be wired. This run did not prove it.

## Options

- Wire the allow rule anyway
- Do not wire it: setup step 4 only names the guard and ticket PRs stay human-merged

## Decision

Do not wire the allow rule. Setup step 4 names the guard and writes no settings.local.json. The merge-allow.sh offer is removed from the step.

## Why

Owner-confirmed fallback in (E). Without proof that the guard fires, an allow rule could let a workflow agent merge into base with no check at all.

## Consequences

In practice ticket PRs into feat/<slug> stay human-merged until a later run proves that hooks fire for workflow agents and wires the rule.

## How to reverse

After the spike passes, restore the merge-allow.sh offer in setup step 4, worded with the guard text.
