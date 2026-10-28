# Orchestration Rule

The main thread coordinates. Each subagent costs a fresh context. The subagent re-establishes
context and re-explores, and then you re-read its report. Delegate where isolation or parallelism
is the point:

- one implementer per `PLAN.md` task (`wave-parallelism.md`)
- each review pass in its own isolated reviewer (independence is the design, not extra
  verification)
- wide multi-file investigations

Do everything else in the main loop: a few reads, a few edits, a targeted search, or a check of
your own output. For a modest job, prefer one subagent to several. Brief it fully the first time.
Do not redo its work after it reports.

Applies when: a task spans >3 steps or a `specs/<slug>/PLAN.md` is active.

Related: `plan-format.md`, `wave-parallelism.md`, `auto-correct-scope.md`, `guidelines.md`.

## Intake fields (orchestrator writes these)

At intake, before it dispatches any task, the orchestrator runs `feature-intake`. It writes the
result to `specs/<slug>/SUMMARY.md` (shape: `templates/SUMMARY.template.md`):

- **Lane** — `tiny | normal | high-risk` (drives ceremony / how much proof).
- **Confidence** — `high | medium | low` (drives interruption / whether to ask a human).

The classification algorithm that assigns these values lives in `skills/feature-intake/SKILL.md`
Step 3–4. That is the canonical source. This section only names the fields and their consumers.

These two fields are load-bearing:

- The risk-corroboration check in `hooks/commit-gate.sh` (`check_risk`, in the default
  `standard` checks) reads `Lane:` and corroborates it against the staged diff.
- The trust-metrics ledger reads both fields.

The orchestrator MUST write a `Lane:` line. The check gives these results:

- A declared lane below `high-risk` is **blocked** when the diff trips a **block-mode** hard-gate
  signal.
- A warn-mode gate (`workflow-engine`, `weakening-validation`) prints a note and does not block.
- A *missing* lane only **warns** (fail-open), unless `RISK_CORROBORATION_STRICT=1` is set.

The per-gate mode is the `slug=mode` table in `hooks/lib/gate-modes.default.sh`. The hook reads policy
from the git index or that file only, never from a `.claude/` copy.

## Subagent contract

Every subagent returning to main thread MUST include in its summary:

- **Commits made** — sha + subject line (execution mode only)
- **Files touched** — list of paths
- **Lane** — the intake lane this task ran under (`tiny | normal | high-risk`)
- **Deviations** — Rule 1–3 auto-fixes per `auto-correct-scope.md`, labeled by rule
- **Blockers** — anything requiring main thread decision or user input
- **Verify status** — pass/fail of the task's `Verify` command (with command output excerpt on fail)
- **Harness-Delta** — friction this task revealed about the workflow itself: `fix-direct`, `backlog` (→ `compound`), or `none`

Include only what the main thread needs to act without re-reading the subagent's work product.
Do not include raw file dumps.

Under `subagent-driven-development`, the implementer returns the full contract inline, because the
runtime refuses subagent report-file writes. The controller persists the report to
`.harness-state/sdd/` for the task reviewer:

- On a `DONE` or `DONE_WITH_CONCERNS` return, the controller writes
  `.harness-state/sdd/report-<task>.md` verbatim under a one-line "transcribed by controller"
  header. It does this before the task review.
- A fix dispatch also returns that structured report. The controller appends it verbatim under a
  `## Fix round <n>` heading. It does not replace the first report.
- A `BLOCKED` or `NEEDS_CONTEXT` return writes no file and removes any existing
  `report-<task>.md`, so no reviewer sees a stale report.
- After such a removal, the next file-writing return starts a fresh `report-<task>.md`. It is
  written as a first report: the controller header, no `Fix round` heading, and round
  numbering restarts.
- The controller treats a return with no recognisable status as `NEEDS_CONTEXT`.

That full structured report is what the main thread needs, so it is not a raw file dump.

## Evidence in SUMMARY.md (evidence over assertion)

A claim of "done" is only valid with a re-runnable artifact. The subagent records, in `specs/<slug>/SUMMARY.md` (shape: `templates/SUMMARY.template.md`):

