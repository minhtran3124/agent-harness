# gh-309-grilling-rounds — Design

Written 2026-10-16. Pins: repo 2bc2cb2
Revised 2026-10-16. Pins: repo c76a485 + uncommitted

## Goal

Rewrite step 2 of `skills/brainstorming/SKILL.md` so the agent asks the whole frontier of a design
tree in one numbered round, with a recommended answer per question, finds facts itself, and acts
only after the user confirms a shared understanding. The same questions then land in about three
rounds instead of one round per question.

## Current state

- `skills/brainstorming/SKILL.md` is 442 words (measured 2026-10-16 `wc -w`); the ceiling is 600
  (budget, `scripts/audit_skill_prompts.py`). Step 2 is 64 words (measured 2026-10-16 `wc -w`,
  lines 22–26).
- Step 2 says "Ask one clarifying question per message", "Do not over-probe: steps 3–4 still catch
  any gap", "If a question goes unanswered or evasive twice, name the gap and move on", and the
  visual-artifact sentence.
- No test, hook, eval, rule or script pins the step-2 wording. A grep for "clarifying question"
  and "evasive" over `skills/`, `rules/`, `hooks/`, `scripts/`, `tests/` and `evals/` finds only
  `skills/brainstorming/SKILL.md` and an unrelated xia2 pressure scenario
  (`skills/xia2/tests/behavioural/pressure-scenarios.md:104`).
- `scripts/ste-baseline.json` pins one STE finding for `skills/brainstorming/SKILL.md`.
- The source procedure is Pocock's `grilling/SKILL.md` (design tree, frontier, one round, recommended
  answer, facts by subagent, decisions by user, stop when the frontier is empty) at
  mattpocock/skills commit `49dd158`, `skills/productivity/grilling/SKILL.md` (clone tip read 2026-10-16; issue #309 cites the
  file without a commit).

## Approaches considered

| | Approach | For | Against |
|---|---|---|---|
| A (chosen) | Write the procedure inline in step 2, one paragraph of 169 words (measured 2026-10-16 `wc -w`) | The model reads it on every run; no new file; no Read step | Step 2 is longer than the other steps |
| B | Short step 2 plus `references/grilling-rounds.md` | Skill stays short | A reference is read only on an explicit Read step; a new file enters the STE baseline; #308 showed pointer sentences attract intent-review drift findings |
| C | Step 2 as sub-steps 2a–2g, one behavior per line | Easy to map to the seven behaviors | More words than A; breaks the rhythm of the other five steps |

## Architecture

One skill file changes: `skills/brainstorming/SKILL.md`, step 2 only. The new text (169 words,
measured 2026-10-16 `wc -w` on the draft):

```text
2. Map the open decisions as a design tree. The tree holds purpose, constraints, success
   criteria, and boundaries. Approach choice belongs to step 3; section detail belongs to
   step 4. The frontier is each decision whose prerequisites the user already settled. Ask the
   whole frontier in one numbered round. Give a recommended answer for each question, worded
   so that "yes" accepts it. Then wait. Facts are your job: find each one yourself, or
   dispatch a subagent when the search is larger than a few reads; never ask the user for a
   fact. Decisions are the user's: put each to them and wait. If a decision goes unanswered or
   evasive twice, name the gap, record the recommended answer as an assumption, and move on.
   Repeat with the new frontier. Step 2 ends when the frontier is empty and the user confirms a
   shared understanding; the "yes" to the last round counts. Act only after that. Use a visual
   artifact only when seeing the answer is materially clearer than reading it.
```

Map to the seven behaviors in `intent.md`: (1) tree and tier boundary, sentences 1–3; (2)
frontier, sentence 4; (3) one numbered round, sentence 5; (4) recommended answer and "yes",
sentence 6; (5) facts, sentence 8; (6) decisions to the user, sentence 9; (7) stop and
confirmation, sentences 12–13. The evasive rule is sentence 10, for decisions only. The
visual-artifact sentence is unchanged. Steps 1 and 3–6, the HARD-GATE, the design constraints,
`references/design-template.md` and `references/spec-review-loop.md` do not change.

Predicted skill length after the change: 547 words (prediction; 442 − 64 + 169).

