# skill-prompt-refactor — Summary

Lane: high-risk
Confidence: high
Reason: the requested plan covers every `skills/*/SKILL.md` and companion prompt, which is the workflow-engine hard-gate surface; the objective is clear and implementation remains gated on plan approval.
Flags: existing behavior, weak proof, multi-domain, workflow-engine
Affects: skill activation, routing, planning, execution, review, compounding, and shipping contracts
Input-type: harness improvement

### Intent

> tôi muốn tạo kế hoạch cho việc review lại prompt của các skill. mục tiêu là refactor/simplify lai prompt, nhưng vẫn đảm bảo chất lượng, workflow hoạt động tốt. tìm hiểu và lên kế hoachj kỹ càng cho từng mục.

## What changed

Created a repository-wide design, research brief, and implementation plan for simplifying all
registered skill prompts and companion dispatch prompts while preserving behavior and workflow
quality through baseline measurement, focused evals, contract tests, and staged rollout.

### Rationale

The previous surface reduction removed obsolete skills and obvious boilerplate, but the remaining
complexity is concentrated in branch-heavy runtime prose and duplicated policy. The plan therefore
moves deterministic mechanics to tested code, uses progressive disclosure for rare branches, and
requires quality parity before accepting token reduction.

### Alternatives considered

- Line-count-only trimming — rejected because unique gates can hide inside explanatory sections.
- Merge review skills — rejected because their mutually blind oracles cover different defect classes.
- Rewrite all prompts in one wave — rejected because regressions would be difficult to localize.
- Leave behavior unmeasured and rely on the full shell suite — rejected because most prompt
  behavior is not exercised by deterministic CI today.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Plan artifact structure | `python3 skills/visual-planner/render_plan.py skill-prompt-refactor --summarize` | 0 | Run after PLAN.md is written | SC-12 |
| Documentation paths | `bash scripts/lint-doc-truth.sh` | 0 | Pending final plan render | SC-12 |
| Deployed harness smoke | `bash scripts/deploy-harness.sh` | 0 | Source sync confirmed; deployed detector and renderer executed | SC-4 |
| Resolver mismatch regression | `python3 -m pytest scripts/test_resolve_finish_context.py -q` | 0 | Branch `refactor/skill-prompt-surface` resolves `skill-prompt-refactor` by unique token evidence | SC-4 |
| Inventory baseline validity | `python3 scripts/audit_skill_prompts.py --validate-inventory evals/skills/prompt-refactor/results/baseline.json` | 0 | Pinned pre-refactor inventory is structurally valid | SC-1 |
| Behavioral corpus gate | `python3 scripts/score_skill_eval.py --suite behavior --candidate` | 0 | All 36 golden, boundary, and handoff cases have recorded passing first-run candidate observations | SC-3 |
| Activation non-regression | `python3 scripts/score_skill_eval.py --compare evals/skills/prompt-refactor/results/baseline.json evals/skills/prompt-refactor/results/candidate.json --suite activation` | 0 | 162/192 candidate vs 152/192 baseline; 11 improvements, 0 new false positives; prints 1 unmeasured case | SC-2 |
| Review-chain corpus gate | `python3 scripts/score_skill_eval.py --suite review-chain --candidate` | 0 | Schema gate; substantive A/B in `evals/skills/review-chain/results/2026-07-29-prompt-refactor-ab.md` (4/5 both arms, no recall regression) | SC-6 |
| Baseline/candidate comparison | `python3 scripts/score_skill_eval.py --compare evals/skills/prompt-refactor/results/baseline.json evals/skills/prompt-refactor/results/candidate.json` | 0 | Full canonical corpus present in both arms; no regression, no new false positive | SC-9 |
| Resume decision contract | `python3 -m pytest runtime/test_run_state.py runtime/test_resume_decision.py -q` | 0 | State routing and transitions are executable, not prompt-parsed | SC-5 |
| Prompt composition contract | `python3 scripts/render_skill_prompt.py --check-all` | 0 | Required policy delivery and correctness config validate | SC-7 |
| Context delivery regression | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | Both known isolated-context escapes remain blocked | SC-8 |
| Prompt surface reduction | `python3 scripts/audit_skill_prompts.py --compare evals/skills/prompt-refactor/results/baseline.json evals/skills/prompt-refactor/results/candidate-inventory.json` | 0 | 67.9% word reduction | SC-10 |
| Registry consistency | `python3 scripts/check_manifest.py` | 0 | Manifest, inventory, settings, and gate vocabulary agree | SC-11 |

### Rollback

- `git revert <planning-commit-sha>`

### Harness-Delta

- backlog — replace prose-encoded workflow state and prompt-copy parity with structured,
  testable authorities during implementation.
