# Research brief — skill prompt refactor

> Date: 2026-07-28 · Scope: current repository plus current Agent Skills guidance.

## Executive finding

The repository does not need another indiscriminate prose trim. It needs a contract-preserving
refactor around progressive disclosure, deterministic helpers, and pre/post evals.

The largest problem is not the number of registered skills (already reduced from 15 to 12 by
`specs/slim-skill-surface`). It is that a few runtime paths carry state-machine detail, historical
rationale, duplicated policy, and dispatch instructions together. The clearest example is
`subagent-driven-development`: 533 lines today, with the resume behavior expanded through a long
series of follow-up fixes and tests that parse exact prose.

## Local evidence

### Inventory and concentration

- `12` registered `SKILL.md` files: 2,612 lines / 23,268 words.
- `12` companion prompt files: 1,420 lines / 10,766 words.
- Total live prompt surface: 4,032 lines / 34,034 words.
- Largest `SKILL.md`: `subagent-driven-development` (533 lines / 5,260 words).
- Largest companion prompt: `correctness-reviewer-prompt.md`
  (451 lines / 3,743 words).
- `git log` shows 53 historical changes under `subagent-driven-development`, the highest of any
  skill. Fifteen of the twenty latest skill commits are resume-path fixes in that file.

### Existing quality evidence is uneven

| Skill/family | Current evidence | Main gap before refactor |
|---|---|---|
| `feature-intake` | labeled fixtures + automatic scorer; manual blind runs | activation eval and fresh baseline after prompt change |
| `correctness-review` / `intent-review` | five-fixture manual benchmark, false-positive accounting, threshold contract tests | automated prompt composition checks and a pinned pre-refactor rerun |
| `context-propagation-audit` | two escape fixtures + context-boundary probes | deterministic consumer inventory where possible |
| `subagent-driven-development` | many runtime tests plus phrase-based prompt assertions | end-to-end behavioral corpus; replace prose assertions with structured resume decisions |
| `visual-planner` | strong Python and hook tests | slim runtime instructions without changing renderer behavior |
| `brainstorming`, `using-git-worktrees`, `writing-plans`, `finishing`, `compound`, `xia2` | scattered structural or integration checks | systematic activation + behavioral eval coverage |

### Existing contract hazards

1. `runtime/test_run_state.py` reads the live SDD prompt and asserts exact phrases/tables.
   This proves documentation presence, not that a controller makes the correct decision.
2. The correctness threshold is repeated across several prompt files and guarded by regex parity.
   A single structured authority would be simpler.
3. Rule-4 policy has previously drifted in an inline reviewer copy. The current regression test
   protects eight keywords, but the safer shape is an explicit Read/composed authority.
4. `xia2` and `feature-intake` both classify similar signals for different purposes. Without an
   explicit mapping, the same request can be independently labeled twice.
5. `compound` asks the model to rebuild and sort `INDEX.md`, and `finishing` asks it to resolve
   base/spec paths. These are deterministic operations better expressed as tested scripts.

## External guidance

The Agent Skills specification defines progressive disclosure as three tiers: catalog metadata,
the activated `SKILL.md`, and supporting resources loaded on demand. It recommends keeping the
activated instruction body focused and putting scripts/references/assets beside it:

- [Agent Skills specification](https://agentskills.io/specification)
- [Adding skills support — progressive disclosure](https://agentskills.io/client-implementation/adding-skills-support)

The current skill-creation guidance says to cut content the agent would already handle correctly,
prefer concise stepwise guidance, match instruction specificity to task fragility, and move large
conditional material to focused references with an explicit read condition. It recommends keeping
`SKILL.md` under roughly 500 lines / 5,000 tokens:

- [Agent Skills best practices](https://agentskills.io/skill-creation/best-practices)

Activation depends primarily on the frontmatter description. The guidance recommends evaluating
descriptions with realistic positive and near-miss negative prompts, typically around 8–10 of each,
and using a holdout set:

- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)

OpenAI's API guidance notes that prompting behavior changes across model snapshots and recommends
pinned model versions plus evals for consistent measurement:

- [OpenAI API guidance on model-version consistency](https://platform.openai.com/docs/api-reference/debugging-requests)

## Recommended principles

1. **Quality gate before compression metric.** A token reduction is accepted only after safety,
   behavior, and handoff checks pass.
2. **One authority per load-bearing value.** Gate vocabulary, state sets, threshold, schema, and
   lane/depth mapping should be machine-readable or explicitly read from the canonical file.
3. **Progressive disclosure must be conditional.** “See references” is insufficient; say exactly
   when to read which file.
4. **Isolated contexts receive composed prompts.** A child never inherits a policy merely because
   the parent read it.
5. **Move mechanics, not judgment, to code.** State transitions, index sorting, path resolution,
   prompt assembly, and schema validation are good script candidates. Intent interpretation and
   adversarial review are not.
6. **Keep rationale, but off the runtime path.** Benchmarks, incident stories, and rejected
   alternatives belong in README/research/result artifacts.
7. **Refactor by family, not globally.** Intake/research/planning, execution/review, and
   terminal/artifact skills have different failure modes and evals.

## Priority order

| Priority | Target | Why first |
|---|---|---|
| P0 | Eval harness + baseline + contract inventory | prevents a shorter but weaker prompt from appearing successful |
| P1 | SDD resume + correctness FIND prompt | largest runtime context and highest maintenance/churn |
| P1 | Canonical policy/threshold/prompt composition | closes known drift and child-context delivery failure classes |
| P2 | `feature-intake` ↔ `xia2`, writing/brainstorming/worktree | removes duplicate classification and planning prose |
| P2 | `compound`, `finishing`, `visual-planner` | deterministic extraction and runtime-doc slimming |
| P3 | descriptions and cross-skill docs | tune activation after bodies and handoffs stabilize |

## Open decisions for plan review

- Exact model snapshot(s) available for the A/B baseline must be recorded when execution starts.
- The 25% overall / 50% heavy-path context reduction targets are proposed acceptance thresholds;
  they may be tightened after the baseline tool measures actual composed prompts.
- `xia2` should remain portable. The proposed lane→depth mapping applies when `feature-intake`
  metadata exists; the generic fallback classifier remains available as an on-demand reference.