The old sentence "Do not over-probe: steps 3–4 still catch any gap through approach trade-offs
and per-section confirmation" is removed whole. Its condition words `any` and `still` are
replaced by the tier boundary (sentences 2–3) and the stop condition (sentence 12); the
replacement will be cited in `specs/gh-309-grilling-rounds/qualifiers-brainstorming.md`, a plan
output.

The prose follows `skills/asd-ste100/SKILL.md`: short sentences, one instruction per sentence,
active voice, approved words. The STE lint is a Verify row.

### Blind run

A blind run proves the text before merge. It uses two subagents and the orchestrator as relay:

- **Grilling agent.** Receives the HARD-GATE, the new step 2 only (not the whole skill, so it does
  not run step 1), and issue #318's body as the design question. Instruction: run step 2 with the
  user played by a relay; stop at the end of step 2; print the transcript.
- **User agent.** Receives a hidden answer key of 10–13 decisions (budget) on #318, written by the
  orchestrator before the run and never shown to the grilling agent. Instruction: answer only what
  is asked, add nothing; for one named decision, give an evasive answer twice; for any fact,
  answer "I do not know; find it yourself".
- **Relay.** The grilling agent cannot spawn the user agent, so the orchestrator is the relay.
  Each round: the grilling agent ends its turn with the numbered round; the orchestrator sends
  the round to the user agent with `SendMessage` and receives the answers; the orchestrator sends
  the answers to the grilling agent with `SendMessage`, which continues from its own context. One
  round is two message pairs. Neither agent sees the other's prompt.
- **Facts.** The grilling agent has Read, Grep and Glob but no nested dispatch, so the run
  exercises only "find each one yourself"; the subagent half of behavior 5 is not exercised (see
  What we do not claim).
- **Record.** `specs/gh-309-grilling-rounds/blind-run.md` holds the design question, the answer
  key, the transcript, and the scoring table.

## Error behavior

- Blind run takes more than three rounds (budget), or asks a fact or an implementation-level
  question in step 2: edit the text and rerun. At most two edit-and-rerun cycles (budget); then
  raise an `ESCALATIONS.md` entry.
- A subagent cannot be continued or gives no reply to `SendMessage`
  (`docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`): start a fresh agent
  of the same role with the full transcript so far replayed in its prompt, and continue the round.
  Note the restart in `blind-run.md`.
- Grilling agent asks a fact: the user agent refuses; criterion (b) fails.
- Skill over 600 words after an edit: apply
  `docs/solutions/harness/deletion-test-for-word-ceiling.md`.
- No real brainstorming session exists after merge: the live round count is listed in
  `SUMMARY.md` `### Not auto-verified` as an accepted risk (A4), reached by no check.

## Tests

| Check | Command | Tier |
|---|---|---|
| Word ceiling | `python3 scripts/audit_skill_prompts.py` (exit 1 over 600 words) | truth |
| STE lint | `python3 scripts/check_ste_baseline.py --strict --against 996f50d` (no new WARN against the base-branch baseline) | traceability |
| Condition words | `python3 scripts/check_scope_qualifiers.py --base 996f50d --head HEAD`, every listed word resolved in `qualifiers-brainstorming.md` | truth plus reviewer meaning verdict |
| Blind run | transcript and scoring table in `blind-run.md`; criteria (a)–(d) below | provenance, one run scored by hand, marked "(assumed)" |
| Suite | `bash scripts/run-tests.sh` | truth |
| Propagation | context-propagation-audit on the diff | provenance |

Blind-run criteria: (a) the answer key holds 10–13 decisions (budget) and the frontier is empty
in three rounds or fewer (budget); (b) no step-2 question is a fact or an implementation-level
choice; (c) the evaded decision is recorded as an assumption; (d) the grilling agent declares
step 2 ended only after the user agent's confirmation, and not before.

Amended by DC1 (see Decision changes): (a) counts rounds of new questions until the agent first
declares the frontier empty (`ESCALATIONS.md` E001); (b) is the fact half only, and the count of
approach-level or implementation-level questions per run is recorded as an advisory measure.

## Success criteria

- SC-1: step 2 states each of the seven behaviors; checked by the seven-sentence map above and
  the task reviewer's spec verdict.
- SC-2: `skills/brainstorming/SKILL.md` is under 600 words; checked by `audit_skill_prompts.py`.
- SC-3: STE lint reports no new WARN against the `996f50d` baseline; checked by
  `check_ste_baseline.py --strict --against 996f50d`.
