# agents — Project Configuration

Thin **index** consumed by the execution sub-agents (`coding.md`, `test-runner.md`). It does
**not** restate conventions — it points to the docs that already hold them, and carries only the
few execution facts no other doc reliably contains. Fill it in per project.

> **Why an index, not a copy:** most repos already document architecture, style, and testing
> somewhere. Re-describing that here creates a second source of truth that drifts. Point to the
> real doc; only inline a convention when the repo has no doc for it.
>
> Sibling: `skills/xia2/PROJECT.md` (risk-classification signals). Identity lives there — link, don't copy.

---

## Convention sources (point, don't restate)

The agents read these for layering, error/validation, style, and logging. Give the path, or `none`.

- **Architecture / layering:** <path, e.g. `.claude/rules/architecture.md`> — or `none` *(active stack profile; start from `templates/stacks/_skeleton/` or edit directly)*
- **Code style / error handling / validation / logging:** <path, e.g. `.claude/rules/guidelines.md`> — or `none` *(active stack profile; start from `templates/stacks/_skeleton/` or edit directly)*
- **Project identity (name / stack / repo root):** fill the *Inline fallback* below.

> If both paths are `none` **and** there is no `xia2/PROJECT.md`, fill the **Inline fallback**
> section so the agents have something to work from.

---

## Test execution (agent-specific — usually not in the docs above)

Consumed by `test-runner.md` and the coding agent's validation step. For per-runner command/flag
examples across languages, see `test-runner.md → Common Test Runners`.

- **Test command:** <exact command, e.g. `cd apps/api && python -m pytest`>
- **Targeted-run flags:** <e.g. `-x` stop at first failure, `-k <name>` filter, `--tb=short`>
- **Source → test mapping:** <e.g. `app/services/x.py` → `tests/services/test_x.py`>
- **Markers / coverage:** <e.g. markers `unit/integration/edge_case/slow`; gate `--cov-fail-under=80`> — or `see guidelines doc`

---

## Failure diagnosis hints (optional)

Stack-flavored hints layered on top of test-runner's generic categories.

- <e.g. async: missing `await`, wrong async-mock setup, event-loop conflict>
- <e.g. validation: schema/model change broke test-data construction>
- <e.g. data layer: model change without updating fixtures/mocks>

---

## Inline fallback (only if no convention doc exists above)

Leave this empty when the *Convention sources* paths are filled — it exists solely for a bare repo
with no architecture/style docs. Describe the minimum the implementer needs.

- **Layering / flow:** <e.g. `router → use-case → service → repository → model`; keep the entry layer thin, no business logic>
- **Invariants:** <e.g. soft-delete `deleted_at IS NULL`; isolated session for background/streaming work>
- **Error pattern:** <e.g. shared exception factory; guard clauses first; consistent error responses>
- **Input validation:** <e.g. typed models at boundaries (RORO) — never raw dicts>

---

## Notes for maintainers

- The index **points**, it does not duplicate. If you catch yourself copying a doc's content here, link the doc instead.
- Update the convention-source paths when docs move; re-review the two agents after a layer or test-runner change.
- Kept separate from `skills/xia2/PROJECT.md` (risk signals). The agents must also work in a repo that does not use `xia2`.
