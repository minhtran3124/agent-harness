---
name: writing-plans
description: Use after an approved design and research brief to create a detailed, executable multi-step implementation plan before code changes.
---

# Writing Plans

Create `specs/<slug>/PLAN.md` for work that needs a plan. Announce this skill, then **Read `.claude/rules/plan-format.md`** before authoring: it is path-scoped and a new plan does not load it
automatically.

## Required inputs

Read `specs/<slug>/design.md` and `specs/<slug>/research-brief.md`. Stop and tell the user when a
required brief is missing. If the scope contains independent subsystems, propose separate plans.

## Authoring flow

1. Map created/changed files and their responsibilities. Follow existing patterns and give each
   unit a clear boundary; do not introduce unrelated refactors.
2. Write `## 3. Success Criteria` first. Each observable behavior needs a re-runnable, pipe-free,
   sub-60-second check and expected exit code, using the canonical schema from `plan-format.md`.
3. Decompose tasks in canonical `### Task` syntax. Give every task exact Files, imperative Action,
   automated Verify, and measurable Done fields. Make actions test-first where applicable.
4. Ensure same-wave tasks have no file overlap and no unresolved dependency. Use waves only for
   genuinely independent work.
5. Read `references/review-loop.md`, review the plan, and save it. The write hook renders the
   plain `PLAN.html`; use `visual-planner` only when the user asks for its graph-derived overlay.

## Handoff

State the saved plan path. Before any code change, use `using-git-worktrees` unless already
isolated, then invoke `subagent-driven-development`. Ask which execution mode only when the user
has not stated one; both modes use the same gates.