- **`### Verify`** — a table row per check actually RUN: `Check | Command | Exit | Notes`. Never
  list a command that was not run. `hooks/commit-gate.sh` can require this block for `app/`
  changes. It does so when `REQUIRE_VERIFY=1` is set and its app gates run (`REQUIRE_APP_GATES=1`).
- **`### Rollback`** — the exact undo command(s). This section is required for any high-risk /
  Rule-4 action (`rules/auto-correct-scope.md`). For reversible work, `git revert <sha>` suffices.

Behavior-to-proof status lives in the SUMMARY `### Verify` table: one row per check actually run, re-runnable command + exit code.

## Artifact policy (record always-on; plan-ahead by signal)

Two kinds of artifact, sized differently:

- **The record** — every lane, tiny included, writes `SUMMARY.md`. It is the always-on audit
  trail. Its `Rationale` + `Alternatives` make an autonomous decision reconstructable without
  re-reading the diff. "No human" never means "no record."
- **Plan-ahead scaffolding** — a design ADR (`docs/adr/`) / `research-brief.md` / `PLAN.md` exist to reduce
  *uncertainty*. Thus a **signal** triggers them, not the lane alone:
  - `PLAN.md` at >3 steps or >2 files (`rules/plan-format.md`)
  - `research-brief.md` for unfamiliar code or high-risk
  - a design ADR only on a real design fork (≥2 viable approaches) or high-risk

For autonomous work, the substitute for the human gate is **verification, not more documents**.
That means a re-runnable `### Verify` row + independent task review with separate spec and quality
verdicts. Over-documenting reversible work manufactures unread artifacts. They are harder to audit
than the diff, and they erode the record's value.

`FULL_ARTIFACTS=1` (opt-in) forces the complete artifact set regardless of lane — for audit-heavy changes or while calibrating trust. Default is signal-scaled.

## Escalation decision (when to involve a human)

Run this decision at intake and continuously during execution. **Ceremony scales with risk. The
human gate scales with ambiguity.** Never ask a human to classify risk. Ask a human only to confirm
intent or to authorize a dangerous boundary.

ESCALATE — write a block to `specs/<slug>/ESCALATIONS.md` (shape: `templates/ESCALATIONS.template.md`)
and stop — when any of these hold:

- a **hard gate** is hit, and a human has not yet narrowed it. Hard gates include: auth ·
  authorization · data-loss/migration · audit/security · external provider · public contract ·
  weakening validation · high-blast file.
- **confidence is `low`** (any lane), or `medium` on a high-risk task.
- the **direction is ambiguous** (>1 materially different interpretation).
- an **in-flight trigger** fires (see "In-flight escalation checks" below).
- the change would **redefine the system** (architecture direction, validation requirements,
  source-of-truth hierarchy, risk-classification rules, or the workflow itself).

Otherwise **PROCEED autonomously** in the lane. For high-confidence **normal**-lane work, post the
`PLAN.md` and a short notice (**notify-and-proceed**) instead of blocking on approval. The human
may interrupt but is not a gate. Per-task agent reviews stay always-on regardless of lane.

`ESCALATIONS.md` is **deny-on-no-response**: with no recorded decision, the work stays blocked.
`hooks/commit-gate.sh` mechanizes this (`check_escalations`, in the `standard` and `strict`
profiles). It denies a commit touching `specs/<slug>/` while that slug's `ESCALATIONS.md` has
`decision: pending`. A commit that also records the decision is not denied.

## In-flight escalation checks (during waves)

Re-check these continuously while you execute each wave. Any one of them escalates mid-flight:

- **Repeated `Verify` failure** — the same check fails ≥2 times after a fix attempt.
- **Blast radius beyond plan** — a subagent touched files outside its task's declared Files set.
  The task reviewer's spec verdict compares the task's diff to its Files list. At each wave
  commit, `hooks/commit-gate.sh` `check_plan_scope` also warns on paths outside the active plan's
  Files set. That set is a union across tasks, so per-task attribution is the reviewer's job.
- **Hard gate discovered mid-implementation** — intake did not see it. Re-run the corroboration
  check on the wave diff.
- **Recurring deviation** — the same Rule-1–3 deviation repeats across tasks (a PLAN.md gap).
- **Subagent BLOCKED with "the plan itself is wrong"** — this is the only blocker class that
  escalates. Other blockers self-recover (more context → re-dispatch, bigger model, split the
  task).
