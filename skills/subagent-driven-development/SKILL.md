---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance review first, then code quality review. After **all** tasks are done, run one final adversarial correctness review over the entire diff, then one intent review against the original request, before shipping.

**Why subagents:** You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task. They should never inherit your session's context or history — you construct exactly what they need. This also preserves your own context for coordination work.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration

## When to Use

Use this skill when a written plan exists and its tasks are mostly independent. Tightly coupled
tasks are a planning problem — re-plan the waves before executing. With no plan at all, go back to
`writing-plans` (or `brainstorming` if the design is not settled).

The same pipeline serves both execution modes — see `## Parallel session` below for the
separate-session variant.

## Step 0 — Validate the plan before any implementation

**Gate. Run these four checks BEFORE the first task. If any fails, STOP, name the specific
violation, and do not execute.** Read `.claude/rules/plan-format.md`,
`.claude/rules/wave-parallelism.md`, and `.claude/rules/auto-correct-scope.md` first — they are
path-scoped, so do not rely on `paths:` injection to have loaded them.

1. **Required fields populated.** Every task has all four non-empty: Files, Action, Verify, Done.
   A `### Task` heading with no field bullets is prose, not a task — but a Tasks section with no
   parseable task at all is a violation. Legacy fenced `<task>` XML blocks carry the same four
   semantics and remain executable: reject a plan for missing semantics, never for its syntax.
2. **Zero file overlap across same-wave tasks** (`wave-parallelism.md` Invariant 1). Name the task
   ids and the overlapping path.
3. **Verify is a single automated shell command**, exit-code-checkable. Reject "manually test in
   browser", "open and check", "visually inspect".
4. **Plan scope matches the trigger threshold** — >3 discrete steps OR >2 files OR ETA >30 min.
   Below all three, stop and suggest a direct edit instead.

Then read the plan for **substantive** concerns and raise them before marking it `active`. The
four checks above are mechanical: a plan can satisfy every one of them and still be wrong —
missing a migration its tasks depend on, sequencing waves against a real dependency, solving the
wrong problem. Surfacing that after wave 1 has burned a task is strictly worse than surfacing it
now. If the approach itself looks wrong, say so and wait; the `BLOCKED` ladder below is the
recovery path, not the intended one.

## The Process

**Step 1 — Load rules and ensure branch isolation.** Read the path-scoped
`.claude/rules/auto-correct-scope.md` and `.claude/rules/wave-parallelism.md`, then apply
`auto-correct-scope.md` → Branch isolation before dispatching wave 1. Do not proceed until work is
on the lane-appropriate dedicated branch. Keep the auto-correct rule path in every implementer
prompt because subagents cannot rely on the orchestrator's copy.

**Next — mark the plan active.** Before dispatching wave 1, set the frontmatter
`status: proposed → active` in `specs/<slug>/PLAN.md` (canonical values only:
`proposed | active | paused | shipped`). `hooks/blast-radius-check.sh` keys on `status: active` to
identify the active plan, and the edit auto-re-renders `PLAN.html` via `render-plan-on-write.sh`.
Append commit shas to `## Status Log` after each wave (`rules/wave-parallelism.md`); the `shipped`
transition happens later in `finishing-a-development-branch`.

**Step 2 — Per task, in order.** For each task in the current wave:

1. **Dispatch the implementer** (`./implementer-prompt.md`) with the task's **full text** —
   the controller extracts every task from the plan up front and pastes what the subagent needs.
   A subagent must never be told to go read `PLAN.md` itself: it gets exactly the constructed
   context, and nothing of the orchestrator's session history.
2. **Answer its questions before it works.** If it asks, answer completely and re-dispatch; do
   not rush it into implementing on a guess.
3. **Spec compliance review** (`./spec-reviewer-prompt.md`) — does the code match the task spec,
   with nothing missing and nothing extra? Issues → the same implementer fixes → re-review.
4. **Code quality review** (`./code-quality-reviewer-prompt.md`) — **only after spec compliance
   is green.** Running quality first is the wrong order: it polishes code that may not yet be the
   right code. Issues → fix → re-review.
