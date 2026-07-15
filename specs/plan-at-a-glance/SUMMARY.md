# plan-at-a-glance — Summary

Lane: high-risk
Confidence: medium
Reason: Modifies a core skill engine (`skills/visual-planner/render_plan.py`) and likely the `hooks/render-plan-on-write.sh` hook — both hard-gate high-blast-radius files — plus changes existing `/writing-plans` output behavior.
Flags: existing-behavior, weak-proof, multi-domain
Affects: skills/visual-planner/render_plan.py (core skill engine), hooks/render-plan-on-write.sh, rules/plan-format.md (PLAN.md machine contract), skills/writing-plans/SKILL.md
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- The user's request VERBATIM at intake — github.com/minhtran3124/agent-harness#54 -->

**Title:** Make generated plans easy for humans to read at a glance

## Problem

Plans are generated to be *executed by agents*, but they are hard for a **human** to read at a glance.

Today `/writing-plans` produces `specs/<slug>/PLAN.md` as a sequence of fenced `xml` task blocks (per `rules/plan-format.md`). The readable artifact — `PLAN.html`, built by `skills/visual-planner/render_plan.py` — is **gitignored** (`.gitignore:36`) and lives only on the machine that rendered it.

Consequences:

- **Reading a plan on GitHub or in an editor gives you raw XML.** No wave map, no file map, no progress. The reader has to mentally reconstruct execution order and scope from ~N `<task>` blocks.
- **The nice view isn't shareable.** To see `PLAN.html` you must clone the repo and run `python3 skills/visual-planner/view_plan.py <slug>` (local server + Chrome). A reviewer on a PR, a phone, or another machine can't.
- **No cross-plan overview by default.** There are ~29 dirs under `specs/`. `build_roadmap.py` can index them into `ROADMAP.html`, but that output is also local-only and must be built by hand.
- **Progress isn't visible in the plan.** Task status lives in the `## Status Log` prose, so "where are we?" requires reading the whole file.

## Goal

A human should understand a plan — scope, order, progress — **without running any tooling**, straight from the tracked `PLAN.md`.

## Proposed directions (for discussion, not a committed design)

**A. Make `PLAN.md` itself self-summarizing (highest value, lowest cost).**
Have `/writing-plans` emit an auto-generated "At a glance" block at the top of the tracked file:

- a **wave × task table** — wave, task id, human title, files touched, `<done>` state;
- a **Mermaid diagram** of wave order / task dependencies (GitHub renders Mermaid natively — zero tooling to view);
- counts: tasks, waves, files touched, est. steps.

Because `PLAN.md` is tracked, this ships the readable view everywhere for free — GitHub, IDE preview, `cat`.

**B. Make progress readable in-place.**
Checkbox-style task status (`- [x] 1.1 — …`) in the summary block, updated as waves complete, so `## Status Log` stays the audit trail and the header answers "where are we?".

**C. Make the rich view shareable, not just local.**
Options — pick one, don't do all: publish `PLAN.html` as a shareable Artifact URL; or attach the rendered plan to the PR; or keep it local and accept that (A) covers the sharing need.

**D. Lower the friction on the existing renderer.**
A single entry point for "show me all plans" (`build_roadmap.py` → `ROADMAP.html`) rather than a manual script invocation.

## Constraints / non-goals

- Must not break the machine contract: agents parse `<task id/wave/files/action/verify/done>`; the summary block is **additive** and derived, never the source of truth.
- Keep rendering **deterministic and script-owned** (`render_plan.py`), not LLM-transcribed — same rationale as `skills/README.md` § visual-planner.
- Regenerating the summary must be idempotent (the `render-plan-on-write.sh` PostToolUse hook already fires on every `PLAN.md` write — a summary generator can hook the same path).

## Suggested first step

Start with **(A) + (B)** only, behind `render_plan.py`'s existing parser (it already extracts waves, files, and task ids — the data is there, it just isn't written back into Markdown).

## What changed

<!-- pending — no implementation yet; intake only -->

Nothing yet. This SUMMARY records the intake classification only. Work is **blocked pending escalation** (see `specs/plan-at-a-glance/ESCALATIONS.md`).

### Rationale

High-risk lane is forced by a hard gate: the suggested first step edits `render_plan.py`, a core skill engine, and probably the `render-plan-on-write.sh` hook — both high-blast-radius files that cannot self-downgrade. Confidence is medium (not high) because the issue is explicitly framed "for discussion, not a committed design" with four directions (A/B/C/D); a reasonable default exists (A+B per the suggested first step) but the exact scope needs one human confirmation before the full high-risk chain runs.

### Alternatives considered

- Treat as `normal` lane — rejected: touching `render_plan.py` is a named hard gate, cannot be self-downgraded.
- Proceed autonomously on A+B without escalation — rejected: high-risk + medium confidence escalates per `rules/orchestration.md` (a human narrows scope / confirms which directions ship).

### Deviations

- none

### Verify

<!-- No implementation run yet. Verify rows will be filled during execution. -->

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| (pending — intake only) | — | — | No code changed yet |

### Rollback

<!-- Required before any high-risk work is considered done. To be filled at implementation time. -->

- Intake only — no change to roll back. `git revert <sha>` once implementation commits land.

### Harness-Delta

- none
