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
branches its empty-state wording: `status: shipped` renders `_No tasks recorded in this plan._`;
every other status keeps the existing `_No tasks defined yet._`. `summarize_plan_file` was
already parsing frontmatter and discarding it — it now keeps it and passes `status` through.

The defect being fixed is the word "yet": it claims the plan's tasks are still pending. That is
accurate while a plan is being drafted, but false once the plan has shipped — as in
`specs/durable-run-state/PLAN.md`, an acceptance-contract rollup over Phases A–D whose §4 reads
"None — this is a rollup of already-completed work". The shipped wording is deliberately neutral
rather than naming the rollup case: see the review round below.

### Rationale

Fixed at the generator rather than in the affected `PLAN.md`, because the block is script-owned
and regenerated on every save by `hooks/render-plan-on-write.sh` — a hand-edit would be silently
clobbered on the next write. Frontmatter `status` is the only signal already available that
distinguishes "rollup" from "not written yet", and it required no new plan-schema field.

### Alternatives considered

- Hand-edit the rendered line in `specs/durable-run-state/PLAN.md` — rejected: the sentinel block
  is regenerated on every save, so the edit would not survive.
- Change the empty-state wording unconditionally — rejected: it would drop the useful "not
  authored yet" signal for a genuinely empty draft plan, which is still accurate there.
- Add a dedicated `rollup: true` frontmatter field — rejected: it would require a
  `rules/plan-format.md` schema change for a rendering nicety. Neutral wording gets the false
  claim out without adding a field authors must remember to set.
- Label the shipped-and-empty case a rollup (the first revision of this change) — **withdrawn
  after review**, see below.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| renderer unit tests (incl. the empty-state cases) | `python3 -m pytest skills/visual-planner/test_render_plan.py -q` | 0 | 82 passed | |
| shipped + task-less renders neutral wording, never a guessed "rollup" | `python3 -m pytest skills/visual-planner/test_render_plan.py -k empty_tasks -q` | 0 | 4 passed, 78 deselected | |
| plan renderer still round-trips a real plan end-to-end | `python3 skills/visual-planner/render_plan.py specs/plan-at-a-glance/PLAN.md` | 0 | writes PLAN.html (gitignored) | |

<!-- Deliberately NOT listed: `bash scripts/run-tests.sh` (whole-suite row — exceeds the 60s
     cap, per docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md) and
     `ruff format --check` (exit 127 on the CI runner — ruff is not installed there, so the
     row is not re-runnable where the gate runs). Both were listed in the first revision of
     this file and both were rejected by ci-strict-gate; see the Review round below. The full
     suite was still run locally (ALL GREEN) — it is just not a valid Verify row. -->


### Review round — PR #170

**Codex P2 — "Require an actual rollup signal" (accepted, premise corrected).** The first
revision rendered `_Rollup plan — no tasks of its own._` for a `status: shipped` task-less plan.
Verified the objection against ground truth: `skills/finishing-a-development-branch/SKILL.md`
Step 4 sets `status: shipped` on whichever `PLAN.md` the branch resolves to, as a lifecycle
signal that "the feature reached a PR". It carries no rollup semantics, so
"shipped + no tasks ⟹ rollup" was an unsound inference — any ordinary task-less plan that
shipped would have been mislabelled, and regenerated that false claim on every save.

Fixed by making the shipped case **neutral** (`_No tasks recorded in this plan._`) instead of
guessing. That still removes the original defect — "yet" falsely claiming pending work — without
asserting something the renderer cannot know. Added a regression test that fails if the word
"rollup" ever reappears in the shipped empty-state output.

**ci-strict-gate BLOCKED (run 30192872992) — my Verify rows were not machine-verifiable.**
Two of the three rows in the first revision failed `verify_summary --check`:

| Row | Gate result | Cause |
| --- | --- | --- |
| `bash scripts/run-tests.sh` | `TIMEOUT (limit: 60s)` | A whole-suite row — exactly what `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md` says never to list |
| `ruff format --check …` | `MISMATCH claimed=0 actual=127` | Exit 127 = command not found; `ruff` is not installed on the CI runner, so the row is not re-runnable where the gate runs |

Replaced with three targeted rows that run in CI in well under 60s. The full suite is still run
locally; it is simply not a valid Verify row.

### Rollback

- `git revert <sha>` — pure rendering change, no state or schema migration. Any `PLAN.md` whose
  At-a-glance block was regenerated with the new wording reverts to `_No tasks defined yet._` on
  its next save.

### Harness-Delta

- none
