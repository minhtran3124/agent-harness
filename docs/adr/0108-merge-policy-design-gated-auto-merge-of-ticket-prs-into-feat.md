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

## Update (ticket #545): owner approval for one merge into base

The "human merge for everything else" part changes. A single plain `gh pr merge <n> --repo o/r --match-head-commit <head sha>` into base, from the main session, now gets `permissionDecision: "ask"`: Claude Code shows the owner a confirmation prompt that names the PR number, base and head commit, and the owner's Yes is the approval. The approval covers that one call. `--auto`, wrapped merges, `gh api`, GraphQL, `gh alias`, a subagent or workflow agent, an unknown or missing `permission_mode`, and every doubt path stay denied. The `feat/*` path is unchanged. The owner's `!` and terminal merge stay.

Probe result (headless `claude -p`, Claude Code 2.1.316, PreToolUse hook returning `ask` for a Bash call; test: `RUN_ASK_PROBE=1 bash tests/hooks/merge-guard.test.sh`): under `default`, `auto` and `bypassPermissions` the Bash call was not run in any of the three modes. `ask` is not turned into an allow, also under `bypassPermissions`; with no one to answer, Claude Code returns it as a denial. The interactive prompt itself cannot be driven headless, so that part rests on the hooks reference ("ask prompts the user"). Decision: no `UserPromptSubmit` token fallback is needed.
