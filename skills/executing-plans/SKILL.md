---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

# Executing Plans

## Overview

Load plan, review critically, execute tasks in batches, report for review between batches.

**Core principle:** Batch execution with checkpoints for architect review.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## The Process

### Step 0: Validate plan against .claude/rules/plan-format.md guardrails

**Gate — run BEFORE any implementation step. If ANY check fails, STOP, surface the specific violation(s) to the user, and do NOT execute.**

References: `.claude/rules/plan-format.md` (XML schema + guardrails) and `.claude/rules/wave-parallelism.md` (zero file overlap invariant).

Run these four guardrail checks against the plan:

1. **Required sub-elements populated.** Every `<task>` MUST have all 4 required sub-elements populated (non-empty): `<files>`, `<action>`, `<verify>`, `<done>`. Missing or empty → violation; name the offending task id.
2. **Zero file overlap across same-wave tasks.** Tasks sharing the same `wave` attribute MUST have ZERO overlap in `<files>` paths. Any shared path between same-wave tasks → violation; name the task ids and the overlapping path(s). See `.claude/rules/wave-parallelism.md` Invariant 1.
3. **`<verify>` is a single automated shell command.** Each `<verify>` MUST be exit-code-checkable (e.g. `pytest`, `curl`, `ruff check`, `mypy`, `alembic upgrade head`, `make migrate`). Reject "manually test in browser", "open and check", "visually inspect", or any step that cannot be validated by exit code. Per `.claude/rules/plan-format.md` Guardrail 2.
4. **Plan scope matches trigger threshold.** The full workflow is for tasks that span >3 discrete steps OR touch >2 files OR have ETA >30 min. If the plan is smaller than all three thresholds → STOP and suggest a direct edit instead of executing the full plan workflow. Per `.claude/rules/plan-format.md` "When to use this format".

**If any guardrail fails:** STOP. Report the specific violations (quote the failing task id(s) and sub-element(s)) back to the user. Reference `.claude/rules/plan-format.md` / `.claude/rules/wave-parallelism.md`. Do NOT proceed to Step 1.

**If all guardrails pass:** proceed to Step 0b.

### Step 0b: Ensure branch isolation (before any code change)

Implementation must never begin on `main`/`master` or another shared branch. Before the first task:

1. Check the current branch: `git symbolic-ref --short HEAD`.
2. If on a shared/protected branch — `main`, `master`, or any branch in
   `HARNESS_SHARED_BRANCHES` (the same list `hooks/branch-isolation-guard.sh` enforces) —
   **invoke `using-git-worktrees`** to create an isolated worktree + feature branch, then
   continue execution there. Do not proceed on the shared branch.
3. If already on a dedicated feature branch (or inside a worktree created for this slug), proceed.

This is the structural point that creates the branch. It is now backstopped at write time by
`hooks/branch-isolation-guard.sh`, which **hard-blocks** any code edit made on a shared branch
once a plan is `status: active` (break-glass: `BRANCH_ISOLATION_REASON`). `branch-guard.sh` only
warns, and only at commit time — so do not rely on it; create the branch here.

### Step 1: Load and Review Plan

1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with your human partner before starting
4. If no concerns: Create TodoWrite and proceed

### Step 2: Execute Tasks

**Before the first task:** set the frontmatter `status: active` (from `proposed`) in
`specs/<slug>/PLAN.md` — `hooks/blast-radius-check.sh` keys on it, and the edit auto-re-renders
`PLAN.html` via `render-plan-on-write.sh`. Canonical values only: `proposed | active | paused | shipped`.

For each task:

1. Mark as in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Mark as completed

### Step 3: Final review passes (same gates as subagent-driven-development)

After all tasks complete and verified, run the final review chain over the whole diff — this
path ships the same review gates as `subagent-driven-development`, not fewer:

1. **`/correctness-review`** — adversarial runtime-bug hunt over the full branch diff.
2. **`/intent-review`** — diff vs the original request (the `### Intent` in `specs/<slug>/SUMMARY.md`), blind to PLAN.

Fix or escalate any confirmed findings before proceeding. Do NOT skip these because execution
happened in a separate session — they are the difference between "passed the plan" and "correct".

### Step 4: Complete Development

After the review passes are clean:

- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use finishing-a-development-branch
- That skill runs the tests, marks the plan `shipped`, pushes, and opens a PR (it never merges).

## When to Stop and Ask for Help

**STOP executing immediately when:**

- Hit a blocker mid-batch (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**

- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember

- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Between batches: just report and wait
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**

- **using-git-worktrees** - REQUIRED: Set up isolated workspace before starting
- **writing-plans** - Creates the plan this skill executes
- **finishing-a-development-branch** - Complete development after all tasks
