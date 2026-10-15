# Intent: STE rollout to the remaining harness prose (Phase 3)

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

Phases 1–2 (`specs/ste100-harness-prose/`, PR #293) rewrote only three pilot files in
ASD-STE100 style. The pilot passed (`specs/ste100-harness-prose/DECISION.md`), so the design
allows the rollout. The rest of the agent-executed prose in `rules/`, `skills/` and `agents/`
still has 290 hard STE lint findings across 46 files (`scripts/ste-baseline.json`). The pilot
also showed that an STE rewrite can drop a scope qualifier silently. Only a per-file
meaning-equivalence review caught it, and the task-reviewer prompt does not run that review by
default.

## Proposed outcome

- Every in-scope prose file is rewritten in STE-flavored mode, as in the pilot, in waves of 4–6
  files. Each wave lowers the baseline entries of the files it touches and passes
  `bash scripts/run-tests.sh`.
- Each rewritten file gets a meaning-equivalence verdict from the task reviewer.
- The task-reviewer prompt has a meaning-equivalence instruction for changed prose files, so the
  review runs without a plan asking for it. This lands before the first rewrite wave.
- `scripts/check_scope_qualifiers.py` lists condition words (if, unless, only, when, never,
  except, for a new, without) that a removed prose line had and no added line in the same hunk
  has. `review_package.py` shows the list as an advisory section beside `## STE lint`.
- `feature-intake` tells the tiny lane to apply `skills/asd-ste100/SKILL.md` to direct edits of
  agent prose, within the 600-word ceiling.

## Affected users and systems

- Every agent that reads harness rules, skills, dispatch prompts and agent definitions, in this
  repo and in consumer repos after deploy.
- The SDD task reviewer and `review_package.py`.
- `scripts/ste-baseline.json`.

## Constraints

- Branch `docs/ste100-prose-rollout` is stacked on `docs/ste100-harness-prose`. The PR targets
  that branch until PR #293 merges, then it is retargeted to `sdlc`.
- No meaning change. A literal-grep test that a rewrite breaks is fixed in the prose, never by
  loosening the test.
- The 600-word ceiling from `audit_skill_prompts.py` stays. SDD `SKILL.md` is at 600/600 and
  `feature-intake/SKILL.md` at 599/600.
- `synonym-rotation` stays excluded from the blocking count.
- The qualifier-drop section is advisory only. It never fails a build or a review by itself.

## Out of scope

- Eval fixtures (`skills/*/tests/*.md`).
- Templates: `skills/*/templates/`, `agents/PROJECT.template.md`,
  `skills/brainstorming/references/design-template.md` and
  `skills/xia2/references/research-brief-template.md` (assumed: they define output shape).
- The vendored `skills/asd-ste100/` and the three pilot files.
- Files with a baseline count of 0 (assumed: no measured finding to fix).
- A new paid pilot. The Phase 2 pilot result covers the method.
- Consumer `PROSE_ROOTS` scope and the other advisory correctness findings from PR #293.

## Open questions

- none

## What success looks like

- `python3 scripts/check_ste_baseline.py --strict` exits 0, and every in-scope file's baseline
  entry is lower than or equal to its value at the start of this PR.
- A task-review meaning-equivalence verdict exists for each rewritten file.
- `bash scripts/run-tests.sh` is all green, and the context-propagation audit, correctness review
  and intent review pass.

## Original request

let start for phase 3 now