- SC-4: every condition word the qualifier check lists is cited as kept or replaced; checked by
  `qualifiers-brainstorming.md` and the reviewer.
- SC-5: the blind run passes criteria (a)–(d); checked by `blind-run.md` (assumed measure).
- SC-6: no other file under `skills/brainstorming/` changes; checked by `git diff --stat`.

## Non-goals

- A question cap or a fixed number of rounds.
- A fixed question template or emoji.
- A design-tree field in `design.md`; the tree lives in the conversation.
- A test that greps the step-2 wording.
- Changes to `feature-intake`, `xia2`, `writing-plans`, the normal lane's notify-and-proceed
  flow, or any hook.
- A separate `grilling` skill.
- Brainstorming for #318; the blind run borrows its question and binds nothing.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | No file outside `skills/brainstorming/SKILL.md` pins the step-2 wording | provenance: Local, 2026-10-16, grep over skills/ rules/ hooks/ scripts/ tests/ evals/ | SC-6 and `bash scripts/run-tests.sh` | A test breaks; update the pin in the same task |
| A2 | Issue #318's body yields 10–13 decisions (budget) that can be asked without a prerequisite from outside the issue | none yet: Inference from the issue's eight design items and three proof items | SC-5 criterion (a), answer-key step of the blind-run task | Pick #313 or #312 as the question instead |
| A3 | A subagent given only step 2 and the HARD-GATE follows the procedure without the rest of the skill | none yet: Inference | SC-5 | Give it the whole skill and tell it step 1 is done |
| A4 | A blind run on a fixture question predicts live behavior | none yet: Inference; the issue's proof is a live session | accepted risk: the live count is listed in `### Not auto-verified` until the first real session | The first real session exceeds three rounds; open a follow-up issue |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| A real brainstorming session closes in three rounds | Only a blind run on a fixture is measured before merge |
| The agent never asks a fact | The text says so; only the blind run checks it, once |
| The subagent half of behavior 5 (dispatch when the search is large) works | The grilling agent in the blind run has no nested dispatch; only "find it yourself" is exercised |
| Rounds are cheaper in tokens | Not measured; the issue measures rounds, not tokens |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Proof is a blind run before merge plus the first real session after merge | `blind-run.md` is a plan task; live count goes to `### Not auto-verified` | settled |
| D2 | Facts: find yourself, or dispatch a subagent when the search is larger than a few reads | Intent amended and re-pinned at 2bc2cb2 | settled |
| D3 | No fixed question template or emoji; numbered plus a recommended answer | Fewer words; STE-friendly | settled |
| D4 | Replace "Do not over-probe…" with a tier boundary and a stop condition (frontier empty plus user confirmation) | The tree is bounded at the requirements tier; `any`/`still` cited as replaced | settled |
| D5 | Evasive rule applies to decisions only; after two evasions record the recommended answer as an assumption | Facts are never evaded, they are found | settled |
| D6 | Only step 2 changes; no design-template field; no wording test | One hunk in one skill file; spec files and a possible `ste-baseline.json` update are the only other changes | settled |
| D7 | Blind-run question is issue #318's body | Answer key is written on #318; the run binds nothing for #318 | settled |
| D8 | User agent has a hidden answer key, answers only what is asked, evades one decision twice, refuses facts | Criteria (b) and (c) are testable | settled |
| D9 | Scoring is manual on the transcript, four criteria, recorded in `blind-run.md` | One Verify row | superseded by DC1 |
| D12 | Scoring is manual on the transcript, four criteria as amended: (a) rounds of new questions until the frontier is first declared empty, ≤3 (budget); (b) no step-2 question asks the user for a fact, with the approach- or implementation-level question count recorded as advisory; (c) and (d) unchanged | SC-5 is scored on the last run under these criteria; a follow-up issue owns the tier boundary | settled |
| D10 | Blind run is a plan task right after the rewrite task, before the review chain | Review sees the evidence | settled |
| D11 | Approach A: inline prose in step 2 | Skill predicted at 547 words | settled |

## Decision changes

- DC1 — 2026-10-16 — reopens D9 — evidence: three blind runs (`blind-run.md`) asked 3 of 16, 4 of 19 and 5 of 19 questions at approach or implementation level despite the tier-boundary sentence, while every run closed the question frontier in 2 rounds and asked no fact; `ESCALATIONS.md` E001 (round counting) and E002 (criterion (b)), both decided by the user — new decision: D12
