# review-policy — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: orchestrator (intent review, finding 1)
- date: 2026-10-11
- trigger: ambiguous-direction
- question: Should the policy's do-not-report list exclude "anything CI already enforces" (intent wording), or only lint and format findings that a wired linter or formatter already checks (as built)?
- context: Excluding everything CI checks could make a finder hold back a real runtime bug because a test or check exists; the approved design and two reviews narrowed it. Receipt and PR wait on this.
- options:
  - A) Keep the narrow scope (lint/format already checked; a runtime bug with a trigger stays reportable). No code change.
  - B) Widen to "anything CI already enforces". One policy line changes; finders may suppress real bugs covered by a CI check.
- default_if_no_response: BLOCK
- decision: A
- decided_by: Minh Tran (chat reply "A cả hai")
- decided_at: 2026-10-12

## E002

- raised_by: orchestrator (intent review, finding 3)
- date: 2026-10-11
- trigger: ambiguous-direction
- question: Must the correctness scorer also Read the policy (intent lists "correctness review (finders and scorer)"), or is it exempt as the approved design says?
- context: The scorer only scores evidence; Nit routing is its existing threshold, and the linter-moot rule is already in its prompt. Receipt and PR wait on this.
- options:
  - A) Keep the scorer exempt (`CONTEXT_MATRIX` rationale stays). No code change.
  - B) Add a policy Read to the scorer prompt and its matrix entry. Two files change; adds words to the scorer prompt.
- default_if_no_response: BLOCK
- decision: A
- decided_by: Minh Tran (chat reply "A cả hai")
- decided_at: 2026-10-12
