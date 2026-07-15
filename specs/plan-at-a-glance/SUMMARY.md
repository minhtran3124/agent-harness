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

Escalation E001 resolved (human chose **A+B**; see `ESCALATIONS.md`). Implemented on branch
`feat/plan-at-a-glance`. `skills/visual-planner/render_plan.py` gained an opt-in `--summarize` flag that
injects a deterministic, additive "At a glance" block into the tracked `specs/<slug>/PLAN.md` — a count
line, a wave×task Markdown table, a `flowchart LR` Mermaid diagram (one subgraph per wave, `Wn→Wn+1`
edges), and a `### Progress` checklist whose done-state derives from the `## Status Log`. The block is
delimited by line-anchored `AT-A-GLANCE:BEGIN/END` sentinels, inserted before the first `## ` heading
(preserving the H1 + any `> For Claude` directive), regenerated idempotently (write-only-if-changed), and
stripped from the HTML render to avoid duplication. The existing `render-plan-on-write.sh` PostToolUse
hook now passes `--summarize`, so the block refreshes on every PLAN.md save. `rules/plan-format.md` and
`skills/writing-plans/SKILL.md` document the block as additive/derived — the `<task>` blocks stay the
source of truth. Directions C (Artifact publishing) and D (roadmap entry point) were deferred.

**Review-driven fixes (each its own commit):** count intersection so a stale done-id can't inflate the
count (`2144659`); DRY consolidation of `_wave_sort_key` into the existing `wave_sort_key` + orphan-
sentinel guard (`ce276cf`); a CRITICAL correctness fix — line-anchoring sentinel detection so a PLAN.md
that merely *mentions* the sentinel strings in prose/code is never corrupted (`471f705`); and trailing-
whitespace tolerance on sentinel lines (`5d6e725`).

**Known limitations (report-only):** (1) this feature's own `PLAN.md` parses to 0 tasks (its task
actions embed literal `<task>` fixture strings), so `--summarize` on it emits a degenerate "No tasks
defined yet" block — left un-self-injected; normal plans summarize correctly. (2) `--summarize` normalizes
CRLF→LF on write (LF-only repo — acceptable). (3) "est. steps" from the issue's count list is
intentionally omitted (design §4.1 — no distinct step datum exists).

### Rationale

High-risk lane is forced by a hard gate: the suggested first step edits `render_plan.py`, a core skill engine, and probably the `render-plan-on-write.sh` hook — both high-blast-radius files that cannot self-downgrade. Confidence is medium (not high) because the issue is explicitly framed "for discussion, not a committed design" with four directions (A/B/C/D); a reasonable default exists (A+B per the suggested first step) but the exact scope needs one human confirmation before the full high-risk chain runs.

### Alternatives considered

- Treat as `normal` lane — rejected: touching `render_plan.py` is a named hard gate, cannot be self-downgraded.
- Proceed autonomously on A+B without escalation — rejected: high-risk + medium confidence escalates per `rules/orchestration.md` (a human narrows scope / confirms which directions ship).

### Deviations

- none — implementers reported no Rule 1–3 auto-fixes; all changes were either planned tasks or
  review-driven fixes carrying their own commits (listed under "What changed").

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Unit (render + summary + inject + strip) | `"$TMPDIR/harness-tests-venv/bin/python" -m pytest skills/visual-planner/test_render_plan.py -q` | 0 | 79 passed (57 baseline + 22 new) |
| Hook contract | `bash tests/hooks/render-plan-on-write.test.sh` | 0 | 5 passed (block injected on save + idempotent) |
| CLI end-to-end | `python3.13 skills/visual-planner/render_plan.py <tmp>/PLAN.md --summarize` | 0 | block injected, PLAN.html strips it, 2nd run byte-identical |
| Corruption fix (real plan copy) | `--summarize` on a copy of this `PLAN.md` | 0 | +162 bytes, 0 content deleted, sentinel-mention source preserved, correct anchor |
| Correctness review | adversarial whole-diff pass | — | CRITICAL corruption found → fixed (`471f705`); LOW whitespace → closed (`5d6e725`); re-review CONFIRMED-FIXED |
| Intent review | blind-to-plan vs issue #54 | — | ✅ no divergence; A+B fully delivered, no excess |

### Rollback

- Pure-additive feature. `git revert 60df278..5d6e725` (or revert the range) restores prior behavior;
  the `--summarize` flag + hook arg removal reverts to HTML-only rendering. Generated blocks already in
  any PLAN.md are inert Markdown and can be deleted by removing the `AT-A-GLANCE:BEGIN…END` region.

### Harness-Delta

- none — the feature dogfoods the existing render-plan hook path; no workflow friction surfaced.
