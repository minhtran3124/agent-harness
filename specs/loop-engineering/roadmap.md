# Loop Engineering — Roadmap

Principle: **name and connect what exists; build only the verified gaps.**
Evolve `resume_decision.py` / `run_state.py` / SC contract — do not build a parallel loop framework.

```text
            Phase 1                Phase 2               Phase 3
        ┌─────────────┐       ┌──────────────┐      ┌──────────────┐
        │ Ground-truth│       │  Evaluator   │      │    Goal      │
        │ the proposal│──────▶│ protocol v1  │─────▶│  envelope    │
        │ doc (S)     │       │ (M)          │      │  (M)         │
        └─────────────┘       └──────┬───────┘      └──────┬───────┘
                                     │                     │
                                     ▼                     ▼
                              ┌──────────────┐      ┌──────────────┐
                              │ Run-level    │      │ In-loop      │
                              │ budgets (M)  │─────▶│ deterministic│
                              │ Phase 4      │      │ eval (L)     │
                              └──────────────┘      │ Phase 5      │
                                                    └──────────────┘
        Later (explicitly deferred): /loop recurring outer scheduler,
        multi-agent optimization, cost/token budgets.
```

| Phase | Deliverable | Builds on (existing) | Effort | Gate risk |
|---|---|---|---|---|
| **1. Ground-truth the doc** | Revised `research-loop.md` in agent-harness: corrected Core Finding, verified gap list, oracle-reconciliation section, constraints section, warning header | Verdict table in `research-brief.md` §2 | S | none (docs-only) |
| **2. Evaluator protocol v1** | One result schema (`status/score/evidence/exit`) + thin adapters wrapping `verify_summary.py`, `check_verify_rows.py`, `check_review_receipt.py`; registry file. No new evaluators. | `REVIEW-RECEIPT.template.json` as schema seed | M | `scripts/` warn-tier in `ci-strict-gate.sh` |
| **3. Goal envelope** | Machine-readable goal block (id, SC refs, constraints, lane/confidence) in the spec sidecar; lifecycle mapped onto existing `run_state.py` states | SC table, `plan-format.md`, `run_state.py` FSM | M | index-safe requirement |
| **4. Run-level budgets** | `max_iterations` / `max_time` per run in `review-config.json`-style config; `resume_decision.py` returns `budget-exceeded` reason_code | `maximum_fix_rounds` precedent; `resume_decision.py` action set | M | no-new-hooks bar — implement inside existing scripts |
| **5. In-loop deterministic eval** | Controller runs the cheap tier after each iteration; per-iteration evaluation receipts; three LLM oracles stay final gates, final receipt still SHA-pinned | Phases 2–4 stable | L | receipt semantics must not weaken |

Dependencies: 2 → {4, 5}; 3 → 5. Phases 2 and 3 can run in parallel after 1.

Escalation triggers for the whole track: any phase requiring a new hook, weakening
receipt/oracle independence, or touching `settings.json` → human decision first.
