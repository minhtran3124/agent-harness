# Resume actions

`resume_decision.py` is the authority. Invoke it source-tree-first, deployed-copy only when the
source is ABSENT — never as an error fallback, so a fail-closed exit 3 is not re-answered from a
stale deployed copy:

```
if [ -f runtime/resume_decision.py ]; then python3 runtime/resume_decision.py --slug <slug>; else python3 .claude/runtime/resume_decision.py --slug <slug>; fi
```

Do not discard stderr. Treat ANY non-zero exit as `stop`, and require `schema_version == 1` before
acting on `action`. For `rebuild`, run the named non-mutating check first, then
rebuild only when it reports projection drift. For `wait` or `stop`, report the returned reason and
do not edit. For `resume-repair` follow the named CI/review loop; do not re-run plan tasks. For
`resume-review-chain`, start final delivery/correctness/intent review. Only `execute-plan` enters
the preflight and wave loop.

On `execute-plan`, run every `cursor.checks_to_rerun` entry — the exact Verify of each task the
ledger claims complete — before dispatching `cursor.next_task`. A failed check is not a pass: route
it to the existing repair/escalation path instead of continuing the wave. Apply any
`required_transition` (activation, catch-up advance, or return-to-origin) only after the session has
confirmed the external condition it names; the decision command supplies the required edge, never
the judgment that its condition is met.
