# Research brief — Superpowers 6.0 review-pipeline adoption

> Date: 2026-07-29

## Executive finding

The repository should adopt Superpowers 6.0's per-task review compression, but not its numbers or
its full workflow. The local lane system already solves the fixed-ceremony problem, and the final
review chain covers distinct oracles. The safe optimization boundary is the duplicate per-task
spec/quality evidence read.

## Evidence

| Claim | Local evidence | Upstream evidence |
|---|---|---|
| Two task reviewers remain | `skills/subagent-driven-development/SKILL.md:38-39` | v6 replaces them with `task-reviewer-prompt.md` |
| Minor currently blocks | SDD says not to advance with any open issue | v6 only loops on Critical/Important |
| Per-task spec result is binary | `spec-reviewer-prompt.md:66-68` | v6 adds cannot-verify-from-diff |
| Task evidence is pasted/rebuilt | `implementer-prompt.md:16`; both reviewer prompts | v6 task-brief/report/review-package file handoffs |
| PLAN lacks explicit global/interfaces contract | `rules/plan-format.md`; `writing-plans/SKILL.md` | v6 Global Constraints and per-task Interfaces |
| Reviewer is not fully immutable | `agents/reviewer.md:11` acknowledges Bash can mutate | v6 reviewers are explicitly read-only |
| Local final oracles are distinct | SDD `references/review-chain.md` | Upstream only has one broad final review |
| Local task scaling already exists | `feature-intake` tiny/normal/high-risk lanes | Article's amortization rule |

## Existing strengths to preserve

- Machine-enforced branch, risk, receipt, SUMMARY, and verification gates.
- Tiny lane for bounded work.
- Success Criteria coverage linked to SUMMARY Verify evidence.
- Context-propagation, correctness, and intent as separate final oracles.
- Independent correctness scorer.
- Existing skill eval and context-boundary corpora.
- Project-local worktrees and durable run state.

## Reliability correction

The article's claimed independent 12-session, -14% token result is not supported by its linked
benchmark. The linked 500-task study reports materially higher token use and runtime with no
statistically significant correctness gain. Therefore this plan requires a local A/B and sets no
headline savings assumption.

## Implementation constraints

1. Run the full existing test suite before editing any hook or script.
2. Capture baseline prompt/eval evidence before deleting the old reviewer prompts.
3. Keep legacy plan parsing and old shipped artifacts valid.
4. Use file paths for bulk handoffs; never paste generated diffs into controller dispatches.
5. Give every child prompt an explicit model and complete local contract.
6. Keep reviewer output bounded and mechanically checkable.
7. Record Minor findings durably and expose them to final review.
8. Preserve first-run and version-pinned evaluation discipline.

## Open implementation decisions resolved by this plan

- Unknown routing: one focused context expansion, then escalation.
- Minor routing: non-blocking, stored in SUMMARY, included in final-review input.
- Reviewer consolidation: local prompt only; remove optional external-template branch.
- Review package trust: optimized default view, not the boundary of truth.
- Model policy: explicit per dispatch, standard reviewer floor; cheap tier only for truly mechanical
  implementation.
- Rollout: quality gate first, then efficiency gate.
