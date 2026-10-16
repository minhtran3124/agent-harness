# Intent: Agreed test seams from plan to implementer to reviewer

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

The implementer writes the code and its tests from the same assumptions, and nothing tells it
where a test must observe behavior. On gh-175 every per-task review passed and 145 tests were
green. The plan-blind correctness review then found about 11 real bugs, because the tests were
fitted to synthetic fixtures that shared the implementation's blind spot
(`docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md`). Today:

- a plan task names what it consumes and produces (`Interfaces`), but not where its tests
  observe behavior;
- the implementer prompt says only "Write tests. Follow TDD if the task says to.";
- the task reviewer's quality verdict does not check where a test sits or where its expected
  values come from.

## Proposed outcome

1. **Plan.** `rules/plan-format.md` and `skills/writing-plans/SKILL.md` add a separate
   `- **Seams:**` task field directly after the `Interfaces` line (format B, decided by the
   user). A seam is the point where the test observes behavior. One seam is the ideal number.
   The field states what the seam catches and what it misses, for example:
   `` - **Seams:** `decide()` JSON output — catches: wrong next_task; misses: file I/O errors. ``
2. **Implementer.** In `skills/subagent-driven-development/implementer-prompt.md`, "Write tests.
   Follow TDD if the task says to." is replaced by these rules:
   - Write tests only at the declared seams.
   - Take each expected value from an independent source: a known-good literal, a worked
     example, or the spec.
   - If a test breaks on a refactor and the behavior did not change, the test is
     implementation-coupled. Rewrite it.
3. **Reviewer.** The quality verdict in `task-reviewer-prompt.md` gets a seam-conformance check:
   each new test sits at a declared seam, and the implementer copied no expected value from the
   implementation.
4. **Resume.** The seam list reaches the implementer and the reviewer after `resume <slug>` from
   a fresh session. `task_brief.py` rebuilds the brief from the plan. (observed: `task_brief.py`
   copies the whole task block into the brief, and `render_plan.py` appends an unknown bullet
   to the field before it, so the `Seams:` field reaches the brief and shows in the Interfaces
   cell of `PLAN.html` with no change to either parser; the context-propagation audit confirms
   this)
5. **Check.** `scripts/check_plan_contract.py` rejects (exit 1, blocking, decided by the
   user) a new contract plan with a task that has no `- **Seams:**` field. A task with no
   behavior to test writes `- **Seams:** none — <reason>`, and the check accepts that form only
   with a non-empty reason.
6. **Opt-in marker (Q3, option A, decided by the user).** `writing-plans` writes a
   `Plan-contract: 2` line inside `## Global Constraints`. `check_plan_contract.py` requires the
   `Seams:` field only on a plan that carries this marker. A contract plan without the marker
   keeps today's checks and stays valid. This follows the existing opt-in pattern, where
   `## Global Constraints` itself opts a plan into the contract.

## Affected users and systems

Agents that write plans (`writing-plans`), implementer and task-reviewer subagents under
`subagent-driven-development`, and users who read plans and review receipts. Consumer repos get
the change on their next harness re-sync.

## Constraints

- The bug-fix red/green rules in the implementer prompt stay as they are.
- Legacy plans (no `## Global Constraints`) keep parsing and executing unchanged.
- The 36 committed plans that already declare `## Global Constraints` have no `Seams:` entry.
  They must not start to fail `check_plan_contract.py`: `subagent-driven-development` runs the
  check before execution and on resume, and `scripts/check_task_review_adoption.py` runs it on
  `specs/superpowers-6-review-pipeline-adoption/PLAN.md` on every `run-tests.sh` and CI run.
  Proposed outcome 6 meets this constraint. Repo consumers may have contract plans in flight
  when they re-sync; the marker keeps those valid too.
- `skills/subagent-driven-development/SKILL.md` is at 600 of 600 words. If it must change, the
  deletion-test procedure (`docs/solutions/harness/deletion-test-for-word-ceiling.md`) frees
  the words first.
- Edited agent prose follows `skills/asd-ste100/SKILL.md`.
- PR targets `sdlc`.

## Out of scope

- Changes to `skills/visual-planner/render_plan.py` and `runtime/resume_decision.py`. (assumed:
  not needed, see Proposed outcome 4; if the audit finds otherwise, escalate, because
  `render_plan.py` is a high-blast file)
- Rewriting existing tests or plans to add seams.
- The prove-the-red check (#313) and the diagnosing-bugs skill (#318).
- Changes to `correctness-review`; it stays the plan-blind oracle.

## Open questions

- Q1 (decided by the user): the check is required and blocking, not warn-only. See Proposed
  outcome 5.
- Q2 (decided by the user): format B, a separate `- **Seams:**` field after `Interfaces`; a task
  with no behavior to test writes `- **Seams:** none — <reason>`.
- Q3 (decided by the user): option A, the `Plan-contract: 2` marker. See Proposed outcome 6.
  Rejected: skip `status: shipped` plans, a git-date cutoff, backfilling the 36 plans, and
  blocking every contract plan after fixing the known callers.

## What success looks like

- The recorded gh-175 fixture-fitted case, replayed through the task reviewer with the seam
  check, gets at least the implementation-coupled tests flagged that the correctness review
  found later (the issue's proof).
- The context-propagation audit shows the seam list reaches the implementer and the reviewer on
  both the same-session path and the `resume <slug>` path.
- `check_plan_contract.py` exits 0 on each of the 36 committed contract plans, and exits 1 on a
  `Plan-contract: 2` plan with a task that has no `Seams:` field or an empty `none —` reason.
- `bash scripts/run-tests.sh` passes.

## Original request

ok

(Agreed plan from the previous turn: close #302, park #310, and start #312 with feature-intake
in a new worktree cut from `sdlc`. GitHub issue #312, "[P2] Lesson 2: agreed test seams from plan
to implementer to reviewer": Declare the test seams in the plan. Send them to the implementer and
to the reviewer. Ban tautological tests. Steps — 1. Plan: extend the `Interfaces` line in
`rules/plan-format.md` and `skills/writing-plans/SKILL.md` with a `Seams:` entry for each task. A
seam is the point where the test observes behavior. One seam is the ideal number. Add a one-line
note on what the seam catches and what it misses. 2. Implementer: in
`skills/subagent-driven-development/implementer-prompt.md`, replace "Write tests. Follow TDD if
the task says to." with these rules: write tests only at the declared seams; take each expected
value from an independent source: a known-good literal, a worked example, or the spec; if a test
breaks on a refactor and the behavior did not change, the test is implementation-coupled —
rewrite it. 3. Reviewer: add a seam-conformance check to the quality verdict in
`task-reviewer-prompt.md`. Each new test sits at a declared seam. The implementer copies no
expected value from the implementation. 4. Resume path: the context-propagation-audit must show
that the seam list survives `resume <slug>` from a fresh session. `task_brief.py` rebuilds the
brief. Lane: high-risk. Dependencies: #308. Proof: replay the recorded fixture-fitted case
through the task reviewer with the seam check; the issue passes when the reviewer flags at least
the implementation-coupled tests that the correctness review found later.)

Q1: bat buoc có check
Q2: đề xuất

Q1 - required check
Q2 - B

phân tích câu Q3

A
