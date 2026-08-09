---
name: subagent-driven-development
description: Use to execute an approved multi-task PLAN.md: waves of isolated implementer subagents with per-task review, separate-session resume, and final delivery/correctness/intent gates before shipping.
---

# Subagent-Driven Development

Execute a valid plan with isolated implementation and review contexts. A task may advance only
after its Verify command and both per-task reviews are green.

## Resume first

For `resume <slug>`, run the resume authority before editing — source tree first, deployed runtime
second:

```
if [ -f runtime/resume_decision.py ]; then python3 runtime/resume_decision.py --slug <slug>; else python3 .claude/runtime/resume_decision.py --slug <slug>; fi
```

The fallback fires ONLY when the source file is absent — never on a non-zero exit — so a
fail-closed exit 3 is not silently re-answered from the gitignored, possibly-stale deployed copy.
Do not discard stderr. A default consumer install owns `.claude/runtime/resume_decision.py`, not a
root `runtime/`; its sibling `run_state.py` resolves because Python puts the script's own directory
on `sys.path`. Treat ANY non-zero exit as `stop`, and require `schema_version == 1` before acting on
`action`. Branch only on the structured `action`/`reason_code`: `execute-plan`, `resume-repair`,
`resume-review-chain`, `wait`, `stop`, or `rebuild`.

On `execute-plan`, first re-run every `cursor.checks_to_rerun` item (each claimed-complete task's
exact Verify) and dispatch NO pending task until those claims verify; a failed check routes to the
repair path. Apply `required_transition` ONLY after the session confirms the external condition it
names. Do not reconstruct the FSM from prose or initialize a missing historical run during
execution. Read `references/resume.md` only when the returned action requires a manual transition
or repair.

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
  paths to `task-reviewer`, which pins `claude-opus-5`. One reviewer returns both
  `spec_verdict` and `quality_verdict` using `task-reviewer-prompt.md`.
- `cannot_verify` gets one focused context or test-runner retry. If still unknown, escalate; never
  treat it as a pass. Fix all Critical/Important findings in one dispatch, then re-review both
  verdicts. Record Minor findings in SUMMARY and the progress ledger; provide their roll-up to the
  final review chain.
- `NEEDS_CONTEXT` receives missing context; `BLOCKED` is re-dispatched with changed context/model,
  split, or escalated when the plan itself is wrong. Repeated verification failure or blast-radius
  escape is an escalation signal. Keep controller narration to one short status line between calls.

After all tasks pass, transition to `verifying` when tracked and read
`references/review-chain.md` for the final sequence.

## Receipt and ship gate

Write `.review-receipt.json` at the reviewed HEAD. Handoff requires both a passing
`python3 scripts/verify_summary.py --check <slug>` (including Success Criteria coverage) and a
passing receipt with zero blocking findings. Any post-review code commit invalidates the receipt:
re-run the affected review; never hand-edit its SHA.
