# gh-309-grilling-rounds — Blind run of the new step 2

Proof for SC-5 (design D1, D7–D10), marked "(assumed)": one fixture question, a hidden answer key,
a grilling agent (`Explore` type: Read, Grep, Glob, no nested dispatch) that got only the HARD-GATE,
the new step 2 and the issue body, a user agent that got only the key, and the orchestrator as relay.
Neither agent saw the other's prompt. The answer key was written in the scratchpad before each run
and copied here after the run ended. Three runs were made; the plan allows two reruns. The first
run stays unchanged. `check_gh309.py blindrun` scores the last run.

Rounds are counted per `ESCALATIONS.md` E001 (decision A): `Rounds:` is the number of rounds of
new questions until the agent first declares the frontier empty and asks for confirmation. The
total number of turns, including confirmation re-asks, is given beside it as `Turns:`.

The design question in every run is the body of issue #318 as of 2026-10-16:

> **Phase 2: verification spine.** Roadmap: https://claude.ai/artifact/AohXkjEsZKRDXhHheAsrtW
> 
> ## Goal
> 
> Add an in-repo bug-fix process: a `diagnosing-bugs` skill with six gated phases, wired into intake, the bug-fix lane, and compound.
> 
> ## The gap
> 
> - `skills/feature-intake/SKILL.md` classifies `Input-type: bug fix`, but it routes the work to no diagnosis step.
> - `skills/README.md` draws the bug-fix path as `systematic-debugging` (external) → fix → compound. The README calls the external skill optional. When it is absent, the agent reads code and guesses.
> - `rules/auto-correct-scope.md` and `implementer-prompt.md` require a red/green pair in `### Verify`. They say nothing about how to find the cause before the test.
> - No step minimises the repro, ranks hypotheses, tags instrumentation, or deletes it.
> 
> Pocock's `diagnosing-bugs/SKILL.md` (1,427 words) covers each of these steps. His docs page records three open problems with it. It fires too often on quick questions (his issue #578). It has no gate before the fix (#124). It can paste secrets (#674). The design below closes each one.
> 
> ## Design
> 
> 1. Create `skills/diagnosing-bugs/SKILL.md` with fewer than 600 words. Put the long lists in `references/`.
> 2. Make the skill user-invoked and chain-invoked, not model-invoked. `feature-intake` calls it for `Input-type: bug fix`. The user calls it with `/diagnosing-bugs`. This closes his issue #578.
> 3. Write six phases. Each phase ends with one completion criterion:
>    - **Phase 1, feedback loop.** Name one command that goes red on this bug. Run it at least once. Show the command and its output. Keep the loop fast, deterministic, and agent-runnable. If you cannot build a loop, stop, list what you tried, and ask the user for an environment, a captured artifact, or permission to instrument.
>    - **Phase 2, reproduce and minimise.** Make sure that the loop shows the symptom that the user described. Delete inputs one at a time until each remaining element is necessary.
>    - **Phase 3, hypothesise.** Write three to five ranked hypotheses. Each one states a prediction. Show the list to the user. Continue with your own ranking if the user is away.
>    - **Phase 4, instrument.** Map each probe to one prediction. Change one variable at a time. Tag each debug log with a unique prefix such as `[DEBUG-a4f2]`.
>    - **Phase 5, fix.** Hand off to the bug-fix lane in `rules/auto-correct-scope.md`. The implementer writes the failing test at a valid seam, commits it, then fixes. If no valid seam exists, record that as a finding in `SUMMARY.md`.
>    - **Phase 6, cleanup.** Re-run the Phase 1 loop. Grep the debug prefix and delete each tagged log. Delete throwaway harnesses. Name the confirmed hypothesis in the commit message and in the SUMMARY `Rationale`.
> 4. Add a redaction rule at the top of the skill. Replace each secret with `<REDACTED>` before you show a command or an output. This closes his issue #674.
> 5. Keep the per-task review of `subagent-driven-development` between Phase 4 and Phase 5. This closes his issue #124 with a gate the harness already has.
> 6. Write the diagnosis record to `specs/<slug>/diagnosis.md`: the loop command, the minimised repro, the ranked hypotheses, and the confirmed one. `compound` reads this file to preserve the root cause.
> 7. Copy `scripts/hitl-loop.template.sh` into `skills/diagnosing-bugs/scripts/` for the case where a human must act in the loop.
> 8. Update `skills/README.md`: replace the external `systematic-debugging` row and the bug-fix path with the new skill. Add the skill to the handoff map.
> 
> ## Lane
> 
> Expected lane: high-risk. The change adds a skill and edits `feature-intake` and `subagent-driven-development`, which trips the `workflow-engine` signal.
> 
> ## Dependencies
> 
> #308 (headroom in `feature-intake`). #313 supplies the prove-the-red assertion that Phase 5 relies on.
> 
> ## Proof
> 
> 1. Run the skill on one recorded bug from `docs/solutions/` with a known cause.
> 2. The issue passes when the transcript shows three things. A red loop exists before any hypothesis. A ranked list exists before any probe. The final diff has zero `[DEBUG-` tags.
> 3. Run a quick question through intake. The issue passes when the skill does not fire.
> 
> ## Source
> 
> Pocock, `skills/engineering/diagnosing-bugs/SKILL.md`, `docs/engineering/diagnosing-bugs.md`, and `scripts/hitl-loop.template.sh` at commit `49dd158`.

## Run 1

Step-2 text at `84db611`. Grilling agent: `Explore`. User agent: `Explore` with no file reads.

### Design question

Issue #318, quoted above.

### Answer key

| # | Decision | The user's answer | Note |
|---|---|---|---|
| K1 | Scope of the first version: all six phases, or a subset? | All six phases, but Phase 4 (instrument) may be short. | |
| K2 | Word budget: one SKILL.md under 600 words with `references/` for lists? | Yes. | |
| K3 | Invocation: user-invoked and chain-invoked only, never model-invoked? | Yes. `feature-intake` calls it for `Input-type: bug fix`. | |
| K4 | Where the diagnosis record lives | `specs/<slug>/diagnosis.md`. | |
| K5 | Redaction rule placement | At the top of the skill, before Phase 1. | |
| K6 | Relation to #313 (prove-the-red): depend on it, or ship Phase 5 without it? | Depend on it. #313 ships first. | |
| K7 | Gate between Phase 4 and Phase 5: the existing per-task review, or a new gate? | The existing per-task review of subagent-driven-development. No new gate. | |
| K8 | What happens when no feedback loop can be built in Phase 1 | Stop, list what was tried, ask the user for an environment, an artifact, or permission to instrument. | |
| K9 | Hypothesis count and ranking | Three to five, ranked, each with a prediction. Continue on own ranking if the user is away. | **EVADE TWICE.** First time: "Hmm, I am not sure that matters much." Second time: "Let us not get into that now." Third time asked (if any): answer plainly. |
| K10 | Debug-log tag format | A unique prefix like `[DEBUG-a4f2]`, grepped and deleted in Phase 6. | |
| K11 | `skills/README.md` change: replace the external `systematic-debugging` row? | Yes, replace it and add the skill to the handoff map. | |
| K12 | Proof: one recorded bug from `docs/solutions/` plus one quick question through intake? | Yes. Pass = red loop before any hypothesis, ranked list before any probe, zero `[DEBUG-` tags in the final diff, and the skill does not fire on a quick question. | |

