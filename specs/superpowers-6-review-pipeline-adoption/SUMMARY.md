# superpowers-6-review-pipeline-adoption — Summary

Lane: high-risk
Confidence: high
Reason: The requested plan changes workflow-engine skills, reviewer prompts, agent permissions, plan schema, and evaluation contracts.
Flags: existing behavior, weak proof, multi-domain, high-blast file
Affects: subagent-driven-development, writing-plans, reviewer agent, correctness/intent review, skill evaluations
Input-type: harness improvement

### Intent

> "dich sang tieng viet"
>
> "hãy lưu file, sau đó lập kế hoạch implement cho tất cả những điều suggest ở trên"

Scope anchor: `docs/research/2026-07-29-superpowers-6-review-pipeline-adoption.vi.md`.

## What changed

Saved the corrected Vietnamese review and created a complete high-risk implementation plan for
the recommended Superpowers 6.0 review-pipeline adaptations. No runtime workflow behavior was
changed in this planning task.

### Rationale

The change affects the harness's execution and review engine, so a standalone PLAN without design,
research, risk boundaries, and measurable quality gates would be insufficient.

### Alternatives considered

- Edit the existing untracked translation in place — rejected to avoid overwriting user-owned work
  and because it repeats an unsupported benchmark claim.
- Copy upstream v6 wholesale — rejected because this repository has stronger lane routing, final
  oracles, hooks, and receipts that must be preserved.
- Plan only reviewer consolidation — rejected because file handoffs, unknown routing, PLAN context,
  and A/B proof are required for the consolidation to be safe.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Consolidated reviewer contract | `python3 scripts/check_task_review_contract.py` | 0 | One local reviewer, two verdicts | SC-1 |
| SDD artifact handoffs | `bash tests/scripts/sdd-artifact-handoffs.test.sh` | 0 | Brief and explicit BASE..HEAD package | SC-2 |
| Task-review routing | `bash tests/scripts/sdd-task-review-routing.test.sh` | 0 | Unknown, blocking severity, Minor routing | SC-3 |
| PLAN context contract | `python3 scripts/check_plan_contract.py --self-test` | 0 | New contract and legacy compatibility | SC-4 |
| Task reviewer permissions | `bash tests/scripts/task-reviewer-readonly.test.sh` | 0 | No mutation-capable declared tools | SC-5 |
| Final shared package boundary | `bash tests/scripts/final-review-package-contract.test.sh` | 0 | Mechanical diff only; final oracles remain blind | SC-6 |
| A/B quality gate | `python3 scripts/score_task_review_eval.py --compare evals/skills/task-review/results/baseline.json evals/skills/task-review/results/candidate-v2.json --quality-gate` | 0 | Candidate v1 retained as rejected; v2 accepted | SC-7 |
| A/B efficiency gate | `python3 scripts/score_task_review_eval.py --compare evals/skills/task-review/results/baseline.json evals/skills/task-review/results/candidate-v2.json --efficiency-gate` | 0 | Dispatch 14→7; median 24.84s→13.32s | SC-8 |
| Adoption aggregate | `python3 scripts/check_task_review_adoption.py` | 0 | Source contracts, docs, manifest, tests agree | SC-9 |

### Rollback

- Before commit: `git clean -f -- docs/research/2026-07-29-superpowers-6-review-pipeline-adoption.vi.md specs/superpowers-6-review-pipeline-adoption`
- After commit: revert the focused planning commit with `git revert <planning-commit-sha>`.

### Harness-Delta

- implemented — consolidated task review, context-plan contract, file handoffs, durable routing,
  corpus A/B, and deterministic adoption checks.
