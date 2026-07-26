# at-a-glance-rollup-wording — Summary

Lane: high-risk
Confidence: high
Reason: touches `skills/visual-planner/render_plan.py`, named verbatim in the `high-blast` (block-mode) hard gate in `harness-manifest.json` as "a core skill engine".
Flags: high-blast
Affects: visual-planner renderer — the auto-generated "At a glance" block injected into every `specs/*/PLAN.md` on save
Input-type: harness improvement

### Intent

> fix the At a glance block in the canonical PLAN

(Context from the preceding turn, which surfaced the defect: while updating PR #165's description
I noted "the canonical `PLAN.md` At-a-glance block still renders '_No tasks defined yet._'
(intentional — it's a rollup with no tasks), so it reads oddly if anyone opens it.")

## What changed

`render_summary_block` now takes the plan's frontmatter `status` and, for a task-less plan,
branches its empty-state wording: `status: shipped` renders `_Rollup plan — no tasks of its
own._`; every other status keeps the existing `_No tasks defined yet._`. `summarize_plan_file`
was already parsing frontmatter and discarding it — it now keeps it and passes `status` through.
A shipped plan with no tasks is a deliberate rollup of work done elsewhere (e.g.
`specs/durable-run-state/PLAN.md`, an acceptance-contract rollup over Phases A–D), not a plan
whose tasks are still pending, so "yet" was a false statement about the plan's state.

### Rationale

Fixed at the generator rather than in the affected `PLAN.md`, because the block is script-owned
and regenerated on every save by `hooks/render-plan-on-write.sh` — a hand-edit would be silently
clobbered on the next write. Frontmatter `status` is the only signal already available that
distinguishes "rollup" from "not written yet", and it required no new plan-schema field.

### Alternatives considered

- Hand-edit the rendered line in `specs/durable-run-state/PLAN.md` — rejected: the sentinel block
  is regenerated on every save, so the edit would not survive.
- Change the empty-state wording unconditionally (e.g. "_No tasks in this plan._") — rejected:
  accurate for a rollup but drops the useful "not authored yet" signal for a genuinely empty
  draft plan.
- Add a dedicated `rollup: true` frontmatter field — rejected as speculative; `status: shipped`
  already carries the distinction.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| renderer unit tests (incl. 2 new empty-state cases) | `python3 -m pytest skills/visual-planner/test_render_plan.py -q` | 0 | 81 passed | |
| full harness suite (shell + python) | `bash scripts/run-tests.sh` | 0 | ALL GREEN — 216 python tests; run on the pre-split working tree, same two-file delta | |
| ruff format conformance (touched files) | `ruff format --check skills/visual-planner/render_plan.py skills/visual-planner/test_render_plan.py` | 0 | 2 files already formatted | |

### Rollback

- `git revert <sha>` — pure rendering change, no state or schema migration. Any `PLAN.md` whose
  At-a-glance block was regenerated with the new wording reverts to `_No tasks defined yet._` on
  its next save.

### Harness-Delta

- none
