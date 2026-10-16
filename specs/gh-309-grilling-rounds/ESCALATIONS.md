# gh-309-grilling-rounds — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: orchestrator (Task 3.1, blind run)
- date: 2026-10-16
- trigger: plan budget reached (two reruns used) with criterion (a) still failing on the literal count
- question: How is `Rounds: <n>` counted for SC-5, and is a fourth blind run allowed?
- context: Three blind runs were made on the #318 fixture (transcripts in `blind-run.md`).
  - Run 1 (text at `84db611`): 2 rounds, 16 questions, no fact question, the evaded decision recorded as an assumption. **(d) failed**: the agent declared step 2 ended without a confirmation turn, because the last round held one evasion and the text said "the yes to the last round counts". Fixed in `91d45b1`: "A plain 'yes' to the whole last round is that confirmation. Otherwise ask for it."
  - Run 2 (text at `91d45b1`): the question frontier closed in 2 rounds; the agent then asked for confirmation (round 3). The user agent answered "No" and named four key rows it had not been asked (scope of six phases, 600-word budget, Phase 1 stop rule, debug-tag format). All four are stated verbatim in the issue body, and the agent had treated them as settled prerequisites, as the procedure says. Round 4 asked them, round 5 confirmed. **Total 5 rounds; (d) passed; (c) not exercised** (the evade marker sat on a decision the issue also states, so it was never asked).
  - Key revised (v2) per `docs/solutions/harness/skill-eval-blind-run-scoring.md` ("when runs consistently disagree with a fixture, suspect the answer key"): the four rows marked settled-by-the-issue, the evade marker moved to the gate decision.
  - Run 3 (text at `91d45b1`, key v2): the question frontier closed in 2 rounds; the evaded decision was recorded as an assumption; the agent asked for confirmation (round 3). The user agent again named four unasked rows (invocation flag, redaction placement, #313 dependency, Phase 3 blocking), all four also stated in the issue body and missed by the key revision. Round 4 asked them, round 5 confirmed. **Total 5 rounds; (b), (c), (d) passed.**
  - In all three runs the skill's own behavior was the same: every open decision asked in 2 rounds, facts looked up, confirmation requested (after the fix), evasions handled. The extra rounds in runs 2 and 3 came only from the fixture's rule 6, which made the user agent demand explicit questions on decisions the issue text already settles.
- options:
  - A) Count `Rounds:` as the rounds of new questions until the agent first declares the frontier empty and asks for confirmation (2 in every run). This matches the issue's measure ("the frontier closes in three rounds or fewer") and design criterion (a) ("the frontier is empty in three rounds or fewer"). Record the total turn count (5) beside it in `blind-run.md` and in SUMMARY `### Not auto-verified`. SC-5 then passes on Run 3 as written. No code or text change. Recommended.
  - B) Count every round, including confirmation re-asks (5). Run 3 fails (a). Allow one more blind run (a fourth, beyond the plan's two-rerun budget) with a key that marks every issue-stated row as settled, and score that run.
  - C) Count every round and stop: record SC-5 as failed, do not ship.
- default_if_no_response: BLOCK
- decision: A — `Rounds:` counts the rounds of new questions until the agent first declares the frontier empty and asks for confirmation (2 in every run); the total turn count (5) is recorded beside it in `blind-run.md` and in SUMMARY `### Not auto-verified`. SC-5 is scored on Run 3. No code or text change.
- decided_by: Minh Tran (chat reply "A")
- decided_at: 2026-10-16
