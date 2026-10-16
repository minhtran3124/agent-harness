# gh-312-test-seams — Design

Written 2026-10-16. Pins: repo 2cd6403

## Goal

Make the plan, the implementer and the task reviewer agree on where each test observes behavior
and on which inputs. The target failure is the gh-175 failure: green per-task reviews over tests
fitted to one synthetic fixture.

## Reading path

1. `intent.md` — the approved request and the user's decisions (Q1–Q3, B1–B8). Read it first.
2. `design.md` (this file) — how the decisions become files, checks and rules.
3. `SUMMARY.md` — lane, intake notes, and later the Verify evidence. Skip the template comments.
4. `canary.md` (written during implementation) — the SC-5 canary and the gh-175 replay results.

## Current state

- `rules/plan-format.md:44-54` defines the context contract. A plan opts in by declaring
  `## Global Constraints`. Each task then carries `Criteria` and `Interfaces`. No field says
  where a test observes behavior.
- `scripts/check_plan_contract.py` enforces the contract only on plans with
  `## Global Constraints`. It reads `Criteria` and `Interfaces` with a one-line regex (`:24`).
- `skills/subagent-driven-development/implementer-prompt.md:44` says only "Write tests. Follow
  TDD if the task says to.", followed by the bug-fix red/green rules.
- `skills/subagent-driven-development/task-reviewer-prompt.md` gives the reviewer the brief, the
  report and the review package. The prompt allows "one named, focused read-only search" and
  says "Do not crawl the repository broadly" (`task-reviewer-prompt.md:28-30`). The package
  holds the full `-U10` diff
  (`skills/subagent-driven-development/scripts/review_package.py:90`). The quality verdict checks STE lint only.
- `skills/subagent-driven-development/scripts/task_brief.py:23,56` copies the
  `## Global Constraints` section and the whole task block into the brief.
- `skills/visual-planner/render_plan.py:256` appends a bullet with an unknown field name to the
  field before it.
- 36 committed plans declare `## Global Constraints` (measured 2026-10-16, `grep -l` over
  `specs/*/PLAN.md`): 35 `status: shipped`, 1 `status: active` (`gh-261`, issue closed).
  `scripts/test_check_task_review_adoption.py` runs the checker on one shipped plan in every
  `run-tests.sh` and CI run.
- gh-175 record: the correctness review found 11 bugs (`specs/gh-175-executable-resume-cursor/
  SUMMARY.md:110`). The tests at `e76b0fe` observe `decide()` JSON output with literal expected
  values, and all of them use the one synthetic fixture `_ACTIVE_MD_PLAN`
  (`runtime/test_resume_decision.py:30` at that commit).

## Approaches considered

- **A. Rules inline in both prompts (chosen).** The implementer rules go into
  `implementer-prompt.md`. The seam check goes into `task-reviewer-prompt.md`.
  `scripts/check_task_review_contract.py` pins the key phrases in both. Each rule is in the
  dispatch prompt, so delivery does not depend on a subagent Read. Cost: about 120 more words
  (prediction) in the implementer prompt, and one rule written twice.
- **B. Shared reference file.** One source, but delivery depends on a subagent Read, and the task
  reviewer may read only the paths it receives.
- **C. `task_brief.py` injects a `## Test rules` section.** Delivery is certain and B8 is
  automatic, but the policy becomes a string in Python and every resume brief changes.

## Architecture

| File | Change |
|---|---|
| `rules/plan-format.md` | Define the `- Plan-contract: 2` marker (a bullet inside `## Global Constraints`), the `- **Seams:**` field after `Interfaces`, the `none — <reason>` form, and one example |
| `skills/writing-plans/SKILL.md` | Step 3: write the marker, and write `Seams:` for each task |
| `scripts/check_plan_contract.py` | Seam checks, only on a plan that carries the marker |
| `scripts/test_check_plan_contract.py` | Unit tests for each error row, and a corpus test over `specs/*/PLAN.md` |
| `skills/subagent-driven-development/implementer-prompt.md` | Replace "Write tests. Follow TDD if the task says to." with the test rules |
| `skills/subagent-driven-development/task-reviewer-prompt.md` | Add the seam check to the quality verdict |
| `scripts/check_task_review_contract.py` | Pin the key phrases of both prompts |
| `specs/gh-312-test-seams/canary.md` | Canary record (pass criterion) and gh-175 replay record (evidence) |

