# gh-312-test-seams — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: orchestrator (intent review, finding 4)
- date: 2026-10-16
- trigger: ambiguous-direction
- question: Does the reviewer's seam check apply to every new or changed test in the diff, or only to new tests?
- context: The approved intent (outcome 3) lists "a new test that does not sit at a declared seam" and keeps "Rewriting existing tests" out of scope. The approved design (Architecture, reviewer seam check) and the shipped prompt (`task-reviewer-prompt.md:64`) say "each new or changed test". So a task that edits one line of an old test can get an Important finding for that test and be pushed to rewrite it. Shipping is blocked until the intent oracle and the prompt agree.
- options:
  - A) Only new tests. Change the reviewer prompt to "Check each new test in the diff." (and the search allowance line to "each new test file"). An edited old test is not checked. Matches the intent text and its out-of-scope line. Recommended.
  - B) New and changed tests, as the design and prompt say now. Amend intent outcome 3 and re-pin it. A task that touches an old test must bring that test to the seam rules.
  - C) New tests fully; for a changed test, check only the lines the task changed (steps 2 and 3, not step 1). Amend intent and the prompt; more nuance for the reviewer to apply.
- default_if_no_response: BLOCK
- decision: A — only new tests. The reviewer prompt says "Check each new test in the diff." and the unmarked-plan search allowance is "one search for each new test file". An edited old test is not checked.
- decided_by: Minh Tran (chat reply "A")
- decided_at: 2026-10-16
