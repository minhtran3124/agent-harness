---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** Plan-writing may run anywhere (`specs/` stays writable on shared branches); the feature branch/worktree is created at Execution Handoff via `using-git-worktrees`, before the first code edit.

**Save plans to:** `specs/<slug>/PLAN.md`

Artifact + slug convention: specs/README.md + .claude/rules/plan-format.md

**Step 0 — load the format rule:** Read `.claude/rules/plan-format.md` now. It is path-scoped
(not auto-loaded), and writing a brand-new PLAN.md does not trigger its `paths:` injection —
this explicit Read is the load-bearing step.

## Input Artifacts

Before writing anything, read both files from the spec directory:

1. `specs/<slug>/design.md` — the approved spec from brainstorming
2. `specs/<slug>/research-brief.md` — xia2's findings on what already exists

The research brief determines what to reuse vs. build from scratch. If `research-brief.md` is missing, flag it to the user before proceeding — writing a plan without it risks reinventing existing code.

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

Then, **before decomposing tasks**, author the `## 3. Success Criteria` table — the acceptance
contract (schema in `.claude/rules/plan-format.md` → Success Criteria schema). Writing the
observable behaviors and their re-runnable checks first gives the tasks something to trace to:
every task should serve one or more SCs. A new markdown plan that ships without this table fails
plan review.

## Plan Format (canonical: `.claude/rules/plan-format.md`)

The plan format has exactly one home: `.claude/rules/plan-format.md`. Do not restate the
schema here or in the plan. Non-negotiables it defines:

- YAML frontmatter (`slug/status/owner/created`) — hooks key on `status:`
- the document section list (Motivation … Status Log)
- one `### Task` markdown section per task (the only authoring syntax — never XML,
  never fenced):

  ```markdown
  ### Task 1.1 — Short human title (wave 1)

  - **Files:** exact/path/one.py, tests/exact/path/test_one.py
  - **Action:** Imperative instruction. Complete code, not "add validation".
    Order the work test-first: failing test → run it → implement → re-run.
  - **Verify:** `pytest tests/exact/path/test_one.py -x`
  - **Done:** Measurable acceptance state.
  ```

- guardrails: zero same-wave file overlap; Verify = one automated command, <60s
- the `## 3. Success Criteria` acceptance-contract table (`SC-<n>` ids, pipe-free <60s checks,
  `exit <n>` Expected) — schema in `.claude/rules/plan-format.md` → Success Criteria schema

When writing Action and Verify bodies:

- Exact file paths always; complete code in the plan (not "add validation").
- Exact commands with expected output; the command goes in Verify, the expected
  outcome in Done.
- Reference relevant skills with @ syntax.
- DRY, YAGNI, TDD.

## Plan Review Loop

After completing each chunk of the plan:

1. Dispatch plan-document-reviewer subagent (see plan-document-reviewer-prompt.md) with precisely crafted review context — never your session history. This keeps the reviewer focused on the plan, not your thought process.
   - Provide: chunk content, path to spec document
2. If ❌ Issues Found:
   - Fix the issues in the chunk
   - Re-dispatch reviewer for that chunk
   - Repeat until ✅ Approved
3. If ✅ Approved: proceed to next chunk (or execution handoff if last chunk)

**Chunk boundaries:** Use `## Chunk N: <name>` headings to delimit chunks. Each chunk should be ≤1000 lines and logically self-contained.

**Review loop guidance:**
- Same agent that wrote the plan fixes it (preserves context)
- If loop exceeds 5 iterations, surface to human for guidance
- Reviewers are advisory - explain disagreements if you believe feedback is incorrect

## Visual Render Handoff

`specs/<slug>/PLAN.html` is auto-generated by the deterministic `render-plan-on-write.sh` hook
**every time a `PLAN.md` is written** (PostToolUse Write|Edit → `visual-planner/render_plan.py`).
The plain render therefore needs **no sub-agent and no manual step** — it already happened. Never
transcribe HTML yourself.

**Announce:** "Plan approved — PLAN.html auto-rendered by the render-plan hook."

The same hook also injects an additive, sentinel-delimited "At a glance" block (count line, wave×task
table, Mermaid flowchart, progress checklist) directly into the tracked `PLAN.md` — deterministic and
script-owned, derived from the task sections and `## Status Log` — so a human can read scope, order,
and progress on GitHub with no tooling. See `rules/plan-format.md` → Auto-generated "At a glance" block.

Dispatch ONE `general-purpose` sub-agent **only when the user explicitly asks for risk /
blast-radius overlay** (the hook does plain render only). That sub-agent runs the 3-step `--review`
dance documented in `visual-planner/SKILL.md` (`--emit-files` → gather `code-review-graph` data →
write `specs/<slug>/.plan-review.json` → render with `--review`), and returns (≤100 words) the
written `PLAN.html` path + the script's self-check status. On a non-zero exit, surface the
`SELF-CHECK FAILED:` lines verbatim — do **not** claim success.

`PLAN.html` is untracked (it lives beside `PLAN.md` in `specs/`, but is gitignored as a derived artifact — `specs/` itself is tracked). Plain
render needs no MCP and finishes in seconds; reserve `--review` for when graph-derived risk is wanted.

## Auto-View

After the plan is saved and the hook has rendered `PLAN.html`, **open it for the user** — then go straight to the
Execution Handoff question below. This runs in the main thread (it's a user-facing action), and only
when a display is attached; headless contexts (CI, remote boxes) skip it silently.

```bash
# "Has a display?" — Darwin always; Linux needs X11 ($DISPLAY) or Wayland ($WAYLAND_DISPLAY).
if [ "$(uname)" = "Darwin" ] || [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
  python3 .claude/skills/visual-planner/view_plan.py <slug> --file
else
  echo "Headless — skipping auto-view; open specs/<slug>/PLAN.html manually."
fi
```

`--file` opens `PLAN.html` instantly and returns (no blocking, no lingering server), so the handoff
flows right into the question. A user who wants the localhost/clipboard experience runs
`view_plan.py <slug>` (server mode) themselves.

## Execution Handoff

After saving the plan, rendering `PLAN.html`, and auto-viewing it, hand off to execution:

**"Plan complete and saved to `specs/<slug>/PLAN.md` (visual: `specs/<slug>/PLAN.html`)."**

- **REQUIRED SUB-SKILL:** `using-git-worktrees` (if not already isolated), then
  `subagent-driven-development`.
- Before the first code change, apply `.claude/rules/auto-correct-scope.md` → Branch isolation.
  Do not hand off until work is on the lane-appropriate dedicated branch.

`subagent-driven-development` covers both execution modes: fresh subagent per task in this
session (the default), or the same skill run from a parallel session in the worktree, which
executes in batches with a checkpoint between them. Ask the user which they want only if they
have not already said — the gates are identical either way.
