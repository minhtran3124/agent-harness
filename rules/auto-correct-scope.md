---
paths:
  - "specs/**"
---

# Auto-Correction Scope

Path-scoped (not auto-loaded): injected when any `specs/**` file is read. Task subagents also
load it via the rule path injected into their dispatch prompt (`subagent-driven-development`).

This rule classifies what Claude may self-fix during implementation and what requires user
confirmation. It reduces HITL and keeps trust.

Applies when executing a `specs/<slug>/PLAN.md` task. For ad-hoc single fixes, user judgment rules.

Related: `plan-format.md`, `guidelines.md`, `orchestration.md`, `skills/feature-intake/SKILL.md`.

## Lane-aware autonomy

The intake lane (`specs/<slug>/SUMMARY.md`, set by `feature-intake`) decides how much autonomy applies. Rules 1–4 below are constant. The lane decides whether a plan and a human confirmation are required first. The classification algorithm that assigns the lane lives in `skills/feature-intake/SKILL.md` Step 3, the canonical source. The table below is a separate axis: the autonomy this repo grants per lane.

| Lane | Autonomy | Plan | Human confirm |
|---|---|---|---|
| **tiny** | Full auto — direct patch on a fresh branch | none | none (machine gates are the safety net: `commit-gate.sh`, `branch-isolation-guard.sh`) |
| **normal** | Auto with proof gates (one task reviewer, two verdicts) | yes | only if confidence low / ambiguous |
| **high-risk** | Auto-plan, gated-execute | yes (full chain) | only on ambiguity or a hard gate (Rule 4) |

### Branch isolation (canonical policy)

Create a dedicated branch before the first implementation edit. This does not scale with
ceremony. The tiny lane uses `git checkout -b <type>/<slug>`. The normal and high-risk lanes use
`using-git-worktrees` for an isolated worktree + branch. Never implement on a shared branch.

`hooks/branch-isolation-guard.sh` enforces this for every lane. It uses
`HARNESS_SHARED_BRANCHES` (default `main master`). Only `specs/*` bookkeeping is exempt, so intake
can record `SUMMARY.md` first. Break glass with `BRANCH_ISOLATION_REASON=<why>`. The hook records
the override in `docs/harness-experimental/break-glass-log.md`.

> **Evidence the lane requires (single source of truth):** `scripts/verify_summary.py --lane` mechanizes the lane → evidence mapping. This keeps this table, `skills/feature-intake/SKILL.md` (Step 7), and the `SUMMARY.md` checks from drifting apart. It reads `specs/<slug>/SUMMARY.md` and asserts:
>
> - **tiny** → filled `Lane`/`Confidence`/`Reason`.
> - **normal** → + a non-placeholder `### Verify` row.
> - **high-risk** → + a non-empty `### Rollback`, and a `### Not auto-verified` section. The `### Not auto-verified` check is **advisory by default**: it prints a warning and still exits 0. Set `REQUIRE_NOT_AUTO_VERIFIED=1` to make it blocking. Blocking is the intended end state once the back catalogue has drained.
> - **any lane, `Input-type: bug fix`** → + a `red`/`green` row pair in `### Verify`, or a `Red test exempt: <reason>` line. The `red` row's command is `python3 scripts/run_at_commit.py <red sha> -- <test command>`, where `<red sha>` is the commit that adds the failing test before the fix. Its Exit is from 1 to 123. The `green` row runs the same test command with Exit 0. After the red commit, a change must exist outside `specs/` and the red test files. This check is **advisory by default**. Set `REQUIRE_RED_TEST=1` to make it blocking.
>
> Run `python3 scripts/verify_summary.py --lane <slug>` (exit 1 = missing evidence). Edit the mapping there, not only in prose. `hooks/commit-gate.sh` **enforces** the mapping at commit time (`check_lane_evidence`, in the `standard` and `strict` profiles) on every staged `specs/<slug>/SUMMARY.md`. The staged copy is what is checked, so a commit that adds the missing evidence self-unblocks.

Rule 4 (STOP) still fires inside **every** lane. A hard gate discovered mid-task escalates regardless of how the work was classified. Ceremony scales with risk. The human gate scales with ambiguity, not risk.

**The record is always-on. Verification substitutes for the human gate.** Every lane writes `SUMMARY.md` (the audit record, incl. `Rationale` / `Alternatives`). For autonomous work, a re-runnable `### Verify` row + independent review earn the skipped human confirmation. Extra planning docs do not earn it. Plan-ahead docs (`design` / `research-brief` / `PLAN`) scale by signal (`rules/orchestration.md` → Artifact policy). `FULL_ARTIFACTS=1` forces the full set when maximum traceability is wanted.

## Rule 1 — Auto-fix (no ask)

Obvious bugs discovered during implementation:

- Wrong ORM/data-access query (missing join, incorrect filter, soft-delete not respected)
- Off-by-one, null-check miss, wrong comparison operator
- Logic contradicting the task's `Action`
- Test failures caused by the implementation mistake (not test design)
- Missing `await` on async call, or sync call in async context
- Typos in identifiers

## Rule 2 — Auto-add (no ask)

Missing functionality clearly required by project standards but not explicitly listed in the task's `Action`:

- Input validation at API boundary (your validation layer / schema, guard clauses)
- Error handling for documented failure modes (datastore errors, upstream 4xx/5xx)
- Missing imports, type hints, schema fields
- Your error factory (e.g. `BadRequest / NotFound / ServerError`) where a bare framework exception was used
- Logging in your project's logging convention (`techstacks/`) where an exception was swallowed silently

## Rule 3 — Auto-fix blocking

Issues preventing the task from completing:

- Missing dependency (add to your dependency manifest, note rationale in SUMMARY)
- Syntax error in Claude's own output
- Wrong import path
- Migration revision ID collision (regenerate)
- Linting / type-check failures (your linter / type-checker) on newly-written code

## Rule 4 — STOP + ask user

> **Canonical gate list:** the hard-gate vocabulary lives in `harness-manifest.json`. The diff-detectable gates are under `hard_gates.detectable` (enforced by `hooks/commit-gate.sh`'s `check_risk`). The judgment-only STOP items below are under `hard_gates.judgment` (removing functionality, session/scope, replacing a service). Keep this list in sync with the manifest. The harness repo's `scripts/check_manifest.py` guards the detectable half in harness CI (it does not deploy into a consuming repo).

Changes requiring architectural judgment — NEVER auto-apply:

- Schema changes (add/remove/rename DB table or column) not in the task's `Action`
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

- Rule 2 — Added a `BadRequest` guard for invalid input. `src/services/<entity>_service.<ext>`. Commit `abc1234`.
- Rule 3 — Added `<library>>=<version>` to the dependency manifest. Needed by the new client. Commit `def5678`.
```

If a deviation keeps re-appearing across tasks, report it as a PLAN.md gap: the original spec was incomplete.

## Rollback (high-risk / Rule-4 actions)

This section applies to any high-risk-lane work or Rule-4 action that proceeds (after the human narrows scope, or in a loosened category). That work MUST record the exact undo command(s) in `specs/<slug>/SUMMARY.md` under `### Rollback` before it is considered done. Reversibility is a precondition for autonomy. An action you cannot cleanly undo is not eligible for the autonomous path.

> example — substitute your stack

```markdown
### Rollback

- Revert migration: `<migration downgrade command>`
- Revert code: `git revert <sha>`
```
