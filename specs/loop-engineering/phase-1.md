# Phase 1 — Ground-truth the proposal doc

Lane: tiny (docs-only, no code paths) · Confidence: high · Effort: S
Target repo: `minhtran3124/agent-harness` → `research-loop.md`
Prereq artifacts: `research-brief.md` (verdict table §2), `roadmap.md` (this spec dir).

## Objective

`research-loop.md` currently asserts five "missing abstractions" of which four are
contradicted by shipped code. Left as-is, it becomes a false premise that propagates
through plan-anchored reviews. Phase 1 rewrites the diagnosis while preserving the
(correct) target architecture, so later phases plan from ground truth.

## Non-goals

- No code changes anywhere.
- No restructuring of sections 11–18 (kept as-is per REVISE verdict).
- No implementation of evaluator protocol / budgets (Phases 2+).

## Tasks

### T1 — Add provenance header
Files: `research-loop.md` (top)
Action: insert a status block: "Diagnosis originally written before disk verification;
current-state claims corrected 2026-08-22 against harness-skills @ <sha> — see
`specs/loop-engineering/research-brief.md` for per-claim evidence."
Done: header present; names the evidence brief.

### T2 — Rewrite "Core Finding / Main missing abstractions"
Files: `research-loop.md` §Core Finding
Action: replace the 7-item missing list with the verified 4-gap list
(evaluator protocol, run-level time budget, goal envelope w/ priority/deadline, per-iteration
receipts) + a "previously claimed missing, actually shipped" table citing file:line
(fix-round caps, non-progress detector, feedback routing, SC acceptance contract).
Done: no claim in the section contradicts the verdict table in research-brief.md §2.

### T3 — Correct sections 5 and 8 (current-state description)
Files: `research-loop.md` §5, §8
Action: §5 — acknowledge the existing caps/progress guards and reframe the delta as
"run-level, not round-level"; §8 — replace "review near the end" with the accurate
per-task-review-inside-the-wave description, keeping the correct cheap-tier/final-gate
split that §8 already proposes.
Done: sections describe the shipped workflow accurately.

### T4 — Add "Oracle reconciliation" section
Files: `research-loop.md` (new section after §8)
Action: document the resolved design: deterministic evaluators in-loop; three LLM
oracles (correctness / intent / context-propagation-audit) remain plan-blind final
gates; explicitly reject §4's correctness-review-per-iteration variant and say why
(cost + receipt semantics).
Done: section exists; §4 carries a pointer to it.

### T5 — Add "Binding constraints" section
Files: `research-loop.md` (new section before implementation order)
Action: list the shipped constraints any implementation must clear: no-new-hooks bar,
no LLM-as-judge acceptance checks, index-safe state reads, plan-blind FIND stage
untouched; cite the docs/solutions entries by path.
Done: all four constraints named with sources.

### T6 — Align §17 implementation order with roadmap.md
Files: `research-loop.md` §17
Action: reframe P0 from "define Goal contract / state machine" (already shipped as SC
table + run_state.py) to "name and connect existing primitives"; order becomes the
5-phase roadmap. Keep "do not start with /loop or /goal" conclusion.
Done: §17 matches `specs/loop-engineering/roadmap.md` phases 1–5.

## Verify

| Check | Command | Expected |
|---|---|---|
| No stale "MISSING" claims for shipped items | `grep -n "missing" research-loop.md` reviewed manually against research-brief.md §2 | 0 contradictions |
| Evidence pointers resolve | spot-check each cited `file:line` in harness-skills | all exist |
| Markdown renders | `git diff --stat` limited to `research-loop.md` | docs-only diff |

## Escalation

None expected. If revising the doc surfaces a claim the audit did not cover, verify it
on disk first (never resolve by prose) — `not_observed != absent`.

## Rollback

`git revert <sha>` (single docs commit).
