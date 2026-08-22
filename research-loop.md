# Research: Loop Engineering for Agent Harness

## Status

Research / architecture proposal. This document does **not** prescribe an immediate implementation. It captures how the existing harness could evolve toward a Loop Engineering model while preserving its current governance and review strengths.

> **Provenance note (2026-08-22).** The current-state diagnosis in the original draft was
> written before disk verification and over-claimed several gaps. The claims below have been
> corrected against the shipped code at `38e7103` — see
> `specs/loop-engineering/research-brief.md` for the per-claim evidence table (11 claims,
> each with `file:line` sources). The target architecture (sections 11–18) is unchanged.

## Context

The harness already provides a strong workflow-oriented control system:

```text
Request
  ↓
feature-intake
  ↓
risk / confidence / route
  ↓
brainstorm → research → plan
  ↓
worktree / branch isolation
  ↓
subagent-driven-development
  ↓
verify + task review
  ↓
correctness review
  ↓
intent review
  ↓
compound / ship
```

The key observation is that this is primarily a **gated workflow**. It has retry and verification loops, but the central abstraction is still the task/plan and its completion gates.

Loop Engineering suggests a complementary execution model:

```text
Goal
  ↓
┌──────────────────────────────┐
│          AGENT LOOP          │
│                              │
│ Plan → Act → Observe         │
│           ↓                  │
│         Evaluate             │
│           ↓                  │
│       Goal reached?          │
│        ↙       ↘             │
│      No         Yes          │
│      ↓           ↓           │
│    Adjust       Done         │
│      │                         │
│      └───────────┐             │
└──────────────────┼─────────────┘
                   ↓
             Human judgment
```

The proposed direction is therefore **not** to replace the existing harness with an autonomous loop. Instead, add a Loop Engine below the existing governance layer.

---

## Core Finding

The repository already has most of the primitives required for Loop Engineering, but they are currently expressed as workflow-specific mechanisms.

### Already strong

- Risk classification and hard gates
- Confidence / ambiguity handling
- Branch and worktree isolation
- Task-level verification
- Independent task review
- Adversarial correctness review
- Intent review
- Context-propagation audit
- Escalation and human gates
- Durable run state / resume behavior
- Review receipts and evidence
- Knowledge compounding
- Distinct agent roles and capability contracts

### Previously claimed missing — actually shipped

The original draft listed seven missing abstractions. Disk verification shows most exist
under different names (*acceptance contract*, *Success Criteria*, *fix rounds*,
*in-flight escalation checks*):

| Claimed missing | Shipped as | Evidence |
|---|---|---|
| Iteration / retry budgets | `maximum_fix_rounds: 3`; one-retry rule for `cannot_verify`; fail-≥2 escalation | `skills/correctness-review/review-config.json:14`; `skills/subagent-driven-development/SKILL.md:58-59`; `rules/orchestration.md:78` |
| Convergence / progress detection | findings-not-decreasing + diff-hash-unchanged → escalate; in-flight escalation checks; blast-radius hook | `skills/correctness-review/SKILL.md:28-29`; `rules/orchestration.md:74-85`; `hooks/blast-radius-check.sh` |
| Evaluator feedback → next action | fix rounds + re-review; verdict-routed re-dispatch; intent-review routing | `skills/correctness-review/SKILL.md:26-29`; `skills/subagent-driven-development/SKILL.md:59-63` |
| Goal as first-class object (~70%) | SC table = acceptance contract + Global Constraints, SC coverage enforced | `rules/plan-format.md:69-108`; `scripts/verify_summary.py:372-411` |
| Goal lifecycle / state machine | run-state FSM + executable resume-decision authority | `runtime/run_state.py:233-304`; `runtime/resume_decision.py` |
| Loop controller | SDD wave controller + 6-action decision function | `skills/subagent-driven-development/SKILL.md`; `runtime/resume_decision.py` |

### Verified remaining gaps

1. **Unified evaluator protocol** — one result schema (`status/score/evidence/exit`) +
   thin adapters over the existing bespoke checkers (`verify_summary.py`,
   `check_verify_rows.py`, `check_review_receipt.py`); no shared registry today.
2. **Run-level budgets** — `max_iterations` / `max_time` per run (round-level caps exist;
   run-level wall-clock does not; cost/token budgets deferred — not measurable today).
3. **Goal envelope** — a named, machine-readable bundle (id, SC refs, constraints,
   lane/confidence, priority/deadline) mapped onto the *existing* `run_state.py` FSM.
