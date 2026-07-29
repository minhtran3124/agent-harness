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

### Context-Propagation Audit

Diff: `3d1ba4d..HEAD` (50 workflow-engine files). Run 2026-07-29 in the main session after a
dispatched reviewer returned no report twice — a silent return is not a PASS
(`docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`), so the audit was redone
here with every load-bearing row corroborated against file content.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `rules/auto-correct-scope.md` (paths `specs/**`) | `implementer-prompt.md` | implementer subagent | explicit Read | `implementer-prompt.md:104` "FIRST: Read … now"; probe `2026-07-29-prompt-refactor.md` delivered |
| `rules/auto-correct-scope.md` | `correctness-review/prompts/shared.md` | FIND reviewer (plan-blind) | explicit Read | `shared.md:102` "the explicit Read is required" |
| `rules/plan-format.md` (paths `specs/**/PLAN.md`) | `plan-document-reviewer-prompt.md` | plan reviewer subagent | paths-triggered | strict probe below — reviewer is handed a `PLAN.md` path and reads it |
| `rules/plan-format.md` | `writing-plans/SKILL.md` | main | explicit Read | `tests/scripts/writing-plans-contract.test.sh` asserts the Read string |
| PLAN §3 SC rows | `spec-reviewer-prompt.md` | spec reviewer subagent | pasted | `spec-reviewer-prompt.md:21-24` "Quote VERBATIM … CANNOT see PLAN.md" |
| SUMMARY `### Intent` + design SC | `intent-reviewer-prompt.md` | intent reviewer (plan-blind) | pasted | `intent-reviewer-prompt.md:39-44` |
| `prompts/shared.md` + `angles/*.md` | six FIND reviewers | six isolated reviewers | pasted (deterministic composition) | `render_skill_prompt.py --check-all` exit 0 (SC-7) |
| `rules/research-depth.md` (no `paths:` → auto-loaded) | `xia2`, `feature-intake` | main | always-loaded + explicit Read | `xia2/SKILL.md:17` |
| 8 new `references/*.md` | own `SKILL.md` | main session (has tools) | explicit Read / on-demand | each cited at a named line in its SKILL.md |
| `requesting-code-review/code-reviewer.md` (absent) | `code-quality-reviewer-prompt.md` | code-quality reviewer | n/a — guarded | prompt states the external plugin is not present and routes to the in-repo `reviewer` agent |

**Verdict: PASS.** No load-bearing instruction is `assumed`, no child delivery is inferred from
main-session behavior, and no unanchored inline policy subset was found.

One row was initially suspected to be the #141 escape shape and was cleared by experiment rather
than by argument. `plan-document-reviewer-prompt.md` hands an isolated reviewer a `PLAN.md` path
and three rubric cells reading "per `.claude/rules/plan-format.md`", with **no** Read instruction —
the shape that caused #141. A strict two-arm probe in a disposable sandbox worktree settled it:

- **read arm** — subagent reads `specs/skill-prompt-refactor/PLAN.md`, then correctly quotes the
  **non-guessable** cut-off date `2026-07-16` from inside `rules/plan-format.md`. Delivered.
- **no-read control** — identical question, no file read → `NOT IN CONTEXT`. So it was neither
  prior knowledge nor a guess from the filename.

**This corrects a claim in the harness's own oracle docs.** `evals/context-boundaries/probes/implementer-subagent.md`
states a child context gets "no path-scoped rule auto-loads here; a rule arrives ONLY if the
dispatch prompt explicitly instructs a Read." That is too strong. The accurate rule: a path-scoped
rule does not auto-load in a child context **unless the child reads a file matching the glob** —
which the plan reviewer does. The 2026-07-22 probes only ever tested the no-matching-file case, so
they could not distinguish the two. The #141 lesson is unchanged: that escape had the worker
reading no `specs/**` file at all.

Residual fragility (recorded, not blocking): this row's delivery depends on the reviewer being
passed a **path** it reads. Passing the chunk as inline text instead would silently drop the rule.

### Rollback

- `git revert <planning-commit-sha>`

### Harness-Delta

- backlog — replace prose-encoded workflow state and prompt-copy parity with structured,
  testable authorities during implementation.