Field format:

A task with a seam:

```markdown
- **Interfaces:** Consumes: PLAN.md text. Produces: `resume_decision.py`.
- **Seams:** `decide()` JSON output — catches: wrong next_task; misses: file I/O errors.
```

A task with no behavior to test (an alternative to the line above, not a second line):

```markdown
- **Seams:** none — prose-only change, no behavior to test.
```

Each task has exactly one `- **Seams:**` bullet, on one line. One seam is the ideal number. Inside
one seam, `;` separates the `catches:` clause from the `misses:` clause. When a task needs more
than one seam, the same line names each of them, separated by ` | `, and each seam has its own
`catches:` and `misses:`:

```markdown
- **Seams:** `decide()` JSON output — catches: wrong next_task; misses: file I/O errors | `parse_tasks()` list — catches: dropped tasks; misses: Status-Log parsing
```

The checker reads the first line of the bullet only, as it does for `Criteria` and `Interfaces`,
so a continuation line is not read.

Data flow: `writing-plans` writes the marker and the seams. SDD runs `check_plan_contract.py`
before the first task (`skills/subagent-driven-development/SKILL.md:36-41`). The resume path runs
`resume_decision.py`, which does not run the checker; a resumed run keeps the plan that was
checked before its first task. `task_brief.py` copies `## Global Constraints` (with the
marker) and the whole task block (with `Seams:`) into the brief. The implementer and the
reviewer read the brief. The reviewer also reads the diff in the package and searches the repo
for real inputs with its read-only Grep and Glob tools.

Implementer rules (step 2 of the prompt):

1. Write tests only at the seams in the task's `Seams:` field. When the brief has no
   `Plan-contract: 2` line, skip this rule only.
2. When `Seams:` is `none`, write no new test.
3. If a declared seam cannot observe the behavior, return `NEEDS_CONTEXT` before any edit. Do
   not choose another seam.
4. Take each expected value from a source that is independent of the code: a known-good
   literal, a worked example, or the spec. Do not copy a value from the output of the code.
5. When the repo holds real inputs of the seam's shape, also test the seam on those inputs.
6. A test that fails after a refactor that does not change behavior is implementation-coupled.
   Rewrite it.
7. Bug fix: the red test sits at a declared seam. The other red/green rules stay. A bug-fix
   task whose seam is `none` has no place for its red test, so this is the unusable-seam case of
   rule 3: return `NEEDS_CONTEXT` before any edit.

Reviewer seam check, for each new or changed test in the diff. Each failure is an Important
quality finding:

1. With the marker: the test sits at no declared seam, or the task's seam is `none`.
2. An expected value is copied from the output of the implementation.
3. The test uses only synthetic fixtures while real inputs of the seam's shape exist. For this
   step the reviewer may run one more named, focused read-only search for each declared seam,
   in addition to the one search that the prompt allows today. On a plan without the marker,
   the allowance is one search for each new or changed test file. It cites each search in
   `search_surface`. The ban on crawling the repository broadly stays.

Without the marker, the reviewer skips step 1 and does steps 2 and 3.

## Error behavior

`check_plan_contract.py` keeps exit 0 for pass and exit 1 for a rejection, with one message
line for each problem in the existing `name: Task <id> ...` form.

| Case | Result |
|---|---|
| Marker present, every task has a valid seam | exit 0 |
| Marker present, a task has no `- **Seams:**` field | exit 1 |
| Marker present, a task has two or more `- **Seams:**` bullets | exit 1 |
| `Seams: none` with an empty reason | exit 1 |
| A seam (a ` \| `-separated part that is not `none`) without `catches:` or without `misses:` | exit 1 |
| `catches:` or `misses:` followed by no text before the next `;`, the next ` \| `, or the end of the line | exit 1 |
| `Plan-contract:` with a value other than `2` | exit 1, unknown version (fail closed) |
| Marker outside `## Global Constraints`, inside a code fence, or written without the leading `- ` | not a marker; today's checks only |
| No marker (the 36 committed plans, measured 2026-10-16) | today's checks only |

