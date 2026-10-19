# Files

- [Resume Decision](resume-decision.md) - runtime/resume_decision.py is the single read-only resume authority for a harness run. It maps durable run-state storage and FSM state to one lifecycle action (execute-plan, resume-repair, resume-review-chain, wait, stop, rebuild) and rebuilds a task cursor from the PLAN.md Status Log and branch commits. Contradictory evidence fails closed.
- [Run-State Engine](run-state-engine.md) - How runtime/run_state.py records each spec run as an append-only events.jsonl log with a rebuildable RUN.json projection. Covers the lifecycle FSM, fcntl locking, event-id idempotency, chain validation, the 0/2/3 exit-code contract, and the hooks, skills, and post-merge workflow that call it.
