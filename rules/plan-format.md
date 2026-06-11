# Plan Format Rule

Applies when writing `specs/<slug>/PLAN.md` for multi-step work.

Related: `auto-correct-scope.md`. See also `CLAUDE.local.md` → Development Workflow → Planning Layer.

## When to use this format

Use XML task format when ANY of:

- Task spans >3 discrete implementation steps
- Task touches >2 files
- ETA >30 min
- Feature spans >1 layer (router + service, service + repo + migration, etc.)

Skip for single-file fixes, typo corrections, config tweaks.

> These thresholds are the **signal** that triggers a `PLAN.md` under the artifact policy
> (`rules/orchestration.md` → Artifact policy). A `SUMMARY.md` is still written for every lane
> regardless — plan-ahead scaffolding scales by signal; the record is always-on.

## XML Schema

Every task in `PLAN.md` MUST use:

```xml
<task id="N.M" wave="K">
  <files>path1, path2</files>
  <action>Imperative instruction. Include rationale when non-obvious.</action>
  <verify>single shell command — exit 0 means pass, finishes <60s</verify>
  <done>Measurable acceptance state</done>
</task>
```

## Rendering requirement (Markdown-safe)

Raw XML-like tags (for example `<task>`, `<files>`, `<action>`) are treated as HTML by many Markdown renderers and become hard to read in preview mode.

To keep plans readable, every task MUST be wrapped in a fenced `xml` code block in the plan document.

Use this presentation pattern:

````markdown
### Task 1.1 — Short human title

```xml
<task id="1.1" wave="1">
  <files>path1, path2</files>
  <action>...</action>
  <verify>...</verify>
  <done>...</done>
</task>
```
````

Rules:

- Do not place raw `<task ...>` blocks directly in Markdown body text.
- Keep one task per fenced `xml` block.
- Keep the optional human title concise and outcome-focused.

Conventions:

- `id`: `<phase>.<task>` — e.g. `2.1`, `2.2`. Sub-tasks: `N.M.x` (e.g. `2.1.1`).
- `wave`: same-wave tasks MAY run in parallel; waves execute sequentially. Omit for single-wave plans.
- `<files>`: comma-separated paths. Used by wave-parallelism rule to check overlap.

## Guardrails

1. **Zero file overlap** across same-wave tasks — prevents merge conflicts when executed in parallel.
2. **Verify must be automated** — `pytest`, `curl`, `ruff check`, `mypy`, `alembic upgrade head`, `make migrate`. Reject "open browser and check" at task level (that belongs in phase-level user-acceptance testing).
3. **Verify <60s** — if longer, split into sub-tasks.

## FastAPI examples

### Migration + model (single wave)

```xml
<task id="1.1" wave="1">
  <files>app/models/trade_log.py, alembic/versions/xxx_add_trade_log.py</files>
  <action>Add TradeLog SQLAlchemy model: UUID PK, user_id FK, trade_type enum, executed_at timestamp. Alembic migration with index on (user_id, executed_at).</action>
  <verify>cd apps/api && alembic upgrade head && pytest tests/models/test_trade_log.py -x</verify>
  <done>Migration applies clean, model tests pass</done>
</task>
```

### Service + router in separate waves

```xml
<task id="2.1" wave="1">
  <files>app/services/trade_log_service.py, tests/services/test_trade_log_service.py</files>
  <action>Create TradeLogService.create_entry() and get_recent(). AsyncMock session in tests. Guard clause on invalid trade_type.</action>
  <verify>cd apps/api && pytest tests/services/test_trade_log_service.py -x</verify>
  <done>Unit tests pass; coverage ≥80% on new file</done>
</task>

<task id="3.1" wave="2">
  <files>app/routers/trade_logs.py, app/schemas/trade_log.py, tests/routers/test_trade_logs.py</files>
  <action>POST /trade-logs + GET /trade-logs/recent. Depends(get_current_user). Pydantic schemas for request/response.</action>
  <verify>cd apps/api && pytest tests/routers/test_trade_logs.py -x</verify>
  <done>Router tests pass; 401 on unauth, 200 + body on auth</done>
</task>
```

## PLAN.md structure

```markdown
---
slug: <kebab-case>
status: proposed | active | paused | shipped
owner: <name>
created: YYYY-MM-DD
---

# <Feature Name>

## 1. Motivation
## 2. Non-goals
## 3. Success Criteria
## 4. Tasks (one fenced `xml` block per task; optional human-readable task titles)
## 5. Risks
## 6. Status Log
```

The FastAPI examples above show the full task shape; `specs/` is tracked in git, so plans are browsable across machines. (`PLAN.html` and `.plan-review.json` are gitignored as derived artifacts.)
