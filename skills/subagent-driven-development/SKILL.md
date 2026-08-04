---
name: subagent-driven-development
description: Use to execute an approved multi-task PLAN.md in waves, including a separate-session resume. Runs isolated implementers, file handoffs, one read-only task reviewer with separate spec/quality verdicts, final delivery/correctness/intent gates, and a review receipt before shipping.
---

# Subagent-Driven Development

Execute a valid plan with isolated implementation and review contexts. A task may advance only
after its Verify command and both per-task reviews are green.

## Resume first

For `resume <slug>`, run `python3 runtime/resume_decision.py --slug <slug>` before editing.
Follow its action exactly: `execute-plan`, `resume-repair`, `resume-review-chain`, `wait`, `stop`,
or `rebuild`. Do not reconstruct the FSM from prose or initialize a missing historical run during
execution. Read `references/resume.md` before acting on `resume-repair`, `resume-review-chain`, or
`rebuild` — for `resume-review-chain` it holds the required simplify-evidence re-check that decides
whether `references/simplify-stage.md` must re-run. `wait` and `stop` are self-sufficient from the
returned reason; only `execute-plan` enters the preflight and wave loop below.

## Preflight

Before the first task, read `.claude/rules/plan-format.md`,
`.claude/rules/wave-parallelism.md`, and `.claude/rules/auto-correct-scope.md`. Stop unless:

1. Every parsed task has Files, Action, Verify, and Done. New contract plans additionally pass
   `python3 scripts/check_plan_contract.py <PLAN.md>`.
2. Same-wave task file sets do not overlap and dependencies are ordered across waves.
3. Every Verify is one automated, exit-code-checkable command.
4. The plan meets the repository's plan threshold.

Ensure branch isolation, set the plan `status: active`, and transition the durable run to
`implementing` when it exists. A missing durable run remains honestly untracked.

## Execute waves

- Before dispatch, generate a deterministic brief using
  `skills/subagent-driven-development/scripts/task_brief.py`; pass its path to the implementer.
  The implementer writes its detailed report to a path in `.harness-state/sdd/` and returns only a
  short status, commits, and report path. Do not paste task history or report contents.
- Generate one explicit `BASE..HEAD` package with `review_package.py`; pass brief/report/package
  paths to `task-reviewer` with an explicit standard-or-better model. One reviewer returns both
  `spec_verdict` and `quality_verdict` using `task-reviewer-prompt.md`.
- `cannot_verify` gets one focused context or test-runner retry. If still unknown, escalate; never
  treat it as a pass. Fix all Critical/Important findings in one dispatch, then re-review both
  verdicts. Record Minor findings in SUMMARY and the progress ledger; provide their roll-up to the
  final review chain.
- `NEEDS_CONTEXT` receives missing context; `BLOCKED` is re-dispatched with changed context/model,
  split, or escalated when the plan itself is wrong. Repeated verification failure or blast-radius
  escape is an escalation signal. Keep controller narration to one short status line between calls.

After all tasks pass, transition to `verifying` when tracked. Read
`references/simplify-stage.md` first — it resolves whether Claude Code's bundled `/simplify`
cleanup stage is required and records its outcome, committing any accepted mutation before any
final evidence exists — then read `references/review-chain.md` for the remaining final sequence.

## Receipt and ship gate

Write `.review-receipt.json` at the reviewed HEAD. Handoff requires both a passing
`python3 scripts/verify_summary.py --check <slug>` (including Success Criteria coverage) and a
passing receipt with zero blocking findings. Any post-review code commit invalidates the receipt:
re-run the affected review; never hand-edit its SHA.