Facts (never answer these; say "I do not know; find it yourself"): anything about what files exist
in the repository, what `feature-intake` currently says, what `rules/auto-correct-scope.md` says,
the current word count of any skill, what Pocock's skill says.

### Transcript

#### Round 1

**Grilling agent:**

ROUND 1

1. Should `diagnosing-bugs` run for every `Input-type: bug fix`, in every lane (tiny, normal and high-risk)? Today intake applies the red/green rule to "any lane, `Input-type: bug fix`".
   Recommended: Yes. Intake routes every bug fix through `diagnosing-bugs` first, in all three lanes, and then continues to the lane route.

2. Must the skill be hard-blocked from model invocation with `disable-model-invocation: true`, as `skills/session-retro/SKILL.md` is? That flag also blocks the Skill tool. So `feature-intake` cannot call the skill by name. It must tell the agent to load `skills/diagnosing-bugs/SKILL.md` by path.
   Recommended: Yes. Set `disable-model-invocation: true`. Intake loads the skill by file path. Users run `/diagnosing-bugs`. Closing #578 needs the block. A narrower description alone is not enough.

3. Should this issue remove `systematic-debugging` from `skills/README.md` completely? That means the External Skills table, the Bug Fix Path, and the handoff-map line. The alternative is to keep it as an optional fallback.
   Recommended: Yes. Remove it everywhere in `skills/README.md` and keep no fallback, so that there is one diagnosis path.

4. In Phase 3, should showing the ranked hypotheses to the user be non-blocking? (The agent shows the list and continues with its own ranking. The only hard gate before the fix stays the per-task review.)
   Recommended: Yes. Phase 3 shows the list and does not wait. The pre-fix gate is the review gate alone.

5. Should the redaction rule cover every persisted artifact as well as chat output? That means `diagnosis.md`, `SUMMARY.md` Verify rows, commit messages, and the `docs/solutions/` record that compound writes.
   Recommended: Yes. Replace each secret with `<REDACTED>` in chat output and in every file or commit that the skill or its handoffs write.

6. When Phase 5 finds no valid test seam, should it use the existing `Red test exempt: <reason>` line in `### Verify` instead of a new kind of SUMMARY finding? `rules/auto-correct-scope.md` and `implementer-prompt.md` already define that line.
   Recommended: Yes. Use `Red test exempt: <reason>`. The reason names the missing seam, and the `Rationale` repeats it. Add no new finding format.

7. Is a `compound` edit in scope? The edit makes `compound` read `specs/<slug>/diagnosis.md` and copy the confirmed hypothesis into the bug record's root cause. The issue's Goal says "wired into … compound", but its eight design items do not edit `compound`.
   Recommended: Yes. Include a small `compound` edit: when `diagnosis.md` exists, compound uses it as the source for the root cause and the minimised repro.

8. Should `hitl-loop.template.sh` be vendored with an `UPSTREAM.md` that records Pocock's repo and commit `49dd158`, as `skills/asd-ste100/` does? (The script does not exist in this repository yet.)
   Recommended: Yes. Vendor it to `skills/diagnosing-bugs/scripts/` and add `skills/diagnosing-bugs/UPSTREAM.md` with the source path and commit. Only the script is vendored. `SKILL.md` stays in-house, so the 600-word ceiling still applies to it.

9. Must #308 and #313 merge before this issue starts, with no part of their work done here? `feature-intake/SKILL.md` has 539 of its 600 words now. `scripts/run_at_commit.py` already exists.
   Recommended: Yes. Both are hard prerequisites and out of scope. This issue starts only after both are merged.

10. For Proof 1, should the recorded bug be `docs/solutions/harness/gate-config-must-read-index.md`? It is a `problem_type: bug` record with a known root cause and a named regression test.
    Recommended: Yes. Use that record. Run the skill on the pre-fix commit, and pass only if the confirmed hypothesis matches the recorded root cause.

11. Should Proof 3 test a quick question asked directly in a fresh session, with no intake? (Intake runs on change requests, so a quick question usually never reaches it.) The pass condition would be that `diagnosing-bugs` does not load.
    Recommended: Yes. Proof 3 has two cases, and the skill must not load in either: (a) a quick bug question asked directly in a fresh session, and (b) a quick question sent through intake that intake does not classify as `bug fix`.

WAITING FOR ANSWERS

**User agent:**

1. yes
2. yes. User-invoked and chain-invoked only, never model-invoked; `feature-intake` calls it for `Input-type: bug fix`.
3. yes. Replace the `systematic-debugging` row with this skill and add the skill to the handoff map.
4. Hmm, I am not sure that matters much.
5. (not in key) Yes. Replace secrets with `<REDACTED>` in chat output and in every artifact the skill or its handoffs write.
6. (not in key) Yes. Use the existing `Red test exempt: <reason>` line and add no new finding format.
7. (not in key) No. Leave `compound` unchanged in this issue.
8. (not in key) No. Do not vendor the script in this issue.
9. yes. Depend on #313, which ships first.
10. Use one recorded bug from `docs/solutions/`, but the pass condition is: a red loop before any hypothesis, a ranked list before any probe, and zero `[DEBUG-` tags in the final diff.
11. No. Test only one quick question sent through intake; it passes if the skill does not fire.

#### Round 2

**Grilling agent:**

ROUND 2

1. (Asked again; the round 1 answer was unclear.) In Phase 3, does the agent show the ranked hypotheses and continue without waiting for the user, so that the only gate before the fix is the per-task review?
   Recommended: Yes. Phase 3 shows the list and does not wait. The gate before the fix is the review gate alone.

2. Is #308 (headroom in `feature-intake`) also a prerequisite that must merge first, or does this issue depend only on #313? Today `skills/feature-intake/SKILL.md` has 539 of its 600-word ceiling, and the new routing line must fit in what is left.
   Recommended: Yes. #308 is also a prerequisite that ships before this issue. That keeps the intake edit clear of the ceiling.

3. `compound` stays unchanged. Should the skill still write `specs/<slug>/diagnosis.md` (the loop command, the minimised repro, the ranked hypotheses, the confirmed one) as the durable diagnosis record?
   Recommended: Yes. Keep `diagnosis.md`. Nothing in this issue reads it automatically. It is the evidence for the review gate and for the commit and `Rationale`.

4. The skill runs in all lanes (round 1, Q1). The tiny lane has no `subagent-driven-development` and so no per-task review. Is the gate before the fix in a tiny-lane bug fix that `diagnosis.md` is committed and shown to the user before the fix starts, with no extra reviewer?
   Recommended: Yes. In the tiny lane, Phase 4 ends with `diagnosis.md` committed and shown, and the agent then fixes. In the normal and high-risk lanes, the existing per-task review is the gate.

