# Resume actions

Before interpreting an `execute-plan` cursor, read `rules/plan-format.md` and
`rules/wave-parallelism.md`. This new-session context does not inherit the original controller's
path-scoped rule delivery.

`resume_decision.py` is the authority. Invoke the source-tree copy first. Invoke the deployed copy
only when the source is ABSENT. Never invoke the deployed copy as an error fallback. This way, a
stale deployed copy never re-answers a fail-closed exit 3. The command is:

```
if [ -f runtime/resume_decision.py ]; then python3 runtime/resume_decision.py --slug <slug>; else python3 .claude/runtime/resume_decision.py --slug <slug>; fi
```

Do not discard stderr. Treat ANY non-zero exit as `stop`. Require `schema_version == 1` before you
act on `action`. Act on each `action` value as follows:

- `rebuild`: run the named non-mutating check first. Rebuild only when it reports projection drift.
- `wait` or `stop`: report the returned reason. Do not edit.
- `resume-repair`: follow the named CI/review loop. Do not re-run plan tasks.
- `resume-review-chain`: start final delivery/correctness/intent review.

Only `execute-plan` enters the preflight and wave loop.

On `execute-plan`, run every `cursor.checks_to_rerun` entry before you dispatch `cursor.next_task`.
Each entry is the exact Verify of a task that the ledger claims complete. A failed check is not a
pass. Route a failed check to the existing repair/escalation path instead of continuing the wave.
Apply any `required_transition` (activation, catch-up advance, or return-to-origin) only after the
session has confirmed the external condition that it names. The decision command supplies the
required edge. It never supplies the judgment that its condition is met.
