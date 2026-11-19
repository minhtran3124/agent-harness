# Feature lane brief

> Kept as the record of the trials of ADR 0039 and ADR 0040. New runs use `/harness:pd-orchestrate`
> and the `pd-work` skill (ADR 0041); do not send this brief.

The brief that the free workers of the feature-lane trial got (ADR 0040). It is not yet the default
way to run a feature ticket: `ship.js` stays the default until a second trial with UAT and a depth L
ticket confirms the result. Replace each `<...>` before sending. Put the brief in a gitignored file in
the worker's checkout (for example `specs/trial/brief.md`), not next to anything the worker must not
read, such as hidden acceptance tests.

Rules for the orchestrator are the same as in the bug lane: route the review to a different session,
and check the worker's claims (tests, full suite) before you report a ticket done.

---

Feature ticket `<id>` for you to build in this checkout (local only, no push).

Checkout: `<path>`
Base: `<base>`. Work on a local branch `feature/<id>`.
Run id: `<run id>`
Owner: the human owner answers your questions in this session (use AskUserQuestion); they may take a
while.

TICKET `<id>`
`<ticket text>`

Steps (do every step that applies, in order; the harness skills and agents named here are installed):

1. Intake: run the `harness:pd-intake` skill on the ticket. Write its verdict (READY | CONFIRM | GRILL |
   BLOCKED) and depth (S | M | L) into `specs/<id>/intent.md`. If the verdict is CONFIRM or GRILL, ask
   the owner (for GRILL use the `harness:pd-grilling` skill) and wait for the answers before you go on;
   write them into `specs/<id>/decision.md`. If BLOCKED, stop and report.
2. Design (depth L only): use the `harness:pd-brainstorming` skill; write `specs/<id>/design.md`.
3. Plan: use the `harness:pd-writing-plans` skill; write `specs/<id>/plan.md`.
4. Acceptance tests (depth M and L): have the `harness:qa-writer` agent write blind acceptance tests
   from the ticket and its acceptance criteria only, before any code. Commit them first.
5. Implement: use the `harness:pd-implement` skill (one implementer subagent per plan step, each in its
   own worktree). Run the full suite `bash scripts/run-tests.sh` and keep the output.
6. Security review: if the ticket is risky (deletion, releases or other irreversible actions,
   secrets, auth, permissions), have the `harness:security-reviewer` agent review the change before
   handoff; address its findings.
7. Code review and intent review: send a message to the session `<orchestrator session>` with the
   ticket id, the checkout path and a short summary. Another session does the review; do not review
   your own change. Wait for the result and address any finding.
8. Acceptance check: for a ticket with a running app or server (FE or BE), run the `harness:pd-uat`
   skill against the running app; for a ticket with no app at depth M or L, have the
   `harness:qa-verifier` agent check it.
9. Decisions: record each decision you made on your own (the `harness:pd-decision-record` skill); an
   early decision with a real trade-off gets an ADR file through its script.
10. Instead of a PR: commit on the local branch `feature/<id>`. Do not push, do not open a PR, do not
    touch main, never merge, never force-push.
11. Report: write `specs/<id>/report.md` (specs/ is gitignored, do not commit it). It starts with the
    line `<!-- harness-fleet:report v1 -->` followed by one JSON object with these fields: v (1), run,
    ticket, reported_by ("worker" or "orchestrator"), status ("done" | "failed" | "blocked" |
    "needs_owner"), head (commit sha or null), gates (each step above and its result, or why it did
    not apply), error (null, or {code, stage, message, evidence: {command, exit_code, output_tail},
    attempts, retryable}), next ("retry" | "reassign" | "ask_owner" | "skip_dependents" | "none"),
    decisions (list of decisions you made on your own).
    Error codes: BRIEF_INVALID, STAGE_BLOCKED, GATE_FAILED, TEST_FAILED, CI_FAILED, MERGE_DENIED,
    FORGE_ERROR, REPRO_NOT_FAILING, PERMISSION_WAIT, NO_RESPONSE, MACHINE_OFFLINE.
    Write `status: "done"` only after the review result has arrived and every finding is addressed or
    answered. Before that, the status is `blocked` with error code NO_RESPONSE.
    Then send the same report text to `<orchestrator session>`.

If a step cannot be done, say so in the report with evidence instead of guessing.