5. `hitl-loop.template.sh` is not vendored. Is the human-in-the-loop case covered only by the Phase 1 stop rule (list what you tried, and ask the user for an environment, a captured artifact, or permission to instrument), with no script and no reference text on HITL loops?
   Recommended: Yes. Rely only on the Phase 1 stop rule. Design item 7 is out of scope.

WAITING FOR ANSWERS

**User agent:**

1. Let us not get into that now.
2. (not in key) Yes. #308 is also a prerequisite and merges before this issue starts.
3. yes. The record lives at `specs/<slug>/diagnosis.md`.
4. (not in key) Yes. In the tiny lane, commit `diagnosis.md` and show it to the user before the fix, with no new reviewer.
5. yes. Stop, list what was tried, and ask the user for an environment, an artifact, or permission to instrument.

#### Close

**Grilling agent:**

STEP 2 ENDED

Gap: the user did not answer Phase 3 (round 1, Q4 and round 2, Q1) in either round. That question was whether the agent waits for the user after it shows the ranked hypotheses. I recorded the recommended answer as an assumption.

Settled decisions:
- Every `Input-type: bug fix` goes through `diagnosing-bugs`, in all three lanes (tiny, normal and high-risk).
- The skill is user-invoked and chain-invoked only, never model-invoked. It has `disable-model-invocation: true`. `feature-intake` calls it for `Input-type: bug fix` and loads it by file path. Users run `/diagnosing-bugs`.
- In `skills/README.md`, `diagnosing-bugs` replaces the `systematic-debugging` row and the bug-fix path. The skill is added to the handoff map, and no external fallback stays.
- Redaction: each secret becomes `<REDACTED>` in chat output and in every artifact that the skill or its handoffs write.
- No valid test seam: use the existing `Red test exempt: <reason>` line. Add no new finding format.
- `compound` stays unchanged in this issue.
- `hitl-loop.template.sh` is not vendored, so design item 7 is out of scope. The human-in-the-loop case relies only on the Phase 1 stop rule: stop, list what was tried, and ask the user for an environment, an artifact, or permission to instrument.
- Prerequisites: #308 and #313 both merge before this issue starts. No part of their work is done here.
- The skill writes the diagnosis record to `specs/<slug>/diagnosis.md`: the loop command, the minimised repro, the ranked hypotheses, and the confirmed one.
- Gate before the fix in the tiny lane: commit `diagnosis.md` and show it to the user before the fix, with no new reviewer. In the normal and high-risk lanes, the existing per-task review of `subagent-driven-development` is the gate.
- Proof 1: run the skill on one recorded bug from `docs/solutions/`. It passes when three things are true: a red loop exists before any hypothesis, a ranked list exists before any probe, and the final diff has zero `[DEBUG-` tags.
- Proof 3: send one quick question through intake. It passes if the skill does not fire. There is no direct fresh-session case.

Assumptions (recommended answers recorded because the user gave no answer):
- Phase 3 does not block. The agent shows the ranked hypotheses and continues with its own ranking. The only gate before the fix is the review gate: the per-task review in the normal and high-risk lanes, and the committed and shown `diagnosis.md` in the tiny lane.
- For Proof 1, the recorded bug is `docs/solutions/harness/gate-config-must-read-index.md` (`problem_type: bug`, known root cause). The user left the choice of bug open.

**Relay note:** no confirmation question was sent to the user agent, because the grilling agent declared the end without asking one.

### Scoring

Decisions: 12
Rounds: 2
Turns: 2
Questions: 16

| Criterion | Evidence | Result |
|---|---|---|
| (a) frontier empty in ≤3 rounds | Round 1: 11 questions. Round 2: 5 questions. STEP 2 ENDED after round 2. | pass |
| (b) no fact or implementation-level question in step 2 | All 16 questions are decisions with a recommendation; the agent looked up `feature-intake` word count, the `session-retro` flag, `run_at_commit.py` and a `docs/solutions/` bug record itself. | pass |
| (c) evaded decision recorded as an assumption | Round 1 Q4 and round 2 Q1 (Phase 3 blocking) evaded twice; the close lists it under "Assumptions". | pass |
| (d) step 2 declared ended only after the user's confirmation | The agent wrote STEP 2 ENDED directly after round 2, which held one evasion. No confirmation question was sent to the user. | fail |

Finding: the sentence "The \"yes\" to the last round counts as that confirmation" let the agent treat a mixed last round as confirmation. Fixed in `91d45b1`: "A plain \"yes\" to the whole last round is that confirmation. Otherwise ask for it."

Result: fail

## Run 2

Step-2 text at `91d45b1`. Grilling agent: `Explore`. User agent: `Explore` with no file reads.

### Design question

Issue #318, quoted above.

### Answer key

| # | Decision | The user's answer | Note |
|---|---|---|---|
| K1 | Scope of the first version: all six phases, or a subset? | All six phases, but Phase 4 (instrument) may be short. | |
| K2 | Word budget: one SKILL.md under 600 words with `references/` for lists? | Yes. | |
| K3 | Invocation: user-invoked and chain-invoked only, never model-invoked? | Yes. `feature-intake` calls it for `Input-type: bug fix`. | |
| K4 | Where the diagnosis record lives | `specs/<slug>/diagnosis.md`. | |
| K5 | Redaction rule placement | At the top of the skill, before Phase 1. | |
| K6 | Relation to #313 (prove-the-red): depend on it, or ship Phase 5 without it? | Depend on it. #313 ships first. | |
| K7 | Gate between Phase 4 and Phase 5: the existing per-task review, or a new gate? | The existing per-task review of subagent-driven-development. No new gate. | |
| K8 | What happens when no feedback loop can be built in Phase 1 | Stop, list what was tried, ask the user for an environment, an artifact, or permission to instrument. | |
| K9 | Hypothesis count and ranking | Three to five, ranked, each with a prediction. Continue on own ranking if the user is away. | **EVADE TWICE.** First time: "Hmm, I am not sure that matters much." Second time: "Let us not get into that now." Third time asked (if any): answer plainly. |
| K10 | Debug-log tag format | A unique prefix like `[DEBUG-a4f2]`, grepped and deleted in Phase 6. | |
| K11 | `skills/README.md` change: replace the external `systematic-debugging` row? | Yes, replace it and add the skill to the handoff map. | |
| K12 | Proof: one recorded bug from `docs/solutions/` plus one quick question through intake? | Yes. Pass = red loop before any hypothesis, ranked list before any probe, zero `[DEBUG-` tags in the final diff, and the skill does not fire on a quick question. | |

Facts (never answer these; say "I do not know; find it yourself"): anything about what files exist
in the repository, what `feature-intake` currently says, what `rules/auto-correct-scope.md` says,
the current word count of any skill, what Pocock's skill says.

### Transcript

#### Round 1

**Grilling agent:**

ROUND 1

1. Purpose and boundary: should `diagnosing-bugs` fully replace the external `systematic-debugging`? That means removing its row from the External Skills table and its line from the handoff map, so that no part of the harness refers to it.
   Recommended: Yes. Remove `systematic-debugging` from `skills/README.md` entirely. Leave the other external skills unchanged.

