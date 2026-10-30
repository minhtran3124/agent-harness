---
ticket: 516
stage: design
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: design)
date: 2026-10-30
---

# 0108. Merge policy design: gated auto-merge of ticket PRs into feat/<slug>, fail-closed merge guard, human merge for everything else

## Context

Ticket #516 (depth L). Ticket PRs into the run's integration branch need an automatic merge path. Everything into base, main or the default branch must stay a human merge. The work is committed on feat/516-feat-workflow-merge-policy-auto-merge-ti; one stale test assertion (shellcheck count 8, now 9) is the only failure.

## Options

- Reuse the committed branch and fix the stale count (8 to 9, exact)
- Loosen the count assertion to a range
- Exclude merge-guard.sh from the shellcheck list
- Restart from v5.0.0

## Decision

Keep the committed design: merge-guard.sh PreToolUse(Bash) hook that fails closed, a per-ticket gate after stageFinish (CI green, no notFixed or score>=50 leftover, intent match, no needs_review decision), stageMerge only for tickets that pass and with no conflict path, a single-ticket run that never calls stageMerge, and a Merge: auto|human line with a readiness checklist on every PR. Fix the stale shellcheck count to exactly 9.

## Why

It follows owner-confirmed decisions A-H. The rest of the branch was verified up to this one stale count, and the count of 9 is proven by listing the files.

## Consequences

Ticket PRs merge automatically only when every gate passes and the guard sees a feat/* base. Any doubt goes to a human. The next new hook script needs the shellcheck count bumped.

## How to reverse

Revert commits 708fd4c6..1e87b218 and the count fix. Restore hooks.json, ship.js stageMerge and its conflict path, setup step 4 and the docs to v5.0.0.