5. **Mark the task complete** and move on. Never advance while either review has an open issue.

**Step 3 — After all tasks pass, run the final chain over the whole diff, in this order:**
`/context-propagation-audit` (only if the cumulative diff touches the workflow-engine inventory)
→ `/correctness-review` → `/intent-review` → write the review receipt →
`finishing-a-development-branch`. Each stage below owns its own contract; an unresolved finding at
any stage blocks the next.


## Wave-aware parallelism policy

This skill can execute implementation tasks in parallel **only** when they are grouped in the same `wave` and are safe to run concurrently.

Parallel dispatch is allowed when ALL are true:

- Tasks are in the same wave from `specs/<slug>/PLAN.md`
- File sets are disjoint (zero overlap)
- No unresolved task dependency inside the wave
- Controller dispatches all wave tasks in ONE assistant message (parallel tool calls)

Use sequential dispatch when ANY are true:

- Tasks touch the same file(s)
- A task depends on outputs of another task in the same wave
- Task scope is ambiguous and requires clarification first

When in doubt, choose sequential execution and re-plan waves before parallelizing.

## Model Selection

Use the least powerful model that can handle each role to conserve cost and increase speed.

**Mechanical implementation tasks** (isolated functions, clear specs, 1-2 files): use a fast, cheap model. Most implementation tasks are mechanical when the plan is well-specified.

**Integration and judgment tasks** (multi-file coordination, pattern matching, debugging): use a standard model.

**Architecture, design, and review tasks**: use the most capable available model.

**Task complexity signals:**
- Touches 1-2 files with a complete spec → cheap model
- Touches multiple files with integration concerns → standard model
- Requires design judgment or broad codebase understanding → most capable model

## Handling Implementer Status

Implementer subagents report one of four statuses. Handle each appropriately:

**DONE:** Proceed to spec compliance review.

**DONE_WITH_CONCERNS:** The implementer completed the work but flagged doubts. Read the concerns before proceeding. If the concerns are about correctness or scope, address them before review. If they're observations (e.g., "this file is getting large"), note them and proceed to review.

**NEEDS_CONTEXT:** The implementer needs information that wasn't provided. Provide the missing context and re-dispatch.

**BLOCKED:** The implementer cannot complete the task. Assess the blocker:
1. If it's a context problem, provide more context and re-dispatch with the same model
2. If the task requires more reasoning, re-dispatch with a more capable model
3. If the task is too large, break it into smaller pieces
4. If the plan itself is wrong, escalate to the human

**Never** ignore an escalation or force the same model to retry without changes. If the implementer said it's stuck, something needs to change.

## Final Adversarial Correctness Review

**Simplify pass (threshold-triggered).** If the cumulative diff has ≥10 substantive
(non-docs/format/lockfile) changed lines, run `/simplify` over the diff before
`/correctness-review`; if it applies fixes, re-run the affected task's test loop. This pass
edits an unmerged, pre-ship diff, so deletion is allowed here — unlike `/intent-review`'s
post-hoc `excess` verdict (below), which stays report-only because removing *shipped*
functionality is a Rule-4 human decision.

**Pre-gate — context-propagation audit (change-triggered).** If the cumulative diff touches the
workflow-engine inventory (`harness-manifest.json` → `workflow-engine`), run
`/context-propagation-audit` first; an audit FAIL blocks the review chain until delivery is proven
or the change is escalated.

After every task's spec + quality review passes, run **one** adversarial correctness review over
the entire implementation diff before handing off to `finishing-a-development-branch`. This pass
**is the `/correctness-review` skill — delegate to it; do not re-implement the pipeline here.**
Dispatch it with a **different model than the implementer** — running it with the model that wrote
the code defeats the ensemble diversity the pass depends on.

**Range to pass:** `BASE` = commit before task 1, `HEAD` = current commit after all tasks, plus the
list of touched files. `/correctness-review` then runs its own pipeline —
**FIND (6 parallel angles) → dedup → SCORE → THRESHOLD(75) → classify → fix-loop** — and enforces
the residual-work gate: every finding is fixed with a sha, escalated, or recorded as advisory
before handoff.

