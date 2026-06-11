---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `specs/<slug>/PLAN.md`

Artifact + slug convention: specs/README.md + .claude/rules/plan-format.md

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

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**

- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

````

## Remember

- Exact file paths always
- Complete code in plan (not "add validation")
- Exact commands with expected output
- Reference relevant skills with @ syntax
- DRY, YAGNI, TDD

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

After saving the plan, rendering `PLAN.html`, and auto-viewing it, **ask the user** which execution
approach to use — present a clear A/B choice (use the `AskUserQuestion` tool when available):

**"Plan complete and saved to `specs/<slug>/PLAN.md` (visual: `specs/<slug>/PLAN.html`). Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**

- **REQUIRED SUB-SKILL:** Use subagent-driven-development
- Stay in this session
- Fresh subagent per task + code review

**If Parallel Session chosen:**

- Guide them to open new session in worktree
- **REQUIRED SUB-SKILL:** New session uses executing-plans