4. **Per-iteration evaluation receipts** — generalize the review receipt; final
   SHA-pinned receipt semantics unchanged.

---

# 1. Goal should become a first-class abstraction

Today the plan/task is the primary unit of execution. A Loop Engine needs a higher-level unit: a **Goal**.

A goal should capture:

```yaml
goal:
  id: feature-x

  objective: "Reduce API p95 latency"

  success_criteria:
    - "p95 < 300ms"
    - "cache hit rate > 80%"
    - "all tests pass"
    - "no public API regression"

  constraints:
    - "no database schema change"
    - "no new external dependency"

  evaluators:
    - pytest
    - performance-benchmark
    - correctness-review
    - intent-review

  budget:
    max_iterations: 5
    max_time_minutes: 60
    max_cost: null

  escalation:
    - "no progress for 2 iterations"
    - "irreversible change required"
    - "budget exceeded"
```

The important distinction is:

> A task describes what the agent should do. A goal describes what must be true when the system is finished.

This allows the agent to change its implementation strategy across iterations while the controller continues evaluating the same objective.

---

# 2. Feature intake can evolve into a Goal Compiler

`feature-intake` is already the natural entry boundary. It currently classifies risk and confidence and chooses the appropriate workflow.

The next evolution should be to compile the request into a structured goal envelope:

```text
request
  ↓
feature-intake
  ↓
┌──────────────────────────────┐
│ Goal Compiler                │
│                              │
│ objective                    │
│ risk                         │
│ confidence                   │
│ success criteria             │
│ evaluators                   │
│ constraints                  │
│ iteration budget             │
│ human gates                  │
│ escalation conditions        │
└──────────────────────────────┘
```

The existing risk lanes should remain authoritative for determining how much autonomy is allowed.

Example:

```text
high-risk + clear
  → autonomous execution may still be possible,
    but with stronger evaluators and human gates

tiny + ambiguous
  → stop for clarification before autonomous execution
```

Risk and ambiguity should remain separate dimensions.

---

# 3. Existing reviews should become Evaluators

The repository already contains sophisticated evaluation logic. The opportunity is to generalize it rather than replace it.

Potential evaluator interface:

```text
evaluate(goal, execution_state, evidence) → EvaluationResult
```

Possible evaluators:

```text
TestEvaluator
CorrectnessEvaluator
IntentEvaluator
SecurityEvaluator
PerformanceEvaluator
ContractEvaluator
HumanEvaluator
```

A result should contain evidence rather than only a model-generated opinion:

```json
{
  "status": "pass | fail | unknown",
  "score": 91,
  "findings": [],
  "evidence": [
    {
      "command": "pytest tests/cache",
      "exit_code": 0
    }
  ]
}
```

This makes the evaluator an objective feedback source for the loop controller.

---

# 4. Correctness review is already a strong evaluator candidate

The existing correctness-review pipeline is especially suitable for this role:

```text
six independent FIND angles
        ↓
deduplicate
        ↓
score
        ↓
threshold
        ↓
classify
        ↓
fix
        ↓
re-review
```

This is already a bounded feedback loop. The architectural change would be to expose its result as an evaluator output rather than treating it exclusively as a final shipping gate.

For example:

```text
implementation iteration 1
        ↓
correctness evaluator
        ↓
FAIL: null handling in X
        ↓
controller feeds finding back to implementer
        ↓
iteration 2
        ↓
correctness evaluator
        ↓
PASS
```

The existing safety limits and escalation behavior should remain intact.

---

# 5. Retry is not the same as a Loop Engine

The current SDD workflow already supports retry, repair, re-review, and escalation.

Conceptually:

```text
implement
  ↓
verify
  ↓
review
  ↓
fail?
  ├─ yes → repair → review again
  └─ no  → continue
```

This is a **micro-loop around task completion**.

A Loop Engine is a controller-level loop:

```text
while goal_not_satisfied:
    execute_action()
    collect_evidence()
    evaluate()
    diagnose_failure()
    choose_next_action()
```

The distinction matters because the next iteration may legitimately change the implementation approach rather than merely apply a small fix.

Note that the micro-loop is already bounded and progress-guarded: fix rounds are capped at
three per finding, and a round with non-decreasing findings on an unchanged diff hash
escalates immediately (`skills/correctness-review/SKILL.md:28-29`). The genuine delta a
Loop Engine adds is **run-level** control (whole-goal iteration and time budgets, strategy
changes between iterations), not round-level control, which ships today.

---

# 6. Introduce a unified Goal state machine

