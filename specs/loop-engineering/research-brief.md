# Research Brief — Loop Engineering for the Harness

Status: research (ground-truthed) · Depth: Deep · Date: 2026-08-22
Source proposal: `minhtran3124/agent-harness` → `research-loop.md` (861 lines)
Verdict on the proposal: **REVISE** — keep the target architecture, rewrite the current-state diagnosis.

## 1. What was assessed

`research-loop.md` proposes evolving the harness from a gated workflow into a
Goal / Evaluator / Loop-Controller model (four layers: Human → Harness → Loop Engine → Agents).
This brief records the disk-verified assessment so no downstream plan inherits an
unverified premise (`docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md`).

## 2. Ground-truth verdicts (claims vs. shipped code)

| # | Claim in research-loop.md | Verdict | Evidence |
|---|---|---|---|
| 1 | correctness-review: six FIND angles → dedupe → score → threshold → classify → fix → re-review | TRUE | `skills/correctness-review/SKILL.md:18-29`, `review-config.json:3-10`, prompt files per angle |
| 2 | Durable run state / resume exists | TRUE (stronger than described) | FSM in `runtime/run_state.py:233-304,465-474`; `runtime/resume_decision.py` (structured action/reason_code); `hooks/state-breadcrumb.sh` |
| 3 | Review receipts exist; a post-review **code** commit invalidates them (`specs/`-only bookkeeping commits are exempt by design) | TRUE | `scripts/check_review_receipt.py:135-157` pins 40-hex `reviewed_head_sha`; `stale-sha` on HEAD advance (specs/-only bookkeeping carve-out) |
| 4 | Iteration/time/cost/retry budgets MISSING | **FALSE** for iteration/retry, TRUE only for run-level time+cost | `review-config.json:14` `maximum_fix_rounds: 3`; SDD one-retry rule `SKILL.md:58-59`; `orchestration.md:78`; shipped spec `specs/acceptance-contract-loop-budget/` |
| 5 | Convergence / progress detection MISSING | **FALSE** | `skills/correctness-review/SKILL.md:28-29` (findings-not-decreasing + diff-hash-unchanged → escalate); `rules/orchestration.md:74-85`; `hooks/blast-radius-check.sh` (wired) |
| 6 | Evaluator feedback into next action MISSING | **FALSE** | fix rounds + re-review (`correctness-review/SKILL.md:26-29`); verdict-routed re-dispatch (`subagent-driven-development/SKILL.md:59-63`); intent-review routing (`intent-review/SKILL.md:29-41`) |
| 7 | Goal as first-class object MISSING | **FALSE** (~70% exists under other names) | SC table = acceptance contract (`rules/plan-format.md:69-108`); Global Constraints; SC coverage enforced by `scripts/verify_summary.py:372-411`. Genuinely missing: priority/deadline-bearing goal object |
| 8 | Current workflow = "implement → review near the end → ship" | **FALSE** | Per-task review runs inside the wave loop (`subagent-driven-development/SKILL.md:8-9,55-61`); final chain is an *additional* gate |
| 9 | Escalation and human gates exist | TRUE | `rules/orchestration.md:55-72`; deny-on-no-response mechanized by `commit-quality-gate.sh` Check 1.5 |
| 10 | No loop controller / goal FSM / evaluation receipts today | **FALSE** — all three exist in embryo | Controller: SDD SKILL + `resume_decision.py` (6 actions); FSM: `run_state.py`; receipts: `REVIEW-RECEIPT.template.json` + exit codes stamped by `verify_summary.py` |
| 11 | Generalized evaluator interface exists | PARTIAL | Real machine-checkable evaluators exist (`verify_summary.py`, `check_verify_rows.py`, `check_review_receipt.py`) but each is a bespoke CLI; no shared protocol/result schema/registry |

Root cause of the false negatives: the proposal audited by keyword ("goal", "budget",
"converge" barely appear) while the concepts ship under the names *acceptance contract*,
*Success Criteria*, *fix rounds*, *in-flight escalation checks*.

## 3. The real gaps (verified)

1. **Unified evaluator protocol** — one result schema (`status/score/evidence/exit`) + thin
   adapters over the existing bespoke checkers. Highest value, moderate cost.
2. **Run-level budgets** — `max_iterations` / `max_time` per run (fix-round caps exist; run-level
   wall-clock and cost/token budgets do not). Token cost is unmeasurable today → defer cost budget.
3. **Goal envelope** — a named, machine-readable bundle of SC table + Global Constraints +
   lane/confidence with an id; lifecycle mapped onto the *existing* `run_state.py` FSM, not a new one.
4. **Per-iteration evaluation receipts** — generalize the review receipt; final SHA-pinned
   receipt semantics unchanged.

## 4. Architecture decision: three-oracle vs in-loop feedback

Resolved, not a contradiction:

- **In-loop tier** — cheap deterministic evaluators only (pytest, SC/Verify rows, lint,
  benchmarks). These are not oracles; running them every iteration pollutes nothing.
- **Final-gate tier** — the LLM oracles stay plan-blind final gates as today:
  correctness-review and intent-review universal; context-propagation-audit keeps its
  conditional trigger (workflow-engine diffs only, `references/review-chain.md:3`).
- Proposal §8 is correct; proposal §4 (correctness-review inside every iteration) is
  rejected: expensive, and it turns "review of the final result" into "review of drafts",
  voiding receipt semantics.

## 5. Binding constraints (from shipped decisions)

- No change to correctness-review's plan-blind FIND stage; no LLM-as-judge acceptance checks
  (`specs/acceptance-contract-loop-budget/design.md` non-goals).
- No new hooks / standing automation without clearing the bar in
  `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md` and `automation-readiness.md`.
- Any goal/budget state a gate reads must be index-safe
  (`docs/solutions/harness/gate-config-must-read-index.md`) — never worktree-only.
- Known loop-control bug to design against: `docs/solutions/harness/review-round-skipped-when-two-arrive-together.md`.

## 6. Source Pack

- Local: files cited per-claim in §2 (primary evidence).
- External surface: conceptual only — no new dependency. Upstream grounding:
  - https://addyosmani.com/blog/agent-harness-engineering/
  - https://towardsdatascience.com/context-engineering-isnt-enough-a-loop-engineering-experiment-with-no-llm-inside-the-loop/
  - https://blogs.oracle.com/developers/the-agent-loop-decoded-three-levels-every-agent-engineer-must-know
  - https://github.com/ai-boost/awesome-harness-engineering
- Consensus alignment: generation/evaluation separation, deterministic controller
  ("no LLM inside the loop"), explicit stop conditions — all match the proposal's target layers.

## 7. Scores (0–10)

| Axis | Score |
|---|---|
| Current-state diagnosis correctness | 3 |
| Proposed-architecture correctness | 8 |
| Completeness | 5 |
| Feasibility | 7 |
| Practical value to this repo | 6 |

See `roadmap.md` (phased plan) and `phase-1.md` (first executable phase).
