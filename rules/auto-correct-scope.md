# Auto-Correction Scope

Classifies what Claude may self-fix during implementation vs what requires user confirmation. Reduces HITL while keeping trust.

Applies when executing a `specs/<slug>/PLAN.md` task. For ad-hoc single fixes, user judgment rules.

Related: `plan-format.md`, `guidelines.md`, `orchestration.md`, `skills/feature-intake/SKILL.md`.

## Lane-aware autonomy

The intake lane (`specs/<slug>/SUMMARY.md`, set by `/feature-intake`) decides how much autonomy applies. Rules 1–4 below are constant; the lane decides whether a plan and a human confirmation are required first:

| Lane | Autonomy | Plan | Human confirm |
|---|---|---|---|
| **tiny** | Full auto — direct patch | none | none (machine gates are the safety net: `ruff-on-edit`, `auto-test-on-change`, `commit-quality-gate`, `risk-corroboration`) |
| **normal** | Auto with proof gates (subagent two-stage review) | yes | only if confidence low / ambiguous |
| **high-risk** | Auto-plan, gated-execute | yes (full chain) | only on ambiguity or a hard gate (Rule 4) |

> **Evidence the lane requires (single source of truth):** `scripts/check_lane_evidence.py` mechanizes the lane → evidence mapping so this table, `skills/feature-intake/SKILL.md` (Step 7), and the `SUMMARY.md` checks do not drift. It reads `specs/<slug>/SUMMARY.md` and asserts: **tiny** → filled `Lane`/`Confidence`/`Reason`; **normal** → + a non-placeholder `### Verify` row; **high-risk** → + a non-empty `### Rollback`. Run `python scripts/check_lane_evidence.py <slug>` (exit 1 = missing evidence). Edit the mapping there, not only in prose.

Rule 4 (STOP) still fires inside **every** lane — a hard gate discovered mid-task escalates regardless of how the work was classified. Ceremony scales with risk; the human gate scales with ambiguity, not risk.

**Record always-on; verify substitutes for the human gate.** Every lane writes `SUMMARY.md` (the audit record, incl. `Rationale` / `Alternatives`). For autonomous work, a re-runnable `### Verify` row + independent review — not extra planning docs — are what earn the skipped human confirmation. Plan-ahead docs (`design` / `research-brief` / `PLAN`) scale by signal (`rules/orchestration.md` → Artifact policy); `FULL_ARTIFACTS=1` forces the full set when maximum traceability is wanted.

## Rule 1 — Auto-fix (no ask)

Obvious bugs discovered during implementation:

- Wrong ORM/data-access query (missing join, incorrect filter, soft-delete not respected)
- Off-by-one, null-check miss, wrong comparison operator
- Logic contradicting the `<action>` spec
- Test failures caused by the implementation mistake (not test design)
- Missing `await` on async call; sync call in async context
- Typos in identifiers

## Rule 2 — Auto-add (no ask)

Missing functionality clearly required by project standards but not explicitly listed in `<action>`:

- Input validation at API boundary (your validation layer / schema, guard clauses)
- Error handling for documented failure modes (DB errors, broker HTTP 4xx/5xx)
- Missing imports, type hints, schema fields
- Your error factory (e.g. `BadRequest / NotFound / ServerError`) where a bare framework exception was used
- Token logging for AI paths (including failure cases)
- `logger.error(f"[COMPONENT] ...: {e}")` where exceptions swallowed silently

## Rule 3 — Auto-fix blocking

Issues preventing the task from completing:

- Missing dependency (add to your dependency manifest, note rationale in SUMMARY)
- Syntax error in Claude's own output
- Wrong import path
- Migration revision ID collision (regenerate)
- Linting / type-check failures (your linter / type-checker) on newly-written code

## Rule 4 — STOP + ask user

> **Canonical gate list:** the hard-gate vocabulary lives in `harness-manifest.json` — the diff-detectable gates under `hard_gates.detectable` (enforced by `risk-corroboration.sh`) and the judgment-only STOP items below under `hard_gates.judgment` (removing functionality, session/scope, replacing a service). Keep this list in sync with the manifest; `scripts/check_manifest.py` guards the detectable half.

Changes requiring architectural judgment — NEVER auto-apply:

- Schema changes (add/remove/rename DB table or column) not in the `<action>` spec
- API contract changes (route path, method, request/response shape) not in spec
- Removing existing functionality, even if seemingly unused
- Introducing a new external service dependency (new broker, AI provider, webhook target)
- Security-sensitive auth/authz changes (permission checks, JWT handling, CORS)
- Session/transaction scope changes (request-scoped ↔ isolated/background session)
- Changes to high-blast-radius files: `settings.json` (hook registration), any `hooks/*` script (auto-runs every session), or a core skill engine (e.g. `skills/visual-planner/render_plan.py`)
- Replacing a service/pattern (e.g. swapping cache impl, or replacing the shared data-access base)

## Reporting

Every Rule 1–3 auto-fix MUST appear in `specs/<slug>/SUMMARY.md` under `### Deviations`:

> example — substitute your stack

```markdown
### Deviations

- Rule 2 — Added `AppException.BadRequest` for invalid trade_type. `app/services/trade_log_service.py`. Commit `abc1234`.
- Rule 3 — Added `httpx>=0.27` to requirements.txt. Needed by new broker client. Commit `def5678`.
```

If a deviation keeps re-appearing across tasks, surface it as a PLAN.md gap — original spec was incomplete.

## Rollback (high-risk / Rule-4 actions)

Any high-risk-lane work or Rule-4 action that proceeds (after the human narrows scope, or in a loosened category) MUST record the exact undo command(s) in `specs/<slug>/SUMMARY.md` under `### Rollback` before the work is considered done. Reversibility is a precondition for autonomy — an action you cannot cleanly undo is not eligible for the autonomous path.

> example — substitute your stack

```markdown
### Rollback

- Revert migration: `alembic downgrade -1`
- Revert code: `git revert <sha>`
```