The existing durable run state and resume mechanisms are useful foundations, but the Loop Engine should have an explicit goal lifecycle.

Proposed conceptual state machine:

```text
PENDING
  ↓
PLANNING
  ↓
EXECUTING
  ↓
EVALUATING
  ↓
 ┌─────────────────────────────────┐
 │                                 │
 PASS                         FAIL / UNKNOWN
 │                                 │
 ↓                                 ↓
COMPLETED                    DIAGNOSING
                                  ↓
                           NEXT_ACTION_DECISION
                             ↙      ↓       ↘
                          RETRY   HUMAN    STOP
                            │      │
                            └──→ WAITING
```

Additional terminal states may include:

```text
ESCALATED
BUDGET_EXCEEDED
ABORTED
```

The controller should make state transitions explicit rather than reconstructing them from prose.

---

# 7. The Loop Controller should be deterministic infrastructure

The Loop Controller should **not** be another vague "autonomous agent" prompt.

It should own:

- goal state
- iteration count
- evaluator results
- budget
- progress tracking
- escalation rules
- agent dispatch
- stop conditions

Conceptually:

```text
                Goal
                  │
                  ▼
             Controller
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
      Agent    Evaluator   Budget
        │         │         │
        └────┬────┴────┬────┘
             ▼         │
          Decision     │
          ↙  ↓  ↘     │
       retry done wait │
         │             │
         └─────────────┘
```

The agent should primarily **act**. The evaluator should **measure**. The controller should **decide**. Human approval should provide **judgment** where required.

---

# 8. Evaluation must happen inside the loop

Current workflow (corrected — the original draft understated it):

```text
per task:  implement → verify → two per-task reviews   ← inside the wave loop
  ↓
final gates: correctness review → intent review → receipt
  ↓
ship
```

Per-task review already runs *inside* the wave loop — "a task may advance only after its
Verify command and both per-task reviews are green"
(`skills/subagent-driven-development/SKILL.md:8-9`). The final chain is an additional
gate, not the only evaluation point.

Loop-oriented workflow:

```text
implement
  ↓
evaluate
  ↓
feedback
  ↓
adjust
  ↓
implement again
  ↓
evaluate again
  ↓
...
```

This changes reviews from being only **gates** into **feedback signals**.

The existing final review chain should still exist. The difference is that cheap, deterministic evaluators can run during the loop, while expensive or high-risk reviews can remain final gates.

---

# 8b. Oracle reconciliation (resolved design decision)

The harness deliberately keeps three independent oracles — correctness-review
(plan-blind), intent-review (plan-prose-blind), and context-propagation-audit. In-loop
evaluation must not erode that independence. The resolved split:

- **In-loop tier**: cheap deterministic evaluators only — pytest, SC/Verify rows via
  `verify_summary.py`, lint, benchmarks. These are not oracles; running them every
  iteration pollutes nothing.
- **Final-gate tier**: the LLM oracles stay exactly where they are, blind exactly as they
  are, and the final receipt stays SHA-pinned. Correctness-review and intent-review are
  universal; context-propagation-audit keeps its existing **conditional** trigger — it runs
  only when the cumulative diff touches workflow-engine paths
  (`skills/subagent-driven-development/references/review-chain.md:3`) and must not become
  mandatory for unrelated changes.

The variant sketched in section 4 — running correctness-review inside every iteration as
a feedback signal — is **rejected**: it is expensive, and it turns "review of the final
result" into "review of drafts", voiding receipt semantics. Section 4 remains as an
illustration of evaluator-shaped output only; see this section for the binding decision.

---

# 9. Add explicit budgets and convergence controls

Autonomous loops need bounded failure modes.

At minimum:

```yaml
budget:
  max_iterations: 5
  max_time_minutes: 60
  max_cost: null
  max_retries_per_finding: 3
```

And progress detection:

```text
if same_failure repeats:
    escalate

if evaluation score does not improve for N iterations:
    escalate

if diff keeps growing without success-criteria improvement:
    stop / human review

if a hard gate is triggered:
    stop immediately
```

This prevents an agent from spending unlimited tokens making increasingly unrelated changes.

---

# 10. Evaluation receipts should become iteration evidence

The existing review receipt concept can be generalized into an evaluation receipt.

Example:

```json
{
  "goal_id": "feature-x",
  "iteration": 3,
  "commit": "abc123",
  "evaluations": [
    {
      "name": "pytest",
      "status": "pass"
    },
    {
      "name": "performance",
      "status": "pass",
      "score": 94
    },
    {
      "name": "correctness",
      "status": "pass"
    },
    {
      "name": "intent",
      "status": "pass"
    }
  ],
  "success": true,
  "remaining_findings": [],
  "budget": {
    "iterations_used": 3,
    "max_iterations": 5
  }
}
```

