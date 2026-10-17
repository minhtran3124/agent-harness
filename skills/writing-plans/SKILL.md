---
name: writing-plans
description: Use after an approved design and research brief to create a detailed, executable multi-step implementation plan before code changes.
allowed-tools: Read, Write, Grep, Glob, Agent, Task, Bash(python3 scripts/check_plan_contract.py *), Bash(python3 skills/visual-planner/render_plan.py *)
---

# Writing Plans

Create `specs/<slug>/PLAN.md` for work that needs a plan. Announce this skill. Then, before
authoring, **Read `rules/plan-format.md`** and **Read `rules/terminology.md`**. Both rules are
path-scoped, and a new plan does not load them automatically. From `terminology.md`, §3 is the
load-bearing section. Every `Verify:`, `Done:`, and Success Criterion must be decidable by running
something. It must never depend on a judgment that output "is correct" or "looks right".

## Required inputs

Read `specs/<slug>/design.md` and `specs/<slug>/research-brief.md`. Stop and tell the user when a
required brief is missing. If the scope contains independent subsystems, propose separate plans.

## Authoring flow

1. Map created/changed files and their responsibilities. Follow existing patterns and give each
   unit a clear boundary. Do not introduce unrelated refactors.
2. Write `## 3. Success Criteria` first. Each observable behavior needs a re-runnable, pipe-free,
   sub-60-second check and expected exit code, using the canonical schema from `plan-format.md`.
3. For every new plan, add exact `## Global Constraints`. Decompose tasks in canonical `### Task`
   syntax. Give every task Files, imperative Action, automated Verify, measurable Done, mapped
   `Criteria` (`SC-n`), and an `Interfaces` line naming what it consumes/produces. Make actions
   test-first where applicable. Write the `- Plan-contract: 2` marker as a bullet in
   `## Global Constraints`. Give every task a `Seams:` line directly after `Interfaces`, in the
   form that `plan-format.md` defines. When `specs/<slug>/diagnosis.md` exists, copy its `Seam:`
   exactly into the fix task's `Seams:` and keep the `- Plan-contract: 2` marker.
4. Ensure same-wave tasks have no file overlap and no unresolved dependency. Use waves only for
   genuinely independent work.
5. When `design.md` has a `## What must be true` section, first write `### Assumption coverage` in
   `## 5. Risks`, after the risk bullets with a blank line. In that case, start Risks with `- none`
   when there are no risks. Reason: the plan renderer cards only the first bullet list. Give each design
   `A<n>` one line: `- A<n> → SC-n`, `- A<n> → Task x.y`, `- A<n> → accepted risk: <reason>`, or
   `- A<n> → retired by DC<n>` when the design retired it. Write
   `- none (design has no assumptions)` when that section is `- none — <reason>`. Check that every
   named `SC-n` and task exists in the plan. Then run `python3 scripts/check_plan_contract.py specs/<slug>/PLAN.md`. Read `references/review-loop.md`, review the plan, and save it. Then run
   `python3 skills/visual-planner/render_plan.py specs/<slug>/PLAN.md --summarize`. This command
   refreshes the At-a-glance block and writes the plain `PLAN.html`. Use `visual-planner` only
   when the user asks for its review-derived overlay.

## Handoff

State the saved plan path. Before any code change, use `using-git-worktrees` unless the work is
already isolated. Then invoke `subagent-driven-development` in this session. Do not ask the user
to choose an execution mode or to confirm the start. Only an escalation trigger in
`rules/orchestration.md` stops the start. A later session continues the run with `resume <slug>`.
