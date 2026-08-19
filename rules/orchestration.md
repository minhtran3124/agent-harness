# Orchestration Rule

Main thread = thin coordinator. Heavy work delegated to fresh-context agents.

Applies when: task spans >3 steps, codebase research needed, or a `specs/<slug>/PLAN.md` is active.

Related: `plan-format.md`, `wave-parallelism.md`, `auto-correct-scope.md`, `guidelines.md`.

## Intake fields (orchestrator writes these)

At intake — before dispatching any task — the orchestrator runs `feature-intake` and writes the result to `specs/<slug>/SUMMARY.md` (shape: `templates/SUMMARY.template.md`):

- **Lane** — `tiny | normal | high-risk` (drives ceremony / how much proof).
- **Confidence** — `high | medium | low` (drives interruption / whether a human is asked).

The classification algorithm that assigns these values lives in `skills/feature-intake/SKILL.md`
Step 3–4 — that is the canonical source; this section only names the fields and their consumers.

These two fields are load-bearing: `hooks/risk-corroboration.sh` reads `Lane:` to corroborate it against the staged diff, and the trust-metrics ledger reads both. The orchestrator MUST write a `Lane:` line: a declared lane below `high-risk` is **blocked** when the diff trips a **block-mode** hard-gate signal (per-gate mode lives in `harness-manifest.json`; warn-mode gates — `workflow-engine`, `weakening-validation` — print a note and allow), and a *missing* lane only **warns** (fail-open) unless `RISK_CORROBORATION_STRICT=1` is set.

## Subagent contract

Every subagent returning to main thread MUST include in its summary:

- **Commits made** — sha + subject line (execution mode only)
- **Files touched** — list of paths
- **Lane** — the intake lane this task ran under (`tiny | normal | high-risk`)
- **Deviations** — Rule 1–3 auto-fixes per `auto-correct-scope.md`, labeled by rule
- **Blockers** — anything requiring main thread decision or user input
- **Verify status** — pass/fail of task's `<verify>` command (with command output excerpt on fail)
- **Harness-Delta** — friction this task revealed about the workflow itself: `fix-direct`, `backlog` (→ `compound`), or `none`

Target length: 150–300 words. No raw file dumps. Main thread must be able to act on the summary alone without re-reading the subagent's work product.

## Evidence in SUMMARY.md (evidence over assertion)

A claim of "done" is only valid with a re-runnable artifact. The subagent records, in `specs/<slug>/SUMMARY.md` (shape: `templates/SUMMARY.template.md`):

- **`### Verify`** — a table row per check actually RUN: `Check | Command | Exit | Notes`. Never list a command that was not run. `commit-quality-gate.sh` can require this block for `app/` changes when `REQUIRE_VERIFY=1`.
- **`### Rollback`** — the exact undo command(s); required for any high-risk / Rule-4 action (`rules/auto-correct-scope.md`). For reversible work, `git revert <sha>` suffices.

Behavior-to-proof status lives in the SUMMARY `### Verify` table: one row per check actually run, re-runnable command + exit code.

## Artifact policy (record always-on; plan-ahead by signal)

Two kinds of artifact, sized differently:

- **The record** — `SUMMARY.md` is written for **every** lane, tiny included. It is the always-on audit trail; its `Rationale` + `Alternatives` make an autonomous decision reconstructable without re-reading the diff. "No human" never means "no record."
- **Plan-ahead scaffolding** — `design.md` / `research-brief.md` / `PLAN.md` exist to reduce *uncertainty*, so they are triggered by **signal**, not by lane alone: `PLAN.md` at >3 steps or >2 files (`rules/plan-format.md`); `research-brief.md` for unfamiliar code or high-risk; `design.md` only on a real design fork (≥2 viable approaches) or high-risk.

For autonomous work the substitute for the human gate is **verification, not more documents**: a re-runnable `### Verify` row + independent task review with separate spec and quality verdicts. Over-documenting reversible work manufactures unread artifacts that are harder to audit than the diff and erode the record's value.

`FULL_ARTIFACTS=1` (opt-in) forces the complete artifact set regardless of lane — for audit-heavy changes or while calibrating trust. Default is signal-scaled.

## Escalation decision (when to involve a human)

Run at intake and continuously during execution. **Ceremony scales with risk; the human gate scales with ambiguity** — never ask a human to classify risk, only to confirm intent or authorize a dangerous boundary.

ESCALATE — write a block to `specs/<slug>/ESCALATIONS.md` (shape: `templates/ESCALATIONS.template.md`)
and stop — when any of these hold:

- a **hard gate** is hit and not yet narrowed by a human (auth · authorization · data-loss/migration · audit/security · external provider · public contract · weakening validation · high-blast file);
- **confidence is `low`** (any lane), or `medium` on a high-risk task;
- the **direction is ambiguous** (>1 materially different interpretation);
- an **in-flight trigger** fires (see "In-flight escalation checks" below);
- the change would **redefine the system** (architecture direction, validation requirements, source-of-truth hierarchy, risk-classification rules, or the workflow itself).

Otherwise **PROCEED autonomously** in the lane. For high-confidence **normal**-lane work, post
the `PLAN.md` and a short notice (**notify-and-proceed**) instead of blocking on approval — the
human may interrupt but is not a gate. Per-task agent reviews stay always-on regardless of lane.

`ESCALATIONS.md` is **deny-on-no-response**: with no recorded decision the work stays blocked. Mechanized by `hooks/commit-quality-gate.sh` (Check 1.5): a commit touching `specs/<slug>/` is denied while that slug's `ESCALATIONS.md` has `decision: pending`; recording the decision in the same commit unblocks.

## In-flight escalation checks (during waves)

Re-check continuously while executing each wave; any of these escalates mid-flight:

- **Repeated `<verify>` failure** — the same check fails ≥2 times after a fix attempt.
- **Blast radius beyond plan** — a subagent touched files outside its task's declared Files set
  (corroborated by `hooks/blast-radius-check.sh`).
- **Hard gate discovered mid-implementation** — not seen at intake; re-run the corroboration
  check on the wave diff.
- **Recurring deviation** — the same Rule-1–3 deviation repeats across tasks (a PLAN.md gap).
- **Subagent BLOCKED with "the plan itself is wrong"** — the only blocker class that escalates;
  others self-recover (more context → re-dispatch, bigger model, split the task).