2. Trigger boundary: should intake send every `Input-type: bug fix` to diagnosis in every lane, tiny included?
   Recommended: Yes. Every bug-fix input in every lane runs diagnosis first. On a tiny bug, the Phase 1 loop can be the red test itself, so the extra cost stays small.

3. Invocation constraint: `disable-model-invocation: true` (already used in `skills/session-retro/SKILL.md`) stops the model from calling the skill through the Skill tool, and that includes `feature-intake` calling it. Should `diagnosing-bugs` set this flag, with `feature-intake` telling the agent to "read and follow `skills/diagnosing-bugs/SKILL.md`" instead of invoking it?
   Recommended: Yes. Set the flag. The intake route uses read-and-follow. `/diagnosing-bugs` stays the user entry point.

4. Position in the lane chain: should diagnosis run right after intake and before the lane route (before `brainstorming` for high-risk, and before `using-git-worktrees` for normal), with `diagnosis.md` as an input to the design and plan that follow?
   Recommended: Yes. The order is intake → diagnosing-bugs Phases 1–4 → lane route. Phase 5 is the lane's own implementation step.

5. Gate before the fix: the per-task review in `subagent-driven-development` reviews implementer diffs, not a diagnosis. It also does not run on the tiny lane. Should the gate before the fix be this instead: Phase 4 cannot end until `specs/<slug>/diagnosis.md` names one confirmed hypothesis and the probe output that confirmed it, and the SDD per-task reviewer (normal and high-risk) then checks the fix task against `diagnosis.md`?
   Recommended: Yes. Use the `diagnosis.md` completion criterion as the gate in all lanes. Add the `diagnosis.md` check to the per-task review only for normal and high-risk.

6. When no valid seam exists: should Phase 5 reuse the existing `Red test exempt: <reason>` line in `### Verify` instead of adding a new finding format in `SUMMARY.md`?
   Recommended: Yes. Reuse `Red test exempt: <reason>`, which `scripts/verify_summary.py` already accepts.

7. Redaction boundary: should the redaction rule be prose only (the rule at the top of the skill, plus a list of secret patterns in `references/`), with no new hook or script?
   Recommended: Yes. Prose and a reference list only. A new hook trips the `high-blast` block gate and is out of scope.

8. HITL script: `scripts/hitl-loop.template.sh` is not in this repo. It exists only upstream at Pocock commit `49dd158`. Should it be vendored into `skills/diagnosing-bugs/scripts/` with a source-and-commit attribution note (the way `skills/asd-ste100/UPSTREAM.md` does it)?
   Recommended: Yes. Vendor it with an `UPSTREAM.md` that names the source and the commit.

9. Proof bug: should the replay use `docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md` as the recorded bug with a known cause, run against the commit before its fix?
   Recommended: Yes. Use that record, because a script reproduces it deterministically and its cause is documented.

10. Proof that the skill does not fire on a quick question: should this be a new case in the existing intake eval (`scripts/run_intake_eval.py` / `scripts/score_intake_eval.py`) that asserts no diagnosis route for a non-bug question?
    Recommended: Yes. Add one negative case and one positive bug-fix case to the intake eval corpus.

11. Dependencies: should implementation wait until #308 (headroom in `feature-intake`, which is now at 539 of 600 words) is merged, while Phase 5 refers to the current advisory red/green check and picks up the #313 assertion when it lands?
    Recommended: Yes. Block on #308 only. Do not block on #313.

WAITING FOR ANSWERS

**User agent:**

1. Replace the `systematic-debugging` row with `diagnosing-bugs`, and add `diagnosing-bugs` to the handoff map.
2. yes
3. yes. The skill is invoked only by the user or by a chain, never by the model on its own, and `feature-intake` calls it for `Input-type: bug fix`.
4. (not in key) Yes. Run Phases 1–4 after intake and before the lane route.
5. Use the existing per-task review in subagent-driven-development, and add no new gate.
6. (not in key) Yes. Reuse the existing `Red test exempt: <reason>` line.
7. yes. Put the redaction rule at the top of the skill, before Phase 1.
8. (not in key) Do not vendor it. Leave it out of the first version.
9. yes
10. yes
11. Depend on #313. #313 ships first.

#### Round 2

**Grilling agent:**

ROUND 2

1. Tiny-lane gap from your answers to Q2 and Q5: the per-task review runs only inside `subagent-driven-development`, which handles the normal and high-risk lanes. A tiny-lane bug fix has no per-task review, so it reaches Phase 5 with no review of the diagnosis. Should a tiny-lane bug fix still run Phases 1–4 and then fix directly, with no review, so that the `diagnosis.md` record and the red/green rows are its only proof?
   Recommended: Yes. Tiny-lane bug fixes run Phases 1–4, write `diagnosis.md`, and patch directly with no added review. This adds no new gate.

2. What the per-task reviewer sees: for a bug-fix task, should the SDD per-task reviewer receive `specs/<slug>/diagnosis.md` in its review package, so that it can check that the fix addresses the confirmed hypothesis? This change only adds an input to the existing review. It does not add a gate.
   Recommended: Yes. Add `diagnosis.md` to the reviewer's inputs for `Input-type: bug fix` tasks. Do not add any new verdict.

3. Dependency on #308: `skills/feature-intake/SKILL.md` has 539 words now, and `scripts/audit_skill_prompts.py` enforces a 600-word ceiling. The new bug-fix route adds words to it. Should this work also wait for #308 (headroom in `feature-intake`), in addition to #313?
   Recommended: Yes. Depend on both #313 and #308, and ship both of them first.

WAITING FOR ANSWERS

**User agent:**

1. (not in key) Yes. Tiny-lane bug fixes run Phases 1–4, write `diagnosis.md`, and patch directly with no added review.
2. (not in key) Yes. Add `diagnosis.md` to the reviewer's inputs only, and add no new verdict.
3. (not in key) Yes. Depend on both #313 and #308, and ship both first.

#### Round 3

**Grilling agent:**

ROUND 3

1. Shared understanding: here is how I understand the design.
   - `diagnosing-bugs` replaces `systematic-debugging` in `skills/README.md` and appears in the handoff map.
   - Every bug-fix input, in every lane, runs Phases 1–4 after intake and before the lane route. The skill sets `disable-model-invocation: true`. `feature-intake` calls it for `Input-type: bug fix`, and the user can call it with `/diagnosing-bugs`.
   - The gate is the existing SDD per-task review, and no new gate is added. That reviewer also gets `diagnosis.md` as an input, with no new verdict. Tiny-lane fixes patch directly after Phases 1–4, with no added review.
   - When no valid seam exists, Phase 5 uses the existing `Red test exempt: <reason>` line.
   - The redaction rule is prose at the top of the skill, before Phase 1.
   - The HITL script is left out of v1.
   - Proof replays `deploy-harness-does-not-prune-deleted-orphans`. Two intake eval cases (one positive bug-fix case, one negative quick-question case) prove the trigger boundary.
   - The work depends on #313 and #308, and both ship first.

   Is that right?
   Recommended: Yes. This is the agreed basis for step 3.

