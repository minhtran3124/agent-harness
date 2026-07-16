<!--
  Escalation channel. Copy to specs/<slug>/ESCALATIONS.md.
  Default is DENY-ON-NO-RESPONSE: if `decision:` stays `pending`, the work stays BLOCKED.
  The agent appends an escalation block and stops; a human appends the decision.
-->

# <slug> — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-quality-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: <orchestrator / agent>
- date: <YYYY-MM-DD>
- trigger: hard-gate | low-confidence | ambiguous-direction | in-flight | system-redefinition
- question: <one sentence — the decision needed>
- context: <one line — what work is blocked on this>
- options:
  - A) <option + consequence>
  - B) <option + consequence>
- default_if_no_response: BLOCK
- decision: pending
- decided_by: <name once decided>
- decided_at: <YYYY-MM-DD>

<!-- copy the E0xx block for each new escalation -->