The system can then distinguish:

```text
"agent says done"
```

from:

```text
"system has evidence that the goal is satisfied"
```

A post-review code change should invalidate the receipt, preserving the existing trust model.

---

# 11. Keep governance separate from execution

The recommended architecture is four layers:

```text
┌───────────────────────────────────────────┐
│                 HUMAN                     │
│ intent / ambiguity / irreversible gates   │
└────────────────────┬──────────────────────┘
                     │
┌────────────────────▼──────────────────────┐
│               HARNESS                     │
│ risk / trust / permissions / escalation   │
└────────────────────┬──────────────────────┘
                     │
┌────────────────────▼──────────────────────┐
│             LOOP ENGINE                   │
│ goal / state / iteration / budget         │
│ evaluator / convergence / stop condition  │
└────────────────────┬──────────────────────┘
                     │
┌────────────────────▼──────────────────────┐
│                AGENTS                     │
│ plan / research / implement / review      │
└───────────────────────────────────────────┘
```

This is preferable to turning the whole repository into an autonomous-loop framework.

The existing harness should remain the **governance/control boundary**. The Loop Engine should become the **execution/control mechanism**.

---

# 12. Proposed responsibility split

| Component | Responsibility |
|---|---|
| Human | Intent, ambiguity resolution, irreversible judgment |
| Feature Intake | Classify request, risk, confidence, compile goal metadata |
| Harness | Permissions, isolation, risk gates, escalation |
| Goal | Objective, criteria, constraints, evaluator set |
| Loop Controller | State, dispatch, iteration, budget, decisions |
| Agent | Plan / research / implement / diagnose |
| Evaluator | Measure goal satisfaction and produce evidence |
| Review | Adversarial correctness / intent / contract checks |
| Compound | Persist reusable knowledge |
| Ship Gate | Final evidence and human merge boundary |

---

# 13. Proposed execution model

For a normal-risk task:

```text
feature-intake
  ↓
create goal
  ↓
research / plan
  ↓
loop controller
  ↓
┌────────────────────────────────────┐
│ iteration 1                        │
│                                    │
│ implement → verify → evaluate      │
│                      ↓             │
│                  feedback          │
└──────────────────────┬─────────────┘
                       │ fail
                       ▼
┌────────────────────────────────────┐
│ iteration 2                        │
│                                    │
│ adjust → implement → evaluate      │
└──────────────────────┬─────────────┘
                       │
                       ▼
                   goal met
                       │
                       ▼
              final review chain
                       │
                       ▼
                     ship
```

For high-risk work, the same loop can operate under stronger gates and narrower autonomy.

---

# 14. Continuous loops should be a later layer

A `/loop`-style recurring mechanism should **not** be the first implementation target.

First establish:

```text
Goal
Evaluator
Controller
```

Then a recurring loop becomes straightforward:

```text
schedule / event
      ↓
discover work
      ↓
create Goal
      ↓
run Goal Loop
      ↓
final review / human gate
```

Examples:

- Check open bugs every hour
- Detect dependency updates daily
- Find stale documentation weekly
- Monitor performance regressions
- Triage incoming issues

The recurring scheduler is an outer loop around the goal loop.

```text
Outer Loop
   ↓
discover work
   ↓
Goal Loop
   ↓
Evaluator
   ↓
Ship / escalate
   ↓
Outer Loop again
```

---

# 15. Multi-agent extension

Once the Loop Controller is established, multi-agent execution can be expressed naturally:

```text
                    GOAL
                      ↓
                  PLANNER
                      ↓
          ┌───────────┼───────────┐
          ↓           ↓           ↓
     Researcher   Implementer  Analyst
          │           │           │
          └───────────┼───────────┘
                      ↓
                EVALUATORS
                      ↓
                  CONTROLLER
                      ↓
              next iteration
```

The controller should decide whether to:

- reuse the same agent
- spawn a fresh context
- switch model class
- split the task
- request missing context
- escalate to a human

The existing agent capability contracts are a good foundation for this separation.

---

# 16. What should NOT change

The following existing mechanisms should be preserved rather than rewritten as part of Loop Engineering:

- risk lanes
- confidence classification
- hard gates
- branch isolation
- worktrees
- task reviewers
- correctness review
- context-propagation audit
- intent review
- escalation handling
- durable resume state
- evidence gates
- review receipts
- knowledge compounding