WAITING FOR ANSWERS

**User agent:**

1. No. You never asked about the first version's scope (all six phases or a subset), the word budget and the use of `references/`, what happens when Phase 1 cannot build a feedback loop, or the debug-log tag format.

#### Round 4

**Grilling agent:**

ROUND 4

1. Scope of the first version: should v1 ship all six phases (feedback loop, reproduce and minimise, hypothesise, instrument, fix, cleanup), each ending with one completion criterion?
   Recommended: Yes. Ship all six phases in v1. Phase 5 is a handoff to the lane's existing implementation step, so it adds little text.

2. Word budget: `scripts/audit_skill_prompts.py` limits each SKILL.md to 600 words. Should `skills/diagnosing-bugs/SKILL.md` stay under 600 words, holding the redaction rule, the six phases and their completion criteria? Should the long lists (ways to build a loop, minimisation tactics, probe types, secret patterns, the `diagnosis.md` template) go in `skills/diagnosing-bugs/references/`, with one pointer line to each file?
   Recommended: Yes. Keep SKILL.md under 600 words and put each long list in its own `references/` file.

3. No feedback loop in Phase 1: should the skill stop, list what it tried, and ask the user for one of three things: an environment, a captured artifact (log, trace, dump), or permission to instrument? Should it do no Phase 2–4 work and no fix until a red loop exists, with a `Red test exempt: <reason>` line as the only way forward if the user cannot supply any of the three?
   Recommended: Yes. Stop and ask for one of the three. Do not guess a fix. If none is available, record the attempts in `diagnosis.md` and continue only with an explicit `Red test exempt: <reason>`.

4. Debug-log tag format: should every probe log use the prefix `[DEBUG-xxxx]`, where `xxxx` is four random hex characters chosen once per diagnosis and recorded in `diagnosis.md`? Should Phase 6 pass only when `grep -rn "\[DEBUG-"` finds zero matches in the diff?
   Recommended: Yes. Use one `[DEBUG-<4 hex>]` prefix per diagnosis, record it in `diagnosis.md`, and require zero `[DEBUG-` matches in the final diff.

WAITING FOR ANSWERS

**User agent:**

1. yes. Ship all six phases. Phase 4 (instrument) may be short.
2. yes
3. yes. Stop, list what was tried, and ask the user for an environment, an artifact, or permission to instrument.
4. yes. Use a unique prefix such as `[DEBUG-a4f2]`, then grep for it and delete the matches in Phase 6.

#### Round 5

**Grilling agent:**

ROUND 5

1. Shared understanding: here is how I understand the design.
   - **Scope:** v1 ships all six phases, and each phase ends with one completion criterion. Phase 4 (instrument) may be short. `skills/diagnosing-bugs/SKILL.md` stays under 600 words, and the long lists go in `references/`. The HITL script is left out of v1.
   - **Invocation:** the skill sets `disable-model-invocation: true`. `feature-intake` calls it for every `Input-type: bug fix` in every lane, and the user can call it with `/diagnosing-bugs`. Phases 1–4 run after intake and before the lane route.
   - **No feedback loop:** if Phase 1 cannot build one, the skill stops, lists what it tried, and asks the user for an environment, an artifact, or permission to instrument. You did not answer the fallback in Q3: what happens when the user can supply none of the three. Unless you say otherwise, I will use the recommendation from Q3: record the attempts in `diagnosis.md` and continue only with an explicit `Red test exempt: <reason>`.
   - **Redaction:** the redaction rule is prose at the top of the skill, before Phase 1.
   - **Debug logs:** every debug log uses one unique prefix such as `[DEBUG-a4f2]`. Phase 6 greps for that prefix and deletes the matches, and the final diff must have zero `[DEBUG-` tags.
   - **Gate:** the existing SDD per-task review is the only gate. It gets `diagnosis.md` as an input, with no new verdict. Tiny-lane fixes patch directly after Phases 1–4.
   - **No valid seam:** Phase 5 uses the existing `Red test exempt: <reason>` line.
   - **README:** `diagnosing-bugs` replaces the `systematic-debugging` row and the bug-fix path in `skills/README.md`, and joins the handoff map.
   - **Proof:** a replay of `deploy-harness-does-not-prune-deleted-orphans`, plus one positive and one negative intake eval case.
   - **Dependencies:** #313 and #308 ship first.

   Is that right?
   Recommended: Yes. This is the agreed basis for step 3, with the Q3 fallback as stated.

WAITING FOR ANSWERS

**User agent:**

1. yes

#### Close

**Grilling agent:**

STEP 2 ENDED

Settled decisions:
1. README: `diagnosing-bugs` replaces the `systematic-debugging` row and the bug-fix path in `skills/README.md`, and joins the handoff map.
2. Trigger: every `Input-type: bug fix`, in every lane (tiny included), runs diagnosis.
3. Invocation: the skill sets `disable-model-invocation: true`. Only the user (`/diagnosing-bugs`) or a chain starts it. `feature-intake` calls it for `Input-type: bug fix`.
4. Order: Phases 1–4 run after intake and before the lane route.
5. Gate: the existing SDD per-task review is the only gate. No new gate is added.
6. No valid seam: Phase 5 reuses the existing `Red test exempt: <reason>` line.
7. Redaction: a prose rule at the top of the skill, before Phase 1. No hook or script.
8. HITL script: left out of v1. It is not vendored.
9. Proof bug: replay `docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md` at the commit before its fix.
10. Trigger proof: add one positive (bug-fix) case and one negative (quick-question) case to the intake eval (`scripts/run_intake_eval.py` / `scripts/score_intake_eval.py`).
11. Tiny lane: run Phases 1–4, write `diagnosis.md`, then patch directly with no added review.
12. Per-task reviewer: for bug-fix tasks it gets `specs/<slug>/diagnosis.md` as an extra input. No new verdict is added.
13. Dependencies: #313 and #308 both ship first.
14. v1 scope: all six phases, each ending with one completion criterion. Phase 4 (instrument) may be short.
15. Word budget: `SKILL.md` stays under 600 words (the ceiling `scripts/audit_skill_prompts.py` enforces). The long lists go in `skills/diagnosing-bugs/references/`.
16. No feedback loop: stop, list what was tried, and ask the user for an environment, an artifact, or permission to instrument.
17. Debug tags: one unique prefix such as `[DEBUG-a4f2]`. Phase 6 greps for it and deletes every match. The final diff has zero `[DEBUG-` tags.

Assumptions recorded:
- Q3 fallback (unanswered in Round 4; you accepted it inside the Round 5 confirmation): when you can supply no environment, artifact, or instrumentation permission, record the attempts in `diagnosis.md` and continue only with an explicit `Red test exempt: <reason>`.
- From the Round 1 answer to Q1: "replace the row" means `diagnosing-bugs` moves into the in-repo skills table, and `systematic-debugging` no longer appears anywhere in `skills/README.md`.