**Do not restate that pipeline here.** `skills/correctness-review/SKILL.md` is its single source of
truth, and `correctness-{reviewer,scorer}-prompt.md` are the dispatch templates. An earlier version
of this section paraphrased the stage detail and went stale within one change; naming the stages
and pointing at the spec is what keeps the two files from disagreeing.

**Why this stage exists.** The per-task spec and quality reviewers are anchored to the plan as
the oracle — spec review asks *"does it match the spec?"*, quality review asks *"is it clean?"*.
Neither asks *"even if the spec is right, does this code fail at runtime?"*. A bug that faithfully
implements a flawed spec passes both — the gap that lets real bugs survive to production and get
caught by external reviewers post-push. The correctness pass closes it.

**Relationship to `/code-review`:** they are siblings. `/correctness-review` is the always-on
in-flow gate and hunts runtime bugs only; the built-in `/code-review` also covers cleanup (reuse,
simplification, efficiency, conventions). On a high-risk lane you may run `/code-review` in
addition, before merge — they compound, and neither replaces the other. `/correctness-review` does
not invoke it.

## Final Intent Review

After `/correctness-review` passes, run **one** intent review over the entire diff before handing
off to `finishing-a-development-branch`. This pass **is the `/intent-review` skill — delegate to
it; do not re-implement the pipeline here.**

**Range to pass:** same as the correctness pass — `BASE` = commit before task 1, `HEAD` = current
commit, plus the touched-file list. The reviewer's oracle is the `### Intent` block of
`specs/<slug>/SUMMARY.md` (the original request, verbatim) plus design.md Success Criteria when it
exists; it is dispatched as a **fresh subagent, blind to PLAN.md** (different model than the
implementer). It classifies findings `gap` / `excess` / `drift` and routes each (fix-loop ·
escalate · report-only), then enforces a residual gate — every finding fixed with a sha or durably
recorded before handoff. See `skills/intent-review/SKILL.md`.

**Why this stage exists.** Spec review (oracle: PLAN) and correctness review (oracle: runtime,
blind to plan) can both pass while the result is still not what the user asked for — if intake or
design misread the intent, every gate passes consistently. The three oracles are mutually blind:
spec-review against the plan, correctness-review against runtime (blind to plan), intent-review
against the original request (blind to plan). This pass is the last check before the human merge gate.

## Review Receipt

Once correctness and intent have both passed (and the context-propagation audit, if it ran), write
`specs/<slug>/.review-receipt.json` from `templates/REVIEW-RECEIPT.template.json` before handing off
to `finishing-a-development-branch`. This is the machine-checkable proof that the reviews actually
ran against the code being shipped — `finishing-a-development-branch` Step 3 gates the push on it via
`scripts/check_review_receipt.py`. The receipt is gitignored (derived / machine-local).

Fill it as:

- `reviewed_head_sha` — `git rev-parse HEAD` (the exact commit the reviews saw).
- `reviews` — one entry per review actually run this session: `correctness`, `intent`, and
  `context-propagation-audit` if the pre-gate fired. Each records `reviewer` (model or tier),
  `result` (`pass` / `fail`), and the open-finding counts (`blocking_open`, `advisory_open`) left
  after the fix-loop.
- `created` — current ISO-8601 timestamp.

**Ship gate (conjunction).** Handoff to `finishing-a-development-branch` requires BOTH conditions,
not either alone:

1. `python scripts/verify_summary.py --check <slug>` passes **including SC coverage** — every
   Success Criterion in `specs/<slug>/PLAN.md` §3 has a passing `Criterion` row in the SUMMARY
   `### Verify` table (SC ↔ passing row). An SC with no passing Criterion row fails the check.
2. **AND** every receipt entry is `result: pass` with `blocking_open: 0`.

Both must hold. A green receipt with an uncovered SC does not ship, and full SC coverage with an
open blocking finding does not ship.

**Re-review after fix (invalidation rule).** ANY fix commit landed after the receipt is written
makes it stale — `reviewed_head_sha` no longer equals `HEAD`, and the finishing gate will refuse the
push. When a post-review fix commit lands, re-run the affected review(s) against the new HEAD and
re-write the receipt (new sha + refreshed results) before handoff. Never hand-edit the sha to match;
re-run the review that the fix invalidated.

