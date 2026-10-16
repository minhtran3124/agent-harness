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
- correction (2026-10-16, after the Task 3.1 review): the context above says the four rows the user agent named in run 3 were "all four also stated in the issue body". That is true for K3, K5 and K6 only. K9-blocking (wait for the user on the ranked hypotheses, or not) is marked open in key v2, so in run 3 the agent declared the frontier empty with one open decision left. The decision text is unchanged; E002 asks whether it still holds.

---

## E002

- raised_by: orchestrator (Task 3.1 review, two Important spec findings)
- date: 2026-10-16
- trigger: SC-5 cannot be claimed; the plan's two-rerun budget is used
- question: Criterion (b) fails in run 3 on its implementation-level half, and E001 rested on a wrong premise for one row. Which way forward?
- context:
  - Design criterion (b): "no step-2 question is a fact or an implementation-level choice". The fact half passes in every run. The implementation-level half fails in every run: run 1 asked 3 of 16 questions at approach or implementation level, run 2 4 of 19, run 3 5 of 19 (listed in `blind-run.md`). Examples: write in-house vs vendor (an approach choice, step 3 by the design's own tier boundary), the frontmatter field `disable-model-invocation: true`, bash lint plus red/green tests for a script. The step-2 text already says "Approach choice belongs to step 3. Section detail belongs to step 4." The model mixes tiers anyway, on this fixture.
  - E001 premise: K9-blocking was an open row in key v2 and the run-3 agent missed it before declaring the frontier empty (round 3). The other three rows named by the user agent are issue-stated. Under decision A, `Rounds:` is still 2; the miss is a correctness note on the "frontier empty" claim, not on the count.
  - Open decisions in key v2: 8 of 12 rows, below the 10–13 budget of criterion (a) and assumption A2.
  - The user-visible point of the issue (ask the frontier in rounds, not one per message; ~3 rounds instead of ~13) held in all three runs: 2 rounds of questions each time, 16–19 questions, facts looked up, evasions handled, confirmation asked after the `91d45b1` fix.
- options:
  - A) Narrow criterion (b) to its fact half by a design decision change (`DC1` reopening the Tests criterion): "no step-2 question asks the user for a fact". Record the implementation-level count per run in `blind-run.md` as an advisory measure, and open a follow-up issue to tighten the tier boundary (for example an explicit "Do not ask how to implement or test; that belongs to steps 3–4") with its own blind run. Confirm that E001 decision A stands on the corrected premise. SC-5 then passes on run 3. Recommended: the three runs give the same answer, a fourth run would re-measure a known tendency, and the issue's own proof is the round count.
  - B) Keep (b) as written. Allow a fourth blind run, beyond the plan budget, with the step-2 text tightened as in A and a key that marks every issue-stated row as settled and leaves at least 10 open rows (a different fixture, or #318 plus added open decisions). Score that run; ship only if (a)–(d) all pass.
  - C) Keep (b) as written and stop: SC-5 fails, the branch does not ship.
- default_if_no_response: BLOCK
- decision: A — narrow criterion (b) to its fact half by design DC1 (D9 superseded by D12); record the implementation-level question count per run as an advisory measure; open a follow-up issue to tighten the tier boundary with its own blind run (opened as #321, milestone Mattpocock Learning); E001 decision A stands on the corrected premise. SC-5 is scored on run 3.
- decided_by: Minh Tran (chat reply "A")
- decided_at: 2026-10-16
