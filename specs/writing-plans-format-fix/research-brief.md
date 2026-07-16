# Research Brief — writing-plans format conflict (C1)

Source finding: `docs/reviews/over-engineering-review-2026-07-16.md` §2 C1 (HIGH).
All claims below re-verified against the working tree on 2026-07-16.

## The conflict is three-way, not two-way

1. **`skills/writing-plans/SKILL.md` teaches a checkbox/step format.**
   - `:55-71` "Plan Document Header" — a superpowers-style prose header (`# [Feature Name] Implementation Plan`, Goal/Architecture/Tech Stack lines).
   - `:73-108` "Task Structure" — `### Task N: [Component]` with `- [ ] **Step 1: Write the failing test**` checkboxes and embedded Python snippets.
   - `:46-53` "Bite-Sized Task Granularity" — one action per 2–5-minute step.
2. **Every downstream consumer requires the XML `<task>` schema** (`rules/plan-format.md`):
   - `skills/executing-plans/SKILL.md:24-31` Step 0 hard gate — rejects any plan whose tasks lack populated `<files><action><verify><done>`; explicitly STOPs and refuses to execute.
   - `skills/visual-planner/render_plan.py:143-192` — depth-balanced scan for top-level `<task>` blocks only; a checkbox plan renders an **empty task list** in PLAN.html and gets an empty At-a-glance block.
   - `skills/subagent-driven-development/SKILL.md` — extracts tasks/waves from `<task>` blocks; wave parallelism reads the `wave` attribute and `<files>` overlap.
   - `hooks/blast-radius-check.sh` — compares edits against the active plan's `<files>` set.
   - `scripts/check_plan_format.py` — validates the XML schema (currently has no automated caller; see review §3).
3. **The skill contradicts itself internally.** Its own reviewer prompt, `skills/writing-plans/plan-document-reviewer-prompt.md:25,28`, requires "one fenced `xml` block (no raw `<task>` tags in body text)" and "valid `<task id ... wave ...>` schema with `<files>`, `<action>`, `<verify>`, `<done>`". So the plan-review loop the skill mandates would flag a plan written per the skill's own Task Structure section.

## A fourth defect: the header omits the machine-read frontmatter

`writing-plans:55-71` mandates a header with **no YAML frontmatter**, but the harness's status lifecycle is frontmatter-driven:
- `hooks/blast-radius-check.sh` keys on `status: active`;
- `skills/executing-plans/SKILL.md:60-62` sets `status: active` before the first task;
- `skills/finishing-a-development-branch` sets `status: shipped`;
- `rules/plan-format.md` "PLAN.md structure" defines the canonical frontmatter (`slug/status/owner/created`) and section list.

A plan starting with writing-plans' header instead of frontmatter silently disables blast-radius checking and the shipped transition.

## Stale claim (same file)

`writing-plans:16`: "This should be run in a dedicated worktree (created by brainstorming skill)" — brainstorming does not create worktrees; the skill's **own** Execution Handoff section (`:193-198`) correctly says the branch/worktree is created *after* the plan is saved, via `using-git-worktrees`. Two contradictory claims 180 lines apart in one file.

## Ground truth — has the bug ever shipped a broken plan?

- **19/19 `specs/*/PLAN.md` with tasks use the XML format; 0 use the checkbox format.** In practice the auto-loaded `rules/plan-format.md` wins over the skill prose.
- 2 plans (`resync-protected-files`, `rules-stack-agnostic`) embedded the writing-plans header text *below* proper frontmatter — harmless hybrids, evidence agents tried to satisfy both documents at once.
- So the failure mode is not "broken plans shipped"; it is (a) contradictory instructions burning reviewer-loop cycles and model attention every planning run, (b) a live trap for **deployed copies** — this skill ships to other repos via `scripts/deploy-harness.sh`, where a target repo may not carry the same auto-loaded rules context weighting, and (c) the empty-render / dead-gate path if the checkbox branch ever wins.

## Residual references elsewhere

- `skills/executing-plans/SKILL.md:67` — "Follow each step exactly (plan has bite-sized steps)": leftover of the checkbox model inside the XML-gated skill. Only other repo-wide echo of the old format (verified by grep for "Bite-Sized / Plan Document Header / Write the failing test").

## Origin

`git log --follow skills/writing-plans/SKILL.md`: the file arrived in the initial import (`bb0dd0e`, superpowers fork) and received three harness-native patches (specs/ transition `0998175`, branch isolation `747da53`, At-a-glance docs `9ad3be8`) — none reconciled the superpowers-era Header/Task-Structure/Granularity sections with the harness's own `rules/plan-format.md`. C1 is a fork-integration gap, consistent with the review's "duplication of truth" root cause (§4).

## What must NOT break (fix constraints)

- The process content of writing-plans that is correct and consumed: Input Artifacts (design.md + research-brief.md), Scope Check, File Structure guidance, Plan Review Loop (+ its reviewer prompt, already XML-correct), Visual Render Handoff/Auto-View (hook contracts), Execution Handoff A/B.
- `rules/plan-format.md` stays the single canonical home of the format (review §4 recommendation: one home per fact; everything else points).
- Durable advice inside the deleted sections (exact file paths, complete code rather than "add validation", exact commands with expected output, TDD ordering) must survive — relocated as guidance for writing `<action>`/`<verify>` bodies, not as a rival format.
