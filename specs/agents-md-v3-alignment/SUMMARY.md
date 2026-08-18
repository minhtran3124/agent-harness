# agents-md-v3-alignment — Summary

Lane: tiny
Confidence: high
Reason: docs-only edit to root `AGENTS.md`. Trips no hard gate — the path matches neither the `workflow-engine` signal (`skills/`, `agents/`, `rules/`) nor any `ci-strict-gate.sh` tier (`hooks/`, `settings.json`, `templates/`, `render_plan.py`, `scripts/`).
Flags: existing behavior
Affects: contributor-facing repo guidelines
Input-type: docs correction
Route: tiny → branch + direct edit
Escalate: no

### Intent

Audit `AGENTS.md` and `CLAUDE.md` against `main` after the v3.0.0 release and correct
whatever drifted.

## What changed

`AGENTS.md` only. `CLAUDE.md` needed no change — every load-bearing claim in it was
verified against the tree (see Verify).

- Structure list gained `runtime/`, `adapters/`, and `techstacks/` — all three are tracked
  top-level directories that the list omitted.
- The `deploy-harness.sh` trigger list gained `runtime`; the script has synced it since
  `SYNCED_DIRS_RE` was widened.
- The direct-pytest command gained `runtime/test_*.py` and
  `skills/subagent-driven-development/scripts/test_task_brief.py`, plus a pointer naming
  `PYTESTS` in `run-tests.sh` as the authoritative list.

### Rationale

`AGENTS.md` was last touched 2026-07-21 (`a510320`), before the v3 line added `runtime/`,
`adapters/`, and the evals tree. The stale pytest command was the sharpest edge: a
contributor following it ran zero run-state engine tests while believing they had run the
Python suite.

### Alternatives considered

- Regenerate `AGENTS.md` from `CLAUDE.md`. Rejected: they serve different readers, and
  nothing in the repo treats one as derived from the other.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| documented pytest command runs | `python3 -m pytest scripts/test_*.py runtime/test_*.py skills/visual-planner/test_render_plan.py skills/subagent-driven-development/scripts/test_task_brief.py -q --no-header --no-cov` | 0 | 600 passed | |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | all referenced paths exist; hook table matches settings.json | |
| CLAUDE.md rule tiers still true | `bash tests/scripts/rule-loading-tiers.test.sh` | 0 | 5 always-on / 4 contextual, as documented | |
| every listed dir is tracked | `git ls-files --error-unmatch runtime adapters techstacks` | 0 | the three added entries are real | |

### Not auto-verified

- That `AGENTS.md` is *complete* — *traceability*. The doc-truth lint checks that referenced
  paths exist; nothing checks that every real directory is referenced, which is exactly how
  `runtime/`, `adapters/`, and `techstacks/` went unlisted for four weeks.
- That the prose guidance (indentation, commit style, review policy) matches practice —
  *unverified*. No gate reads it.

### Rollback

- `git revert <sha>`

### Harness-Delta

- backlog → `compound`: `lint-doc-truth.sh` is one-directional — it catches a documented
  path that does not exist, never a real path that is undocumented. A top-level-directory
  coverage check would have caught this drift at the commit that created `runtime/`.