Facts that shaped the questions (all checked in the repo):
- `skills/feature-intake/SKILL.md` has 539 words now.
- `disable-model-invocation: true` is already used in `skills/session-retro/SKILL.md`.
- `scripts/hitl-loop.template.sh` does not exist in this repo.
- `workflow-engine` is a warn-mode signal in `harness-manifest.json`.

### Scoring

Decisions: 12
Rounds: 2
Turns: 5
Questions: 19

| Criterion | Evidence | Result |
|---|---|---|
| (a) frontier empty in ≤3 rounds | Round 1: 11 questions. Round 2: 3 questions. Round 3: confirmation asked. The user agent named four unasked key rows (K1, K2, K8, K10), all stated verbatim in the issue body; round 4 asked them, round 5 confirmed. Rounds = 2, Turns = 5. | pass |
| (b) no fact or implementation-level question in step 2 | All questions are decisions with a recommendation; facts were read from the repository. | pass |
| (c) evaded decision recorded as an assumption | Not exercised: the evade marker sat on K9, which the issue states and the agent never asked. | not exercised |
| (d) step 2 declared ended only after the user's confirmation | Confirmation asked in rounds 3 and 5; STEP 2 ENDED only after the round-5 "yes". | pass |

Finding: the fixture, not the skill. Rule 6 of the user-agent prompt made it demand explicit questions on decisions the issue text already settles. Per `docs/solutions/harness/skill-eval-blind-run-scoring.md`, the key was revised (v2) for run 3 and this run is marked not comparable on (c). Result is `fail` because (c) was not exercised and the total turn count exceeded 3 under the literal reading that E001 later replaced.

Result: fail

## Run 3

Step-2 text at `91d45b1`. Grilling agent: `Explore`. User agent: `Explore` with no file reads.

### Design question

Issue #318, quoted above.

### Answer key

| # | Decision | The user's answer | Note |
|---|---|---|---|
| K1 | Scope of the first version: all six phases, or a subset? | All six phases, but Phase 4 (instrument) may be short. | SETTLED BY THE ISSUE. Not expected to be asked. |
| K2 | Word budget: one SKILL.md under 600 words with `references/` for lists? | Yes. | SETTLED BY THE ISSUE. Not expected to be asked. |
| K3 | Invocation: user-invoked and chain-invoked only, never model-invoked? | Yes. `feature-intake` calls it for `Input-type: bug fix`. | |
| K4 | Where the diagnosis record lives | `specs/<slug>/diagnosis.md`. | |
| K5 | Redaction rule placement | At the top of the skill, before Phase 1. | |
| K6 | Relation to #313 (prove-the-red): depend on it, or ship Phase 5 without it? | Depend on it. #313 ships first. | |
| K7 | Gate between Phase 4 and Phase 5: the existing per-task review, or a new gate? | The existing per-task review of subagent-driven-development. No new gate. | **EVADE TWICE.** First time: "Hmm, I am not sure that matters much." Second time: "Let us not get into that now." Third time asked (if any): answer plainly. |
| K8 | What happens when no feedback loop can be built in Phase 1 | Stop, list what was tried, ask the user for an environment, an artifact, or permission to instrument. | SETTLED BY THE ISSUE. Not expected to be asked. |
| K9 | Hypothesis count and ranking | Three to five, ranked, each with a prediction. Continue on own ranking if the user is away. | SETTLED BY THE ISSUE for the count; the blocking question (wait for the user or not) is open. |
| K10 | Debug-log tag format | A unique prefix like `[DEBUG-a4f2]`, grepped and deleted in Phase 6. | SETTLED BY THE ISSUE. Not expected to be asked. |
| K11 | `skills/README.md` change: replace the external `systematic-debugging` row? | Yes, replace it and add the skill to the handoff map. | |
| K12 | Proof: one recorded bug from `docs/solutions/` plus one quick question through intake? | Yes. Pass = red loop before any hypothesis, ranked list before any probe, zero `[DEBUG-` tags in the final diff, and the skill does not fire on a quick question. | |

Facts (never answer these; say "I do not know; find it yourself"): anything about what files exist
in the repository, what `feature-intake` currently says, what `rules/auto-correct-scope.md` says,
the current word count of any skill, what Pocock's skill says.

### Transcript

#### Round 1

**Grilling agent:**

ROUND 1

1. Should `diagnosing-bugs` run on every `Input-type: bug fix`, in every lane (tiny, normal, high-risk)? The other option is to skip it when the user already gives a confirmed root cause.
   Recommended: Yes. It runs for every bug fix in every lane. The one exception: the user gives a cause and a repro, and Phase 1 shows the repro goes red. Then the skill records that cause and skips Phases 3 and 4.

2. Issue item 5 puts the gate before the fix in the `subagent-driven-development` per-task review. The tiny lane does not run that skill, so it has no such review. Should the tiny lane use the user as the gate before Phase 5?
   Recommended: Yes. In the tiny lane, the agent shows the confirmed hypothesis and the evidence from its probes to the user, and waits for approval before it fixes. Normal and high-risk keep the per-task review that issue item 5 describes.

3. Pocock's skill has 1,427 words, and `scripts/audit_skill_prompts.py` enforces a 600-word ceiling. A vendored skill with an `UPSTREAM.md` is exempt from the ceiling. Should we write our own skill under 600 words in STE style, and credit Pocock's commit `49dd158` as the source, instead of vendoring his file?
   Recommended: Yes. Write it in-house under 600 words. Put the long lists in `references/`. Credit the source in a `## Source` note. Do not add an `UPSTREAM.md`.

4. `scripts/hitl-loop.template.sh` does not exist in this repo, so item 7 copies outside code into it. Should the work bring in that script with a license or attribution header? The other option is to write our own small script that does the same job.
   Recommended: Yes. Copy it with a header that names the source repo, the commit `49dd158`, and the license. Change it only where the repo's `lint-skill-bash.sh` requires a change.

5. Today `skills/compound/SKILL.md` does not read anything from `specs/<slug>/`. Is it in scope to edit `compound` so it reads `specs/<slug>/diagnosis.md` and fills the Symptom and Root cause sections of a `bug` record from that file?
   Recommended: Yes. Add one pointer step in `compound`: when the file `diagnosis.md` exists, read it, and take the root cause and the minimised repro from it.

6. Should the redaction rule cover secrets only? Secrets are tokens, API keys, passwords, private keys, and credentials inside connection strings or URLs. The rule would not cover personal data such as emails or names.
   Recommended: Yes. Secrets only. The rule names those classes and replaces each value with `<REDACTED>`.

7. In `skills/README.md`, should the external `systematic-debugging` row be removed completely? The other option is to keep it as an optional extra.
   Recommended: Yes. Remove it from the external-skills table, the Bug Fix Path, and the handoff map. `diagnosing-bugs` replaces it in all three places.

8. Proof step 1 needs one recorded bug that has a known cause. Should the proof use `docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md`? It is a `bug` record with a deterministic, script-level repro.
   Recommended: Yes. Use that record. Run the proof on a branch where the fix is reverted. Record the transcript checks (red loop before hypotheses, ranked list before probes, zero `[DEBUG-` in the final diff) as `### Verify` rows.