These are governance mechanisms, not loop execution primitives.

---

# 16b. Binding constraints (from shipped decisions)

Any implementation of this proposal must clear constraints already recorded in the repo:

- **No change to correctness-review's plan-blind FIND stage**, and **no LLM-as-judge
  acceptance checks** — contract checks are re-runnable shell commands only
  (`specs/acceptance-contract-loop-budget/design.md`, non-goals).
- **No new hooks / standing automation** without clearing the recorded bar
  (`docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md`,
  `docs/solutions/harness/automation-readiness.md`).
- **Index-safe state**: any goal/budget state a gate reads must come from the git index,
  never worktree-only files (`docs/solutions/harness/gate-config-must-read-index.md`).
- Design against the recorded loop-control bug:
  `docs/solutions/harness/review-round-skipped-when-two-arrive-together.md`.

---

# 17. Recommended implementation order

The guiding principle — corrected after disk verification — is **name and connect what
exists; build only the verified gaps**. The goal contract and state machine are *not*
greenfield work: the SC table is the goal contract, `runtime/run_state.py` is the state
machine, and `runtime/resume_decision.py` is the controller's decision function. Full
phase plan: `specs/loop-engineering/roadmap.md`.

## Phase 1 — Ground-truth this document (S)

Correct the current-state claims against shipped code (this revision).

## Phase 2 — Evaluator protocol v1 (M)

One result schema (`status/score/evidence/exit`) + thin adapters wrapping
`verify_summary.py`, `check_verify_rows.py`, `check_review_receipt.py`. No new
evaluators; `templates/REVIEW-RECEIPT.template.json` seeds the schema.

## Phase 3 — Goal envelope (M)

Machine-readable goal block (id, SC refs, constraints, lane/confidence) in the spec
sidecar; lifecycle mapped onto existing `run_state.py` states. Index-safe reads only.
Can run in parallel with Phase 2.

## Phase 4 — Run-level budgets (M)

`max_iterations` / `max_time` per run beside `maximum_fix_rounds`;
`resume_decision.py` gains a `budget-exceeded` reason_code. Implemented inside existing
scripts — no new hooks. Cost/token budgets deferred until measurable.

## Phase 5 — In-loop deterministic evaluation (L)

Controller runs the cheap tier after each iteration and records per-iteration evaluation
receipts; the three LLM oracles remain final gates; the final receipt stays SHA-pinned.
Only after Phases 2–4 are stable.

## Deferred

Recurring `/loop` outer scheduler and multi-agent optimization (sections 14–15) come
after the Goal Loop is reliable — unchanged conclusion.

---

# 18. Target architecture

The long-term target can be summarized as:

```text
                         HUMAN
                           │
                    intent / judgment
                           │
                           ▼
                  ┌─────────────────┐
                  │ FEATURE INTAKE  │
                  │ risk/confidence │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  GOAL COMPILER  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  HARNESS        │
                  │ isolation/gates │
                  └────────┬────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │             LOOP ENGINE              │
        │                                      │
        │  ┌────────┐      ┌──────────────┐   │
        │  │ AGENT  │ ───→ │  EVALUATORS  │   │
        │  └────┬───┘      └──────┬───────┘   │
        │       │                 │           │
        │       └──────→ CONTROLLER ←─────────┤
        │                         │           │
        │                 retry / done / wait │
        │                         │           │
        └─────────────────────────┼───────────┘
                                  │
                                  ▼
                         FINAL REVIEW CHAIN
                                  │
                                  ▼
                                SHIP
```

The architectural principle is:

> **Agents act. Evaluators measure. Controllers decide. Humans provide judgment. The harness controls trust and risk.**

---

# 19. Final assessment

The repository is already much closer to Loop Engineering than a typical agent framework because it has strong verification, isolation, review, escalation, and evidence mechanisms.

The main architectural gap is not another skill or another prompt. It is a **first-class control abstraction connecting goals, evaluators, iteration state, feedback, budgets, and stopping conditions**.

The recommended direction is therefore:

```text
Current

Workflow + Skills + Gates + Reviews

        ↓ evolve into

Target

Governance
    +
Goal-oriented Loop Engine
    +
Evaluator system
    +
Existing agent skills
```

Do **not** start by implementing `/loop` or `/goal` as user-facing commands. Start with the underlying Goal / Evaluator / Controller primitives. Once those are correct, `/goal` and `/loop` become thin interfaces over a much stronger architecture.
