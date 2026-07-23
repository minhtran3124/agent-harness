---
paths:
  - "specs/**/PLAN.md"
---

# Plan Format Rule

Applies when writing `specs/<slug>/PLAN.md` for multi-step work.
Path-scoped (not auto-loaded): injected when a `specs/**/PLAN.md` file is read; authoring
flows load it via the explicit Read step in `writing-plans` / `subagent-driven-development`.

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

## Success Criteria schema (the acceptance contract)

The `## 3. Success Criteria` section is the plan's **acceptance contract**: the observable
behaviors the finished work must exhibit, each paired with a re-runnable check. For every new
markdown plan it MUST be a markdown table with exactly these columns:

| ID | Behavior (observable) | Check (re-runnable) | Expected |

Column rules:

- **ID** — `SC-<n>`, sequential and unique within the plan (`SC-1`, `SC-2`, …). No gaps, no reuse.
- **Behavior (observable)** — the externally-visible outcome, phrased so a reader can tell it
  happened without reading the diff. Not an implementation note.
- **Check (re-runnable)** — a command that inherits the same guardrails as a task `Verify` (see
  `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`): a **single** command,
  **pipe-free** (no `|`), finishes in **<60s**, and never a whole-suite row. Split anything larger
  into more SC rows.
- **Expected** — grammar is a leading machine-read token `exit <n>` (a non-zero code is allowed
  when the check asserts failure), optionally followed by free text describing the expectation.
  Examples: `exit 0`, `exit 1 — rejects the unsigned request`.

Same fencing rule as tasks: a Success Criteria table written **inside a code fence** is an
illustration and is ignored; the live contract is the non-fenced table. Example (fenced, so
illustrative only):

```markdown
## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
|------|-------------------------|-----------------------|------------|
| SC-1 | New markdown plan without an SC table is rejected | `python scripts/verify_summary.py --lint specs/<slug>` | exit 1 — missing SC table |
| SC-2 | A well-formed SC table passes the lint | `python scripts/verify_summary.py --lint specs/<slug>` | exit 0 |
```

Exemptions: legacy XML plans (see "Legacy XML plans" below) and pre-existing specs authored
before this rule are exempt — the SC table is required only for **new** markdown plans.

### SUMMARY side — the `Criterion` column

When a plan declares an SC table, its sibling `SUMMARY.md` closes the loop from the other end: the
`### Verify` table accepts an optional trailing **`Criterion`** column naming the `SC-<n>` id that
each row satisfies (`Check | Command | Exit | Notes | Criterion`). `scripts/verify_summary.py`
enforces this coupling — when the sibling `PLAN.md` declares an SC table, the referenced ids must
resolve to real `SC-<n>` rows in that plan. The column is optional when no SC table exists.

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
## 3. Success Criteria  (the acceptance-contract table — see "Success Criteria schema" above)
## 4. Tasks (one `### Task` section per task)
## 5. Risks
## 6. Status Log
```

The examples above show the full task shape; `specs/` is tracked in git, so plans are browsable across machines. (`PLAN.html` and `.plan-review.json` are gitignored as derived artifacts.)

## Legacy XML plans (read-only support)

Plans written before 2026-07-16 use fenced `<task id="N.M" wave="K"><files><action><verify><done>` XML blocks. The renderer, the `subagent-driven-development` Step-0 gate, and `hooks/blast-radius-check.sh` still parse that syntax, so existing plans keep rendering and executing unchanged — but it is **not** an authoring format: never write new plans in XML. One exception: when adding a task to an existing XML plan, keep that plan's XML syntax — in a mixed file the parser reads only the XML tasks, so a markdown task added to an XML plan would be invisible.

## Auto-generated "At a glance" block

`render_plan.py --summarize` (invoked by the `render-plan-on-write.sh` hook on every `PLAN.md` save)
injects an additive, script-owned "At a glance" block — a count line, a wave×task table, a
`flowchart LR` Mermaid diagram, and a `### Progress` checklist — immediately before the first `## `
heading, between `<!-- AT-A-GLANCE:BEGIN -->` / `<!-- AT-A-GLANCE:END -->` sentinels.

It is derived entirely from the task sections (markdown, or legacy XML) and the `## Status Log`
(which stays the source of truth); the block regenerates idempotently on every save and must NOT be
hand-edited. Authors and agents still read and write only the task schema above — the At-a-glance
block is a rendering convenience, not a planning input.