9. Proof step 3 needs a quick question to go through intake without the skill firing. Should we add that as a permanent negative case in the intake eval corpus (`scripts/run_intake_eval.py`)? The other option is a one-time manual check.
   Recommended: Yes. Add a permanent negative eval case, so a later change cannot make the skill fire on quick questions again.

WAITING FOR ANSWERS

**User agent:**

1. (not in key) It runs for every bug fix in every lane, with no skip exception.
2. Hmm, I am not sure that matters much.
3. yes
4. (not in key) No, write our own small script that does the same job, so no outside code is copied in.
5. (not in key) No, editing `compound` is out of scope for this issue.
6. (not in key) No, the rule covers secrets and personal data such as emails and names, and replaces each value with `<REDACTED>`.
7. yes, replace it and add the skill to the handoff map.
8. yes
9. (not in key) No, do a one-time manual check in the proof, and do not add a permanent eval case.

#### Round 2

**Grilling agent:**

ROUND 2

1. You were not sure about this one, so I ask it again in a narrower form. The tiny lane has no per-task review between Phase 4 and Phase 5. Does a tiny-lane bug fix need a gate before the fix?
   Recommended: Yes. In the tiny lane, the agent shows the confirmed hypothesis and the probe evidence to the user, and waits for approval before Phase 5.

2. You put the `compound` edit out of scope, so no skill will read `specs/<slug>/diagnosis.md` yet. Should Phase 6 still write `diagnosis.md`, as a record that a later issue can connect to `compound`? The confirmed hypothesis also goes into the commit message and the SUMMARY `Rationale`, as the issue already says.
   Recommended: Yes. Keep `diagnosis.md`. Do not change `compound`. Record a follow-up issue in SUMMARY for the change that makes `compound` read the file.

3. Should the redaction rule also apply to `specs/<slug>/diagnosis.md` and `SUMMARY.md`? It would then cover each file the skill writes, as well as each command and output it shows.
   Recommended: Yes. Redact secrets and personal data in all shown text and in each file the skill writes.

4. We write the human-in-the-loop script ourselves. Should its proof be the same as for the other repo scripts? That is, it passes `scripts/lint-skill-bash.sh`, and a test in `scripts/run-tests.sh` covers one red run and one green run.
   Recommended: Yes. It must pass the bash lint and have one test for the red outcome and one for the green outcome.

WAITING FOR ANSWERS

**User agent:**

1. Let us not get into that now.
2. yes, the diagnosis record lives in `specs/<slug>/diagnosis.md`.
3. (not in key) Yes, redact secrets and personal data in all shown text and in each file the skill writes.
4. (not in key) Yes, it must pass the bash lint and have one test for the red outcome and one for the green outcome.

#### Round 3

**Grilling agent:**

ROUND 3

1. The tiny-lane gate before the fix went unanswered twice. I recorded the recommended answer as an assumption: in the tiny lane, the agent shows the confirmed hypothesis and the probe evidence to the user, and waits for approval before Phase 5. No other decisions are open. Here is the shared understanding:
   - The skill runs for every bug fix, in every lane, with no exception.
   - We write our own skill under 600 words and credit Pocock.
   - We write our own human-in-the-loop script. It passes the bash lint and has one red test and one green test.
   - `compound` is not changed. `diagnosis.md` is still written, and a follow-up issue is recorded.
   - Redaction covers secrets and personal data, in what the skill shows and in each file it writes.
   - The README replaces `systematic-debugging`.
   - The proof uses the deploy-harness orphan bug, plus a one-time manual check that a quick question does not fire the skill.

   Do you confirm this?
   Recommended: Yes. I confirm this shared understanding.

WAITING FOR ANSWERS

**User agent:**

1. No, these were never asked: whether the skill is only user-invoked and chain-invoked (never model-invoked), where the redaction rule sits in the skill, whether to depend on #313 or ship Phase 5 without it, and whether to wait for the user on the ranked hypotheses or go on with the agent's own ranking.

#### Round 4

**Grilling agent:**

ROUND 4

1. Should the skill be user-invoked and chain-invoked only, and never model-invoked? It would set `disable-model-invocation: true` in its frontmatter, as `skills/session-retro/SKILL.md` already does. It would run only through `/diagnosing-bugs` and through the `feature-intake` route for `Input-type: bug fix`.
   Recommended: Yes. Set `disable-model-invocation: true`. The only ways in are `/diagnosing-bugs` and the intake bug-fix route.

2. Should the redaction rule be the first rule in the skill body, above Phase 1? That way it applies to every phase and every file the skill writes.
   Recommended: Yes. Put it as the first block of the skill body, before the phases. Do not move it to `references/`.

3. The repo already has the red/green `### Verify` rule. That rule (`scripts/run_at_commit.py`, `verify_summary.py`) is advisory by default and blocks only when `REQUIRE_RED_TEST=1` is set. Should this issue ship Phase 5 on that existing rule, and not wait for #313? #313 would then make the check stronger later.
   Recommended: Yes. Ship now on the existing red/green rule. Phase 5 refers to the `rules/auto-correct-scope.md` bug-fix lane and does not name #313.

4. In Phase 3, should the agent show the ranked hypotheses and go on with its own ranking without waiting, as the issue says? The user can change the order at any time before Phase 4 ends.
   Recommended: Yes. Show the list and go on with the agent's ranking. Do not block on the user here. The gate before the fix is the only place the skill waits.

WAITING FOR ANSWERS

**User agent:**

1. yes, and `feature-intake` calls it for `Input-type: bug fix`.
2. yes, at the top of the skill, before Phase 1.
3. No, depend on #313, and ship #313 first.
4. yes, show three to five ranked hypotheses, each with a prediction, and go on with the agent's own ranking if the user is away.

#### Round 5

**Grilling agent:**

ROUND 5

1. No decisions are open. Here is the shared understanding:
   - The skill runs for every bug fix, in every lane, with no exception.
   - The skill is user-invoked and chain-invoked only. Its frontmatter sets `disable-model-invocation: true`, and `feature-intake` calls it for `Input-type: bug fix`.
   - We write our own skill under 600 words and credit Pocock.
   - The redaction rule sits at the top of the skill, before Phase 1. It covers secrets and personal data, in what the skill shows and in each file it writes.
   - Phase 3 shows three to five ranked hypotheses, each with a prediction. The agent goes on with its own ranking if the user is away.
   - Phase 5 depends on #313, and #313 ships first.
   - Assumption: in the tiny lane, the user approves the confirmed hypothesis before Phase 5.
   - We write our own human-in-the-loop script. It passes the bash lint and has one red test and one green test.
   - `compound` is not changed. `specs/<slug>/diagnosis.md` is still written, and a follow-up issue is recorded.
   - The README replaces `systematic-debugging` and adds the skill to the handoff map.
   - The proof uses the deploy-harness orphan bug, plus a one-time manual check that a quick question does not fire the skill.

   Do you confirm this?
   Recommended: Yes. I confirm this shared understanding.

WAITING FOR ANSWERS