An implementer that meets an unusable seam returns `NEEDS_CONTEXT`. The SDD controller already
handles that status. A reviewer finding goes through the existing Important fix round.

The checker cannot tell a bug-fix task from other tasks, because `Input-type` is in
`SUMMARY.md`, not in the plan. So a bug-fix task with `Seams: none` passes the checker and is
caught by implementer rule 7.

If the canary (SC-5) fails, fix the reviewer prompt and run the canary again. After two failed
runs (budget), stop and escalate under `rules/orchestration.md` "Repeated `Verify` failure".

## Tests

- Unit tests (truth): one test for each row of the error table.
- Corpus test (truth): the checker exits 0 on every committed `specs/*/PLAN.md`.
- Phrase pins (traceability): `check_task_review_contract.py` reads both prompts (today it reads
  only `task-reviewer-prompt.md`) and fails when a pinned phrase leaves either one.
  `scripts/test_check_task_review_contract.py` gets a case for each prompt.
- Brief test (truth): `task_brief.py` on a marker plan gives a brief that holds the marker line
  and the `Seams:` line.
- Canary (truth, one sample): a real task-reviewer dispatch on a synthetic task with one
  off-seam test and one test with a copied expected value.
- gh-175 replay (evidence only): seams written after the fact for the gh-175 task, and the
  reviewer run on `ba964a3..e76b0fe`.
- `bash scripts/run-tests.sh` and `scripts/ci-strict-gate.sh` pass.

## Success criteria

- SC-1: each error-table row has a unit test, and `python3 -m pytest
  scripts/test_check_plan_contract.py -q` exits 0.
- SC-2: the checker exits 0 on every committed plan (corpus test).
- SC-3: `python3 scripts/check_task_review_contract.py` exits 0, and exits 1 when a pinned
  phrase is removed.
- SC-4: the brief for a task in a marker plan contains `Plan-contract: 2` and the task's
  `Seams:` line.
- SC-5: in the canary run the reviewer returns an Important finding for both bad tests.
- SC-6: `canary.md` records the gh-175 replay result as observed.
- SC-7: `bash scripts/run-tests.sh` exits 0.
- SC-8: `python3 skills/visual-planner/render_plan.py specs/gh-312-test-seams/PLAN.md
  specs/gh-312-test-seams/PLAN.html` exits 0 on this spec's own plan, which carries `Seams:`
  fields, and that `PLAN.html` (gitignored) contains the text of one `Seams:` line.

## Non-goals

- Changes to `render_plan.py`, `resume_decision.py`, `task_brief.py`, `correctness-review`, or
  `subagent-driven-development/SKILL.md`.
