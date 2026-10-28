---
ticket: run
stage: intent-fix
status: superseded
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-28
---

# 0004. Report failing descriptions instead of editing them

> Superseded: the plan-blind intent-fix stage made this change against the owner-confirmed decisions; it was reverted because the owner chose to nới cue to use|when and to edit five descriptions (see 0003, 0009, 0010).

## Context

The owner said all current skills and agents must pass without editing any description, and that a failure should be reported. The earlier diff edited five descriptions.

## Options

- Restore the five descriptions and let the check report failures
- Keep the edits and loosen the check

## Decision

Restored the five descriptions to their original text (commit 5471649). The check now reports 14 descriptions with no 'when' cue: skills autopilot, compound, diagnosing-bugs, finishing-a-development-branch, intake, intent-review, setup, using-git-worktrees; agents advisor, implementer, intent-reviewer, researcher, task-reviewer, test-runner.

## Why

The owner's instruction was explicit, and the check was meant to surface failures, not hide them.

## Consequences

check_frontmatter_contract.py exits 1 on the live tree. test_live_repo_passes fails, and so will the CI step in .github/workflows/harness-ci.yml and scripts/run-tests.sh. This is the requested report. The owner has to decide whether to fix the descriptions or relax the cue rule.

## How to reverse

git revert 016891d 5471649, or add 'Use when' clauses to the 14 descriptions.