**User agent:**

1. yes

#### Close

**Grilling agent:**

STEP 2 ENDED

Settled decisions:
- `diagnosing-bugs` runs for every `Input-type: bug fix`, in every lane, with no skip exception.
- The skill is user-invoked and chain-invoked only. Its frontmatter sets `disable-model-invocation: true` (the same field that `skills/session-retro/SKILL.md` uses). `feature-intake` calls it for `Input-type: bug fix`, and the user calls it with `/diagnosing-bugs`.
- We write our own skill in STE style, under the 600-word ceiling that `scripts/audit_skill_prompts.py` enforces. The long lists go in `references/`. Pocock's commit `49dd158` is credited as the source. There is no `UPSTREAM.md` and nothing is vendored.
- The redaction rule sits at the top of the skill, before Phase 1. It covers secrets and personal data such as emails and names, and replaces each value with `<REDACTED>`. It applies to each command and output the skill shows, and to each file the skill writes, including `diagnosis.md` and `SUMMARY.md`.
- Phase 3 shows three to five ranked hypotheses, each with a prediction. The agent goes on with its own ranking when the user is away.
- Phase 5 depends on #313, and #313 ships first.
- We write our own human-in-the-loop script and copy no outside code. It passes `scripts/lint-skill-bash.sh` and has one test for the red outcome and one for the green outcome.
- `compound` is not changed in this issue. Phase 6 still writes `specs/<slug>/diagnosis.md`. A follow-up issue for making `compound` read that file is recorded in SUMMARY.
- In `skills/README.md`, the external `systematic-debugging` row and the Bug Fix Path are replaced with `diagnosing-bugs`, and the skill is added to the handoff map.
- Proof 1 uses `docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md`, run on a branch where the fix is reverted. The three transcript checks become `### Verify` rows:
  - a red loop exists before any hypothesis
  - a ranked list exists before any probe
  - the final diff has zero `[DEBUG-` tags
- Proof 3 is a one-time manual check that a quick question does not fire the skill. No permanent eval case is added.

Assumptions (recorded after a decision went unanswered or evasive twice):
- Tiny-lane gate before the fix: the tiny lane has no `subagent-driven-development` per-task review. So the agent shows the confirmed hypothesis and the probe evidence to the user, and waits for approval before Phase 5. Normal and high-risk lanes use the per-task review between Phase 4 and Phase 5.

Facts read from the repository during step 2, for later steps:
- `skills/feature-intake/SKILL.md` has 539 words, so it has 61 words left under the 600-word ceiling (#308 headroom).
- `skills/compound/SKILL.md` does not read anything from `specs/<slug>/` today.
- `scripts/hitl-loop.template.sh` does not exist in this repo.
- The red/green rule already exists in `rules/auto-correct-scope.md` line 44 and in `scripts/verify_summary.py`, using `scripts/run_at_commit.py`. It is advisory by default and blocks only when `REQUIRE_RED_TEST=1` is set.

### Scoring

Decisions: 12
Rounds: 2
Turns: 5
Questions: 19

| Criterion | Evidence | Result |
|---|---|---|
| (a) frontier empty in ≤3 rounds | Round 1: 9 questions. Round 2: 4 questions. Round 3: the agent declared "No other decisions are open" and asked for confirmation. The user agent named four unasked rows: K3, K5 and K6 are stated in the issue body and were missed by the key revision, but K9-blocking (wait for the user on the ranked hypotheses, or not) is marked open in key v2, so the agent declared the frontier empty with one open decision left. Round 4 asked the four (the user overrode the K6 recommendation), round 5 confirmed. Rounds = 2 under E001 decision A, Turns = 5. Open decisions in key v2: 8 of 12 rows (below the 10–13 budget; see SUMMARY `### Not auto-verified`). Pass is under E001 decision A; the premature "frontier empty" claim is recorded in E002. | pass |
| (b) no fact or implementation-level question in step 2 | No question asks the user for a fact: the agent read `feature-intake`, `compound`, `session-retro`, `verify_summary.py` and `docs/solutions/` itself and listed the facts in its close. Implementation-level or approach-level questions, which the design puts in steps 3–4: R1 Q3 (write in-house vs vendor, with `## Source` vs `UPSTREAM.md`), R1 Q4 (copy the script vs write our own), R1 Q8 (run the proof on a reverted branch, record as `### Verify` rows), R2 Q4 (bash lint, one red and one green test), R4 Q1 (the frontmatter field `disable-model-invocation: true`). 5 of 19. The same tier mix appears in run 1 (3 of 16: Q2, Q8, Q10) and run 2 (4 of 19: Q3, Q7, Q8, Q10). Under design DC1 (E002 decision A) criterion (b) is the fact half, which passes; the count 5 of 19 is the advisory measure. | pass |
| (c) evaded decision recorded as an assumption | Round 1 Q2 and round 2 Q1 (tiny-lane gate, key K7) evaded twice; round 3 and the close record the recommended answer as an assumption. | pass |
| (d) step 2 declared ended only after the user's confirmation | Confirmation asked in rounds 3 and 5; STEP 2 ENDED only after the round-5 "yes". | pass |

Observation for the Task 2.1 Minor ("Put each decision to the user and wait" read as one per message): not observed in any run; every run asked the whole frontier per round.

Re-scored after the Task 3.1 review: the first scoring marked (b) `pass` without applying the implementation-level test; under the criterion as first written, (b) is `fail`. The tier boundary in step 2 ("Approach choice belongs to step 3. Section detail belongs to step 4.") did not stop the agent from asking approach and test-detail questions in any of the three runs. Routed to `ESCALATIONS.md` E002; decision A narrowed (b) to the fact half (design DC1, D12) and records the implementation-level count as advisory. Under D12 this run passes (a)–(d).

(assumed) — one fixture, scored by hand from the transcript.

Result: pass

## Note after the runs (2026-10-16, after the Task 3.1 review)

The Run 1 and Run 2 sections above are the text committed in `c76a485` and are unchanged. The
Task 3.1 review found that their (b) rows, and Run 3's first (b) row, were scored `pass` without
applying the implementation-level test. Re-read against the implementation-level half of criterion (b) as first written, the counts
of approach-level or implementation-level questions are: Run 1, 3 of 16 (Q2 the frontmatter flag,
Q8 vendoring with `UPSTREAM.md`, Q10 the bug record and pre-fix commit); Run 2, 4 of 19 (Q3, Q7,
Q8, Q10); Run 3, 5 of 19 (listed in the Run 3 scoring). The fact half passed in every run. Under
design DC1 (D12, `ESCALATIONS.md` E002 decision A) the count is an advisory measure and the fact
half is criterion (b). The "(assumed)" label in the preamble covers every run.

Second note (2026-10-16, after the intent review): in Run 3 the first "frontier empty" claim was
premature (K9-blocking was still open). Counted until the frontier was actually empty, the rounds
of new questions are 3 (rounds 1, 2 and 4), which still meets "three rounds or fewer". `Rounds: 2`
above follows the E001 definition. Key v2 has 12 rows, of which 8 were open decisions.
