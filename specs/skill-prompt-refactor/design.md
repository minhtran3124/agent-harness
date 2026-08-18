# Design — Review and refactor the skill prompt surface

> Slug: `skill-prompt-refactor` · Date: 2026-07-28 · Lane: high-risk
> Scope: all 12 registered skills, their dispatch/reviewer/scorer prompts, and the
> cross-skill contracts that make the workflow safe.

## 1. Problem and baseline

The current live prompt surface contains:

| Surface | Files | Lines | Words |
|---|---:|---:|---:|
| `skills/*/SKILL.md` | 12 | 2,612 | 23,268 |
| Companion dispatch prompts | 12 | 1,420 | 10,766 |
| **Total** | **24** | **4,032** | **34,034** |

The distribution is uneven. `subagent-driven-development/SKILL.md` is 533 lines /
5,260 words, above the Agent Skills progressive-disclosure recommendation and more than
twice the next largest skill. Its resume branch grew through a sequence of narrow fixes:
15 of the 20 most recent skill commits touch this file. The behavior is valuable, but the
state machine is now encoded mainly as prose and tested by searching for exact phrases.

The repository already completed `specs/slim-skill-surface` on 2026-07-23. That work removed
three obsolete skills and obvious boilerplate. This design is the next layer: simplify the
remaining **runtime instruction paths** without deleting the gates and evidence that justified
them.

## 2. Success definition

The refactor succeeds only when both sides are true:

1. **Quality is non-regressing**
   - every hard gate, stop condition, output schema, handoff, receipt rule, and context-delivery
     requirement has an authoritative source and a re-runnable proof;
   - trigger precision/recall and behavioral task success do not regress on the agreed corpus;
   - review-chain recall and false-positive counts are no worse than baseline;
   - all deterministic and integration tests stay green.
2. **Runtime context is materially smaller and clearer**
   - instructions loaded on every invocation contain only the core decision path;
   - rare branches load focused references on demand;
   - deterministic state transitions, parsing, indexing, and path resolution move to scripts;
   - benchmarked loaded words/tokens fall by at least 25% overall and 50% on the two heaviest
     paths (`subagent-driven-development` and correctness FIND dispatch).

Line count is a diagnostic, not the acceptance oracle. A shorter prompt that loses a gate fails.

## 3. Refactor model

Every current paragraph is classified before editing:

| Class | Destination | Rule |
|---|---|---|
| Core instruction | `SKILL.md` | Needed on nearly every invocation to choose or execute the next action |
| Conditional procedure | `references/*.md` | Read only when the named branch occurs; the parent states the exact read trigger |
| Deterministic operation | `scripts/` or `runtime/` | State folding, parsing, collision handling, path resolution, or validation that can return structured output |
| Dispatch contract | focused prompt fragment / prompt builder | The isolated child receives a complete composed prompt; it never relies on the parent context |
| Historical rationale / benchmark narrative | `README.md`, `docs/research/`, or result file | Preserved for maintainers, absent from the runtime path |
| Duplicate policy | delete, point to authority | No independent copy unless isolation requires it; required copies get a parity test or are composed from the authority |

The intended shape is:

```text
description (activation)
  → compact SKILL.md (common path + branch conditions)
      → reference read only for the selected rare branch
      → script for deterministic decisions
      → fully composed prompt for each isolated subagent
```

## 4. Quality measurement

### 4.1 Four eval layers

1. **Activation eval** — per skill, realistic should-trigger and near-miss should-not-trigger
   queries; score the frontmatter description independently of the body.
2. **Behavior eval** — golden path, boundary, stop/escalation, and handoff cases per skill.
   Record first-run result, model, client version, commit SHA, token usage, tool calls, and
   latency. Do not re-run until green.
3. **Workflow-contract tests** — deterministic checks for source-of-truth parity, output schemas,
   state coverage, context delivery, review receipt, and cross-skill handoffs.
4. **End-to-end canaries** — one tiny, one normal, one high-risk, one resume, and one
   workflow-engine change through the full applicable chain.

### 4.2 Comparison rules

- Baseline and candidate use the same fixtures, model snapshot, reasoning setting, client
  version, clean worktree, and dispatch context.
- Quality gates are evaluated before efficiency. A candidate with fewer tokens but a new miss,
  false positive, unsafe action, or skipped handoff is rejected.
- Report median and p90 loaded tokens/words, model output tokens, tool calls, and elapsed time.
- Keep a holdout set of near-miss activation queries and at least one unseen behavioral case per
  skill to avoid rewriting prompts around the training fixtures.
- Three stochastic runs are used for activation and high-variance behavioral cases; deterministic
  tests run once per commit.

## 5. Per-skill refactor decisions