- Adding seams to existing plans or rewriting existing tests.
- #313 (prove the red) and #318 (diagnosing-bugs).

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | `task_brief.py` copies `## Global Constraints` and the whole task block into the brief | provenance: Local, 2026-10-16, `task_brief.py:23,56` | SC-4 | The marker or the seam does not reach the subagents; then the brief must learn the field (scripts change) |
| A2 | `render_plan.py` shows an unknown `Seams:` bullet inside the Interfaces cell and does not fail | provenance: Local, 2026-10-16, `render_plan.py:256` | SC-8 | Seams are not visible in `PLAN.html`; escalate, because `render_plan.py` is high-blast |
| A3 | `resume_decision.py` parses a plan with `Seams:` bullets with the same task list as the renderer | none yet; Inference: same field regex as `render_plan.py` (`resume_decision.py:48`) | Existing corpus parity test in `runtime/test_resume_decision.py`, which covers this spec's own PLAN.md once it is committed | A resume skips or repeats tasks; escalate |
| A4 | The task reviewer can search the repo for real inputs, within the search allowance this design adds to its prompt | provenance: Local, 2026-10-16, agent list (task-reviewer tools Glob, Grep, Read) and `task-reviewer-prompt.md:28-30` (one search today) | SC-5 | The real-input check cannot run; the reviewer must report `cannot_verify` for it |
| A5 | All 36 (measured 2026-10-16, `grep -l` over `specs/*/PLAN.md`) committed contract plans pass today's checker | truth: Local, 2026-10-16, checker run over each of those plans by the spec reviewer | SC-2 | The corpus test fails before any change; fix or exempt those plans in a separate task |
| A6 | Rule B2 (real inputs) is what the gh-175 tests lacked | provenance: Local, 2026-10-16, gh-175 SUMMARY and `test_resume_decision.py@e76b0fe` | accepted risk: the gh-175 replay is evidence, not a gate | The replay flags nothing; the record says so, and a follow-up issue owns the gap |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| The checker proves that a seam is the right seam | It checks the field's presence and shape only (traceability). The reviewer judges the seam |
| A reviewer flags every bad test | The check is model judgement. The canary is one sample (SC-5) |
| A plan cannot skip the seam rule | A plan without the marker skips it. Only the plan author adds the marker (decision D3) |
| The gh-175 bugs would now be caught | The replay is recorded as evidence, not as a gate (decision D5) |
| Consumer repos keep working mid-run | Their in-flight plans cannot be observed from here. The marker keeps marker-less plans valid by design |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | A separate `- **Seams:**` field directly after `Interfaces` (intent Q2, format B) | No parser change; the field reaches the brief and the rendered Interfaces cell | settled |
| D2 | The seam check blocks (exit 1), it is not warn-only (intent Q1) | A marker plan without seams cannot start SDD | settled |
| D3 | A `- Plan-contract: 2` bullet inside `## Global Constraints` opts a plan into the seam rule (intent Q3, option A) | The 36 committed plans (measured 2026-10-16) and consumer plans in flight stay valid | settled |
| D4 | The rules sit inline in both prompts, pinned by `check_task_review_contract.py` (approach A) | Certain delivery; the pin test guards drift between the two copies | settled |
| D5 | Proof: canary is the pass criterion; the gh-175 replay is evidence (B1) | The issue's original proof is replaced, because gh-175 recorded bugs, not coupled tests | settled |
| D6 | Test the seam on real inputs when the repo has them; the reviewer flags fixture-only tests (B2) | Widens the issue's scope to the recorded root cause | settled |
| D7 | A seam that is not `none` must contain `catches:` and `misses:` (B3) | The checker can verify the note mechanically | settled |
| D8 | Off-seam test, copied expected value, fixture-only test, and a test in a `none` task are Important (B4, B7) | Each opens a fix round | settled |
| D9 | The bug-fix red test sits at a declared seam (B5) | Red/green rules otherwise unchanged | settled |
| D10 | An unusable seam makes the implementer return `NEEDS_CONTEXT` before any edit (B6) | No silent re-seaming | settled |
| D11 | Without the marker, only the declared-seam rule is skipped (B8) | Legacy plans still get the expected-value and real-input rules | settled |
| D12 | An unknown `Plan-contract:` value fails closed; a marker outside `## Global Constraints` or in a fence is not a marker | No silent pass on a version the checker does not know | settled |
| D13 | Exactly one one-line `- **Seams:**` bullet per task; several seams share the line, separated by ` \| `; each seam has its own `catches:` and `misses:`, separated by `;` | The checker stays a one-line read, like `Criteria` and `Interfaces`, and D7 holds for every seam | settled |
| D14 | A bug-fix task with `Seams: none` is an unusable seam: the implementer returns `NEEDS_CONTEXT` | No conflict between the red-test rule and the `none` rule | settled |
| D15 | The reviewer may run one more named, focused read-only search for each declared seam, or for each new or changed test file on a plan without the marker, for the real-input check | The real-input check does not break the prompt's search limit on either kind of plan | settled |
| D16 | The marker is the bullet `- Plan-contract: 2` inside `## Global Constraints` | One exact form for the checker, the unit tests and the `plan-format.md` example | settled |
