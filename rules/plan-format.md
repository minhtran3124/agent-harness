# Plan Format Rule

Applies when writing `specs/<slug>/PLAN.md` for multi-step work.

Related: `auto-correct-scope.md`. See also `CLAUDE.local.md` → Development Workflow → Planning Layer.

## When to use this format

Use the task format when ANY of:

- Task spans >3 discrete implementation steps
- Task touches >2 files
- ETA >30 min
- Feature spans >1 layer (router + service, service + repo + migration, etc.)

Skip for single-file fixes, typo corrections, config tweaks.

> These thresholds are the **signal** that triggers a `PLAN.md` under the artifact policy (`rules/orchestration.md` → Artifact policy). A `SUMMARY.md` is still written for every lane regardless — plan-ahead scaffolding scales by signal; the record is always-on.

## Task Schema

Every task is a `### Task` markdown section carrying five semantics: `id`, optional `wave`,
and populated `Files / Action / Verify / Done`:

```markdown
### Task 1.1 — Short human title (wave 1)

- **Files:** path1, path2
- **Action:** Imperative instruction. Include rationale when non-obvious.
  Continuation lines are indented under the bullet.
- **Verify:** `single shell command — exit 0 means pass, finishes <60s`
- **Done:** Measurable acceptance state
```

Rules:

- Real tasks are plain markdown — never wrap them in code fences (fenced task sections are
  treated as illustrations and ignored, like the example above).
- A `### Task <id>` heading with **no** field bullets is prose, not a task (the renderer
  and gates ignore it).
- Keep the optional human title concise and outcome-focused.

Conventions:

- `id`: `<phase>.<task>` — e.g. `2.1`, `2.2`. Sub-tasks: `N.M.x` (e.g. `2.1.1`).
- `wave`: the `(wave K)` suffix on the task heading. Same-wave tasks MAY run in parallel; waves execute sequentially. Omit for single-wave plans.
- Files: comma-separated paths. Used by the wave-parallelism rule to check overlap and by `hooks/blast-radius-check.sh` as the in-scope set.

## Guardrails

1. **Zero file overlap** across same-wave tasks — prevents merge conflicts when executed in parallel.
2. **Verify must be automated** — your test runner, HTTP probe, linter, type-checker, migration command. Reject "open browser and check" at task level (that belongs in phase-level user-acceptance testing).
3. **Verify <60s** — if longer, split into sub-tasks.

## Examples

> Illustrative only — the paths/commands below are placeholders. Substitute your stack
> (see `techstacks/`): `src/<module>` → your source layout, `<test runner>` → yours, etc.

### Data model + migration (single wave)

```markdown
### Task 1.1 — Add the <Entity> model + migration (wave 1)

- **Files:** src/models/<entity>.<ext>, migrations/<id>_add_<entity>.<ext>
- **Action:** Add the <Entity> data model (PK, foreign keys, the required fields) and a
  migration that creates its table with the needed index.
- **Verify:** `<migration command> && <test runner> tests/models/test_<entity>`
- **Done:** Migration applies clean, model tests pass
```

### Service + entry point in separate waves

```markdown
### Task 2.1 — <Entity>Service (wave 1)

- **Files:** src/services/<entity>_service.<ext>, tests/services/test_<entity>_service.<ext>
- **Action:** Create the service methods (create/get). Mock the data-access layer in tests.
  Guard clause on invalid input.
- **Verify:** `<test runner> tests/services/test_<entity>_service`
- **Done:** Unit tests pass; coverage target met on the new file

### Task 3.1 — <Entity> endpoint + schema (wave 2)

- **Files:** src/routes/<entity>.<ext>, src/schemas/<entity>.<ext>, tests/routes/test_<entity>.<ext>
- **Action:** Add the create/list endpoints behind the auth dependency, with request/response
  schemas.
- **Verify:** `<test runner> tests/routes/test_<entity>`
- **Done:** Endpoint tests pass; unauthorized rejected, authorized returns a body
```

## PLAN.md structure

```markdown
---
slug: <kebab-case — may carry a ticket-source prefix (gh-<n>-…/lin-<ID>-…), see templates/structure/specs-README.md>
status: proposed | active | paused | shipped
owner: <name>
created: YYYY-MM-DD
---

# <Feature Name>

## 1. Motivation
## 2. Non-goals
## 3. Success Criteria
## 4. Tasks (one `### Task` section per task)
## 5. Risks
## 6. Status Log
```

The examples above show the full task shape; `specs/` is tracked in git, so plans are browsable across machines. (`PLAN.html` and `.plan-review.json` are gitignored as derived artifacts.)

## Legacy XML plans (read-only support)

Plans written before 2026-07-16 use fenced `<task id="N.M" wave="K"><files><action><verify><done>` XML blocks. The renderer, the executing-plans Step-0 gate, and `hooks/blast-radius-check.sh` still parse that syntax, so existing plans keep rendering and executing unchanged — but it is **not** an authoring format: never write new plans in XML. One exception: when adding a task to an existing XML plan, keep that plan's XML syntax — in a mixed file the parser reads only the XML tasks, so a markdown task added to an XML plan would be invisible.

## Auto-generated "At a glance" block

`render_plan.py --summarize` (invoked by the `render-plan-on-write.sh` hook on every `PLAN.md` save)
injects an additive, script-owned "At a glance" block — a count line, a wave×task table, a
`flowchart LR` Mermaid diagram, and a `### Progress` checklist — immediately before the first `## `
heading, between `<!-- AT-A-GLANCE:BEGIN -->` / `<!-- AT-A-GLANCE:END -->` sentinels.

It is derived entirely from the task sections (markdown, or legacy XML) and the `## Status Log`
(which stays the source of truth); the block regenerates idempotently on every save and must NOT be
hand-edited. Authors and agents still read and write only the task schema above — the At-a-glance
block is a rendering convenience, not a planning input.