| Skill | Keep in always-loaded core | Move / simplify | Required proof |
|---|---|---|---|
| `feature-intake` | input type, lane/confidence separation, decision order, SUMMARY/Intent write, route | Read gate vocabulary/modes from `harness-manifest.json`; move slug derivation and run-state examples to focused references/helper commands; remove repeated explanations of the two axes | existing intake fixtures + trigger eval + manifest parity + tiny/normal/high-risk/ambiguous routing canaries |
| `brainstorming` | no-implementation gate, one-question discovery, alternatives, design approval, xia2 → writing-plans handoff | collapse checklist/process/after-design repetition; move reviewer loop mechanics to one conditional reference; retain visual-artifact judgment as one rule | design-fork, ambiguous, already-clear, user-revision, and handoff cases |
| `xia2` | research gate, local-first evidence sequence, evidence labels, brief output | stop independently re-classifying risk when intake already supplied a lane; define lane→research-depth mapping; keep portable fallback depth logic in a conditional reference; move ecosystem manifest catalog/template details out of core | existing depth canaries + lane/depth cross-product + waiver + stale-evidence cases |
| `writing-plans` | explicit read of `rules/plan-format.md`, required inputs, acceptance-first decomposition, execution handoff | remove the second summary of the canonical schema; move auto-view and review-overlay details to `visual-planner`; compact reviewer-loop instructions | valid/invalid plan fixtures, SC coverage, missing brief, same-wave overlap, handoff |
| `using-git-worktrees` | detect-before-create, native-first, submodule distinction, deploy harness, clean baseline, branch naming | put fragile detection and fallback validation in a tested helper; keep only its invocation and result routing in the skill | normal checkout/worktree/submodule, ignored/unignored fallback root, deployment failure |
| `subagent-driven-development` | Step-0 gate, task/wave loop, two-stage review order, blocker routing, final oracle chain, receipt conjunction | replace the 16-state resume essay with a deterministic `resume-check` command returning an action/cursor/reason; put rare repair/resume procedures behind exact conditional reads; remove paraphrases of downstream review skills and threshold copies | all run states and legal transitions tested in code, first-run/resume/repair canaries, context-propagation tests, receipt + SC conjunction |
| `correctness-review` | diff selection, six-angle orchestration, dedup, scorer call, threshold route, fix budget, residual gate | move benchmark/history narrative to README; store threshold in one machine-readable authority; split shared FIND contract from six angle fragments and compose only shared+selected angle; read Rule 4 authority rather than inline a drifting list | existing review-chain benchmark, scorer/threshold contract, all six prompt compositions, unreadable-file cap, fix-loop budget |
| `context-propagation-audit` | trigger, consumer matrix, delivery types, hard-fail rules, proof requirement | move incident narrative and worked examples to a reference; add a deterministic inventory helper where possible; retain explicit distinction between parent and child contexts | existing P1/P2 fixtures, context-boundary probes, no-consumer search-surface case |
| `intent-review` | oracle priority, constrained blindness, taxonomy/routing, residual gate | state the exception precisely: reviewer is blind to PLAN except the SC table explicitly passed by the controller; move three-oracle rationale/history to README; compact repeated relationships | intent gap/excess/drift fixtures, missing oracle STOP, SC-unproven, conflict escalation |
| `compound` | when to run, track emission decision, orchestrator-only writes, completion report | move INDEX rebuild, collision numbering, and frontmatter extraction to a deterministic script; reuse canonical templates; reduce four subagent prompts to focused inputs/outputs with a shared composed schema | bug/knowledge/decision/failure emission, multi-decision consolidation, collision, critical promotion, index rebuild |
| `finishing-a-development-branch` | test gate, receipt gate, plan lifecycle, push/open-PR-only invariant | move base/plan resolution and repeated receipt command construction to a helper; move incident rationale and PR body to references/template; eliminate repeated prose around the same push gate | non-main base, mismatched branch/spec slug, stale receipt, tiny skip, shipped status, never-merge test |
| `visual-planner` | renderer/view commands, review-mode branch, self-check failure behavior | move rendering feature catalog, parser internals, historical deviations, and verified examples to README/reference; leave code as authority | existing renderer tests, plain/review/self-check/view smoke tests |

## 6. Companion prompt strategy

Companion prompts are part of the product and are measured separately from `SKILL.md`.

- Create a prompt-composition convention: shared contract + exactly one role/angle fragment +
  invocation inputs. The rendered child prompt must be self-contained.
- Preserve explicit Reads for path-scoped policies in every isolated context that relies on them.
- Give every child one strict return schema. Validate it mechanically before the controller acts.
- Avoid a universal mega-prompt. Sharing is allowed only through deterministic composition;
  “the child can read the parent skill” is not delivery proof.
- Refactor in this order: correctness finder/scorer, SDD implementer/reviewers, intent reviewer,
  document reviewers, then compound extractors.

## 7. Rollout strategy

1. Freeze and record the current baseline before changing prompts.
2. Add measurement and contract tests first.
3. Extract deterministic helpers while old prompts still call the old path; compare outputs.
4. Refactor one skill family at a time. Run its focused eval and full contract suite after each.
5. Run the full pre/post corpus and holdout. Reject or revise any regression.
6. Deploy the derived `.claude/` copy only after source tests and context-propagation audit pass.
7. Open a PR; do not merge without human review. For workflow-engine changes, request one
   outside-lineage reviewer as recommended by `finishing-a-development-branch`.

## 8. Non-goals

- Removing a skill merely because its prompt is long.
- Merging the three review oracles; their different blindness boundaries are intentional.
- Weakening branch isolation, hard gates, review receipts, SC coverage, or escalation rules.
- Rewriting historical specs/results to match the new prompt surface.
- Automating every judgment call. Ambiguity, design trade-offs, and semantic review remain model
  work; only deterministic mechanics move to code.
- Optimizing for one model version without a holdout and an explicit versioned result.

## 9. Principal risks

| Risk | Mitigation |
|---|---|
| A “boilerplate” line hides a unique gate | Build the contract inventory first; every deleted constraint must map to an authority and proof |
| Progressive disclosure causes a child to miss policy | Parent names the exact read condition; prompt builder composes all child-required content; context audit must pass |
| New scripts create more maintenance than they remove | Extract only deterministic, branch-heavy logic with a structured contract and focused tests |
| Prompt A/B is noisy | Pin environment, record first run, use repeated runs only where declared, keep holdout cases |
| Global refactor makes regressions hard to localize | Ship by skill family and keep one focused commit per family |
| Token target encourages harmful deletion | Quality gates run first and are absolute; efficiency is evaluated only among quality-passing candidates |