## Reporting — Rule 1–3 Deviation Logging

Every implementer subagent MUST classify and log each auto-fix it applied during task
execution against `.claude/rules/auto-correct-scope.md` Rules 1–3. The subagent's return
payload MUST include the `deviations` field (see `./implementer-prompt.md` return contract).

Cross-references:

- `.claude/rules/auto-correct-scope.md` — definitions for Rule 1 (auto-fix bugs),
  Rule 2 (auto-add missing standards-driven functionality), Rule 3 (auto-fix blocking
  issues), and Rule 4 STOP cases that must never be auto-applied.
- `.claude/rules/orchestration.md` — subagent contract section (every returning
  subagent reports Commits, Files, Deviations, Blockers, Verify status).

**Destination.** The controller aggregates each task's `deviations` and appends them
to `specs/<slug>/SUMMARY.md` under a `### Deviations` block. One entry per auto-fix.

Entry shape (Markdown bullet):

```markdown
### Deviations

- Rule 2 — Added `AppException.BadRequest` for invalid trade_type. `app/services/trade_log_service.py`. Commit `abc1234`.
- Rule 3 — Added `httpx>=0.27` to requirements.txt. Needed by new broker client. Commit `def5678`.
```

Required fields per entry: rule number (1|2|3), short description, file path, commit
sha (when applicable). If no deviations were applied on a task, the subagent still
returns `deviations: []` and the controller adds no entry for that task.

If the same deviation re-appears across tasks, surface it to the user as a PLAN.md gap
per `auto-correct-scope.md` → Reporting.

## Prompt Templates

- `./implementer-prompt.md` - Dispatch implementer subagent
- `./spec-reviewer-prompt.md` - Dispatch spec compliance reviewer subagent (per task). When the
  task maps to one or more Success Criteria (SC) rows in `specs/<slug>/PLAN.md` §3, **quote those SC
  rows verbatim into the reviewer prompt** — the spec reviewer is an isolated context and cannot see
  the plan, so an SC it never receives is an SC it cannot verify. Have it confirm each quoted SC is
  satisfied by the code (and, where the task adds one, by a passing `Criterion` row in the SUMMARY
  `### Verify` table), not just that the task text was implemented.
- `./code-quality-reviewer-prompt.md` - Dispatch code quality reviewer subagent (per task)
- Final adversarial correctness pass - delegated to `/correctness-review` (see `skills/correctness-review/`); its `correctness-{reviewer,scorer}-prompt.md` live there, not here.
- Final intent review - delegated to `/intent-review` (see `skills/intent-review/`); its `intent-reviewer-prompt.md` lives there, not here.

## Parallel session

The plan can also be executed from a **separate session** — open one in the worktree and run this
same skill there. Everything above still applies: the Step-0 four-check gate, branch isolation,
`status: active`, and the full `/context-propagation-audit` → `/correctness-review` →
`/intent-review` → receipt chain. Running in another session never buys fewer gates.

What changes is only the granularity of control. In a separate session there is no orchestrator
watching each task, so execute in **batches with a checkpoint between them**: run a batch, report
what landed and what verified, and wait before starting the next. Per-task subagent dispatch is
optional there — the controller may implement tasks directly, provided each task's `Verify`
command still runs and passes before the task is marked complete.

**Stop and ask** — in either mode — when a blocker appears mid-batch (missing dependency, an
instruction you do not understand, a `Verify` that fails repeatedly), or when the plan has a gap
that prevents starting. Do not force through a blocker on a guess.

## Integration

**Required workflow skills:**
- **using-git-worktrees** - REQUIRED: Set up isolated workspace before starting
- **writing-plans** - Creates the plan this skill executes
- **superpowers:requesting-code-review** - Code review template for reviewer subagents (external)
- **finishing-a-development-branch** - Complete development after all tasks

**Subagents should use:**
- **superpowers:test-driven-development** - Subagents follow TDD for each task (external)
