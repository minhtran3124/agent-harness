# Design v2 — plan format: markdown first-class, XML optional (C1 + user direction)

Status: approved (user directive 2026-07-16: "XML is no longer mandatory — fix writing-plans + executing-plans + render-plan-to-HTML")
Companions: `research-brief.md` (C1 findings), `PLAN.md` (tasks). Design v1 (dedup-to-XML) superseded by this direction.

## Problem statement

Original C1: `writing-plans` teaches a superpowers checkbox format that every consumer rejects (see research-brief.md). New direction from the user: **XML must no longer be mandatory** — plans written in plain markdown must be accepted end-to-end. The consumers that currently hard-require XML: executing-plans Step-0 gate, `render_plan.py` (renders empty otherwise), `blast-radius-check.sh` (greps `<files>` only), the writing-plans reviewer prompt, and the canonical rule `rules/plan-format.md` itself.

## Decision

**One semantic schema, two accepted syntaxes.** The contract stays: every task has `id`, optional `wave`, and populated `files / action / verify / done`; guardrails unchanged (zero same-wave file overlap, `<verify>` = one automated command <60s). What becomes flexible is the surface syntax:

**Markdown syntax (new default — what writing-plans teaches):**

```markdown
### Task 1.1 — Short title (wave 1)

- **Files:** path/one.py, path/two.py
- **Action:** Imperative instruction. Multi-line continuations are
  indented under the bullet.
- **Verify:** `pytest tests/x -x`
- **Done:** Measurable acceptance state.
```

**XML syntax (still fully supported):** the existing fenced `<task id wave><files><action><verify><done>` blocks. All 19 existing plans keep working with **zero migration**.

Canonical home stays `rules/plan-format.md` — it defines both syntaxes; every other doc points there (preserves the C1 dedup fix; v1's deletion of the checkbox sections still happens).

## Why this shape

- **Markdown-heading syntax ≠ the old checkbox format.** The superpowers format had no files/verify/done semantics at all; this one is the same schema in friendlier clothes. C1's correctness fix survives intact.
- **Field-bullet parsing is deterministic** — `### Task <id>` headings + `- **Field:**` bullets are as machine-parseable as tags, without requiring authors (or deployed target repos) to hand-write XML.
- **XML retained, not deprecated:** 19 existing plans, the At-a-glance pipeline, and worked examples all use it; dual support costs one fallback parser (~50 lines), migration costs zero.

## Component changes

1. **`skills/visual-planner/render_plan.py`** — `extract_tasks()` gains a markdown fallback: if the balanced XML scan yields no tasks, scan the fence-masked body for `### Task <id> [— title] [(wave K)]` headings; span = heading → next `##`/`###` heading; parse `- **Files/Action/Verify/Done:**` bullets (with indented continuations) from the original slice into the **same dict shape** `{id, wave, files, action, verify, done}`. All three call sites (render, `--summarize`/At-a-glance, `--emit-files`) consume the unchanged return contract, so waves, Mermaid, progress checklist, and task cards work identically. XML wins in mixed files (documented; keeps parsing unambiguous). A heading without at least one field bullet is prose, not a task (prevents false positives on narrative headings).
2. **`skills/executing-plans/SKILL.md`** — Step 0 gate rewritten syntax-neutral: checks the four semantic fields populated per task *in either syntax*, same overlap/automation/threshold guardrails; no longer rejects on syntax. Line 67 "bite-sized steps" echo fixed (v1 carry-over).
3. **`skills/writing-plans/SKILL.md`** — v1 deletions still apply (checkbox Task Structure, Plan Document Header, Bite-Sized granularity, stale line 16); the replacement "Plan Format" section now teaches the **markdown syntax** with one compact example and notes XML as equally valid, pointing at `rules/plan-format.md` for the full contract.
4. **`skills/writing-plans/plan-document-reviewer-prompt.md`** — Task Syntax / Readability rows become syntax-neutral (valid task = either syntax with all four fields).
5. **`rules/plan-format.md`** — canonical update: "XML Schema" section becomes "Task Schema — two syntaxes"; the fencing rule is scoped to XML tasks only (markdown tasks are plain markdown, never fenced); wave conventions cover both (`wave="K"` attr / `(wave K)` heading suffix); At-a-glance wording "derived from the task blocks (either syntax)".
6. **`hooks/blast-radius-check.sh`** — declared-files extraction also reads `- **Files:**` bullet lines (case-insensitive) in addition to `<files>` tags. Advisory hook (warns only), so a fenced-example false positive is acceptable and documented in the test.
7. **`skills/visual-planner/SKILL.md`** — the parsing-contract note (~line 190) documents the markdown fallback.
8. **Tests** — `tests/hooks/render-plan-on-write.test.sh`: a markdown-syntax PLAN.md renders with the task present; `tests/hooks/blast-radius-check.test.sh`: markdown `- **Files:**` declarations suppress/raise the warning identically to `<files>`.

## Out of scope

- `scripts/check_plan_format.py` — XML-only validator with **no callers** (review §3, issue #67 wire-or-delete pending). Not extended here; if later wired, it must learn the markdown syntax first.
- s-d-d / wave-parallelism prose mentions of `<task>` — semantics unchanged; wording cleanup rides Phase 3 of issue #67, except the single `implementer-prompt.md` `<verify>` mention which stays valid for XML plans and reads fine generically.
- Migration of existing plans: none needed by design.

## Risks

- **High-blast surfaces touched** (`render_plan.py`, `hooks/*`) — Rule-4 hard gate; explicitly authorized by the user's directive. Mitigation: parser is a pure fallback (XML path byte-identical), full test suite before/after, rollback = `git revert` (no data/schema migration).
- Ambiguous markdown plans (heading without fields, fields without heading) → parsed as prose, plan renders without task cards; executing-plans Step 0 then reports unpopulated tasks — fail-explicit, matching current XML behavior for malformed blocks.
- Divergence between render_plan.py's parser and the gate's prose definition — both derive from plan-format.md's syntax spec; the render test pins the parser to the spec's example verbatim.
