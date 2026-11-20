# Bug lane brief

> Kept as the record of the trials of ADR 0039 and ADR 0040. New runs use `/harness:pd-orchestrate`
> and the `pd-work` skill (ADR 0041); do not send this brief.

The orchestrator sends this brief to one free Pod Bay worker session per bug ticket (ADR 0039). The
worker gets only this text, its ticket and its branch. Replace each `<...>` before sending. Send the
steps once; do not tell the worker how it is scored.

Two rules for the orchestrator (ADR 0039):
- Route the review to a different session, and send its result to the worker.
- Before you report a ticket done, rerun the worker's new test on the base branch (it must fail
  there) and run the full suite on the worker's branch. A report is the worker's own claim.

---

Bug ticket `<id>` for you to fix in this checkout (local only, no push).

Checkout: `<path>`
Branch: `<branch>` (already checked out)
Run id: `<run id>`

TICKET `<id>`
`<ticket text>`

Steps (do all of them, in order):

1. Reproduce: write a test that FAILS on `<branch>` because of this bug. Run it and keep the output.
2. Fix: make that test PASS. Then run the full suite: `bash scripts/run-tests.sh`. Keep the output.
3. Hand off for code review and intent review: send a message to the session `<orchestrator session>`
   with the ticket id, the checkout path and a short summary of the change. Another session does the
   review; do not review your own change. Wait for the review result and address any finding.
4. Instead of a PR: create a local branch `fix/<id>` from `<branch>` in this checkout and commit there.
   Do not push, do not open a PR, do not touch main, never merge, never force-push.
5. Write a report file at `specs/<id>/report.md` (specs/ is gitignored, do not commit it). The file
   starts with the line `<!-- harness-fleet:report v1 -->` followed by one JSON object with these
   fields: v (1), run, ticket, reported_by ("worker" or "orchestrator"), status ("done" | "failed" |
   "blocked" | "needs_owner"), head (commit sha or null), gates (the checks you ran and their result),
   error (null, or {code, stage, message, evidence: {command, exit_code, output_tail}, attempts,
   retryable}), next ("retry" | "reassign" | "ask_owner" | "skip_dependents" | "none"), decisions
   (list of decisions you made on your own).
   Error codes: BRIEF_INVALID, STAGE_BLOCKED, GATE_FAILED, TEST_FAILED, CI_FAILED, MERGE_DENIED,
   FORGE_ERROR, REPRO_NOT_FAILING, PERMISSION_WAIT, NO_RESPONSE, MACHINE_OFFLINE.
   Write `status: "done"` only after the review result has arrived and every finding is addressed or
   answered. Before that, the status is `blocked` with error code NO_RESPONSE.
   Then send the same report text to `<orchestrator session>`.

If a step cannot be done, say so in the report with evidence instead of guessing.
