---
name: subagent-driven-development
description: Use to execute an approved multi-task PLAN.md in waves, including a separate-session resume. Runs isolated implementers, spec then quality review, final delivery/correctness/intent gates, and a review receipt before shipping.
---

# Subagent-Driven Development

Execute a valid plan with isolated implementation and review contexts. A task may advance only
after its Verify command and both per-task reviews are green.

## Resume first

For `resume <slug>`, run `python3 runtime/resume_decision.py --slug <slug>` before editing.
Follow its action exactly: `execute-plan`, `resume-repair`, `resume-review-chain`, `wait`, `stop`,
or `rebuild`. Do not reconstruct the FSM from prose or initialize a missing historical run during
execution. Read `references/resume.md` only when its returned action requires a manual transition
or repair.

## Preflight

Before the first task, read `.claude/rules/plan-format.md`,
`.claude/rules/wave-parallelism.md`, and `.claude/rules/auto-correct-scope.md`. Stop unless:

1. Every parsed task has Files, Action, Verify, and Done.
2. Same-wave task file sets do not overlap and dependencies are ordered across waves.
3. Every Verify is one automated, exit-code-checkable command.
4. The plan meets the repository's plan threshold.

Ensure branch isolation, set the plan `status: active`, and transition the durable run to
`implementing` when it exists. A missing durable run remains honestly untracked.

## Execute waves

- Dispatch one fresh implementer per independent same-wave task; dispatch all parallel tasks in
  one message. Give the child the complete task text and required SC rows, never parent history.
- The implementer must read `auto-correct-scope.md`, run the task Verify, return files, commits,
  deviations, blockers, and evidence.
- Review in this order: spec compliance, then code quality. Fix with the same implementer and
  repeat the affected review. Do not advance with an open issue.
- `NEEDS_CONTEXT` receives missing context; `BLOCKED` is re-dispatched with changed context/model,
  split, or escalated when the plan itself is wrong. Repeated verification failure or blast-radius
  escape is an escalation signal.

After all tasks pass, transition to `verifying` when tracked and read
`references/review-chain.md` for the final sequence.

## Receipt and ship gate

Write `.review-receipt.json` at the reviewed HEAD. Handoff requires both a passing
`python3 scripts/verify_summary.py --check <slug>` (including Success Criteria coverage) and a
passing receipt with zero blocking findings. Any post-review code commit invalidates the receipt:
re-run the affected review; never hand-edit its SHA.
