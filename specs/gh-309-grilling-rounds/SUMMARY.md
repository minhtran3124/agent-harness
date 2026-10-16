# gh-309-grilling-rounds — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate (rewrites step 2 of skills/brainstorming/SKILL.md); the issue proposes normal
Flags: existing behavior, weak proof
Affects: skills/brainstorming (design-fork and high-risk paths)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.


### Intent

Intent-source: specs/gh-309-grilling-rounds/intent.md @ 32400ac8adea07fd3c04530b10b6890dda2f2d43

merge it, re-install with latest code on sdlc branch and start for next gh issue

Issue #309, as referenced (https://github.com/minhtran3124/agent-harness/issues/309):

> **Phase 1: conversation and record prose.** Roadmap: https://claude.ai/artifact/AohXkjEsZKRDXhHheAsrtW
>
> Goal: Ask design questions in rounds, not one per message.
>
> Steps: Rewrite step 2 of `skills/brainstorming/SKILL.md` (442 words) so that the agent does
> this: (1) Map the decisions as a design tree. (2) Find the frontier: each decision for which the
> user already settled the prerequisites. (3) Ask the whole frontier in one numbered round.
> (4) Give a recommended answer for each question. Word the question so that "yes" accepts the
> recommended answer. (5) Dispatch a sub-agent to find any fact. Do not ask the user for a fact.
> (6) Give each decision to the user, then wait. (7) Act only after the user confirms a shared
> understanding. Keep the current rule "move on after two evasive answers" for decisions only.
>
> Scope guard: Only the high-risk path and the design-fork path run brainstorming. The
> notify-and-proceed flow of the normal lane does not change.
>
> Lane: normal, with a context-propagation-audit. Dependencies: None.
>
> Proof: (1) Record one brainstorming session on a real design fork. (2) Count the rounds and the
> questions. (3) The issue passes when the frontier closes in three rounds or fewer.
>
> Source: Pocock, `grilling/SKILL.md`. CHANGELOG: "Same 13 questions land in ~3 rounds instead of 13."

### Intake notes

- The issue proposes lane `normal`. The manifest's `workflow-engine` hard gate covers `skills/*/SKILL.md`, so intake assigns `high-risk`. The human did not narrow scope.
- Confidence high: one clear reading; the issue names the file, the seven behaviors and the proof.
- Proof per intent.md: a blind run before merge, marked "(assumed)"; the first real brainstorming session after merge is the live evidence, listed under `### Not auto-verified` until then.
- 2026-10-16 re-pin: intent.md 374d10c → 2bc2cb2, amended per brainstorming round 1 (tier boundary, stop condition, agent-found facts, blind-run proof). Re-classified: lane, confidence, flags and route unchanged.
- 2026-10-16 re-pin: intent.md 2bc2cb2 → 32400ac, amended after the intent review to record ESCALATIONS E001-A (round counting) and E002-A (criterion (b) fact half, #321), the confirmation wording of `91d45b1`, the spec-local check script, and the audit's paraphrase fix. Re-classified: lane, confidence, flags and route unchanged.
- Self-reference risk: this branch runs brainstorming while it rewrites brainstorming step 2. The session uses the deployed (old) text; the new text is proven only by the recorded run.

## What changed

Step 2 of `skills/brainstorming/SKILL.md` no longer asks one clarifying question per message. It maps the open decisions as a design tree bounded at the requirements tier, asks the whole frontier in one numbered round with a recommended answer per question, finds facts itself (or by subagent for a large search), puts decisions to the user, records an evaded decision as an assumption after two rounds, and ends only when the frontier is empty and the user confirms a shared understanding (a plain "yes" to the whole last round counts; otherwise it asks). The skill is 557 words (measured 2026-10-16 `wc -w`). Steps 1 and 3–6, the HARD-GATE and the references are unchanged. The spec adds `check_gh309.py` (spec-local checks), `qualifiers-brainstorming.md` (condition-word citations) and `blind-run.md` (three blind runs on the #318 fixture).

### Rationale

<!-- Why this approach — the decision + the key constraint/signal that drove it.
     This is the audit record for autonomous (no-human) work: write it so the
     decision can be reconstructed later WITHOUT re-reading the diff. -->

Pocock's `grilling` measured the same change (13 questions in ~3 rounds instead of 13, upstream changelog PR #593), and nothing in this repo pins the old step-2 wording, so the procedure was written inline (design D11) where the model reads it on every run. The "Do not over-probe" brake was replaced by a tier boundary and a stop condition (D4) rather than deleted, because its reason (steps 3–4 still catch gaps) stays true while its rate-limit no longer applies once a round is cheap. Blind run 1 showed the stop condition let a mixed last round pass as confirmation; the fix (`91d45b1`) makes the agent ask when the last round is not a plain "yes".

### Alternatives considered

- Reference file `references/grilling-rounds.md` with a short step 2 (design approach B): rejected, a reference is read only on an explicit Read step and pointer sentences attracted intent-review drift in #308.
- Sub-steps 2a–2g (approach C): rejected, more words and breaks the six-step rhythm.
- Pocock's fixed `❓/➡️` question template: rejected (D3), numbered questions with a recommended answer are enough and cost fewer words.
- A scored eval under `evals/` for the blind run: out of scope for a one-run proof; the KB pattern was reused by hand (hidden key, fresh agents, first run kept).

### Deviations

<!-- Every Rule 1–3 auto-fix per rules/auto-correct-scope.md, labeled by rule.
     Leave a single `- none` line if there were none. -->

- Design decision change: `design.md` DC1 (2026-10-16) reopens D9 and settles D12; criterion (b) of the blind run is its fact half, with the approach- or implementation-level question count recorded as advisory (3 of 16, 4 of 19, 5 of 19). Decided by the user in `ESCALATIONS.md` E002 (A). Follow-up: issue #321 owns the tier boundary. No Rule 1–3 auto-fix.

### Task review ledger

- Task 1.1 (`ae0eba5`): spec pass, quality approved. Minor: (1) each bad self-test fixture carries two defects, so a single regressed check would not be caught alone; (2) `run()` uses `check=True`, so a git failure in `qualifiers`/`scope` is a traceback, not one failure line (still fails closed); (3) `entries()` keys on (line, word), so two drops of one word in one hunk share a key and a bad cited text can hide behind a later good one.
- Task 2.1 (`4a64270`, `84db611`): spec pass, quality approved, meaning pass. Minor (plan-mandated): "Put each decision to the user and wait" two sentences after "Ask the whole frontier in one numbered round" could be read as one decision per message; the wording comes from the design draft. Watched in the blind run (criterion (a)); fix only if the run shows it. Not observed in three runs.
- Task 3.1 (`91d45b1`, `c76a485`): first review spec **fail**, quality approved, meaning pass. Important (1): run 3 criterion (b) was scored `pass` without the implementation-level test; re-scored `fail` (5 of 19 questions at approach or implementation level); routed to E002. Important (2): E001's context said K9-blocking was issue-stated; it was an open row in key v2 and the agent missed it before declaring the frontier empty; corrected in `blind-run.md` and under E001, and E002 asks whether decision A stands. Minor: "(assumed)" label added to runs 1 and 2; "first run unchanged" is unverifiable (recorded under `### Not auto-verified`); key v2 has 8 open rows, below the 10–13 budget (recorded under `### Not auto-verified`).
- Task 3.1 fix rounds: round 1 (`e372f86`) re-scored run 3, corrected the E001 premise and recorded E002 decision A as design DC1/D12, but edited the Run 1 and Run 2 sections, which the plan forbids; round 2 (`119640d`) restored both sections to the `c76a485` text and moved the per-run counts to a dated note. Final verdict: spec pass, quality approved. Minor: the note's wording ("scored on the fact half only") corrected to "scored `pass` without applying the implementation-level test"; the SUMMARY lines the reviewer could not see (DC1 pointer under `### Deviations`, the three `### Not auto-verified` entries) are confirmed present by the controller.

### Verify

<!-- Evidence over assertion: one row per check that was actually RUN.
     A claim of "done" is only valid with a re-runnable command + its result.
     Do not list a command that was not run.
     The trailing `Criterion` column is optional: name an `SC-n` from PLAN.md §3
     when the row satisfies one; every SC must be covered by >=1 passing row
     (enforced by scripts/verify_summary.py). Leave blank for rows that map to no SC. -->

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Step-2 anchors, evasive sentence names decision, visual-artifact sentence verbatim, no semicolon | `python3 specs/gh-309-grilling-rounds/check_gh309.py anchors` | 0 | | SC-1 |
| 600-word ceiling for every skill | `python3 scripts/audit_skill_prompts.py` | 0 | brainstorming 557 words | SC-2 |
| STE hard count at or below the 996f50d baseline | `python3 scripts/check_ste_baseline.py --strict --against 996f50d` | 0 | 73 files, 0 above baseline | SC-3 |
| `any`/`still` cited as replaced at HEAD; qualifier script lists nothing else | `python3 specs/gh-309-grilling-rounds/check_gh309.py qualifiers` | 0 | script prints `- none` | SC-4 |
| Last blind run: 12 key rows (8 open), Rounds 2, (a)–(d) pass, earlier runs carry a Result line | `python3 specs/gh-309-grilling-rounds/check_gh309.py blindrun` | 0 | Run 3 scored; Turns 5 recorded beside Rounds 2 (E001 A); 3 rounds counted to actual closure | SC-5 |
| Only `skills/brainstorming/SKILL.md` changed under `skills/` since 996f50d | `python3 specs/gh-309-grilling-rounds/check_gh309.py scope` | 0 | | SC-6 |
| Spec-local checker self-test | `python3 specs/gh-309-grilling-rounds/check_gh309.py --selftest` | 0 | | |

### Not auto-verified

<!-- The other half of the panel. `### Verify` above is the CODE-VERIFIABLE side: every
     row there is a command a machine re-ran. This section is the negative scope — what
     this change CLAIMS that no gate checks. Per CLAUDE.md "Gate verifiability", name the
     tier each such claim actually reached:
       traceability — structure matches (an ID exists, a render agrees with its ledger)
       provenance   — evidence re-derived from the source of truth (receipt pinned at base)
       truth        — behavior re-run (command re-executed, exit codes compared)
     Listing an unverified claim here is not a defect; leaving one UNLISTED is — that is
     how a traceability-tier check gets read as proof of truth.
     Use `- none` only when every claim in this SUMMARY is covered by a Verify row. -->

- The frontier closes in three rounds or fewer in a real brainstorming session — reached none; the only measurement is three blind runs on one fixture (`blind-run.md`, "(assumed)"), accepted risk per design A4. The first real session on a design fork after merge is the live evidence.
- The seven behaviors are stated with their meaning intact — reached provenance; the task reviewer's spec verdict compared the text with the design's seven-sentence map (Task 2.1 ledger); `anchors` only checks phrases.
- Blind-run scoring (a)–(d) — reached provenance; one orchestrator scored the transcripts by hand, and `blindrun` checks only the record's shape. `Rounds: 2` follows E001 decision A; the total turn count was 5 in runs 2 and 3 because the fixture key reopened issue-stated decisions.
- The agent never asks a fact — reached provenance; checked once per run on one fixture, not in general.
- "The first run's section is present and unchanged" — reached none; the three run sections were written and committed together in `c76a485` after the runs, so there is no earlier version to compare; runs 1 and 2 also hold notes written after their runs ("Fixed in `91d45b1`", "the literal reading that E001 later replaced").
- The fixture leaves 10–13 decisions open — reached none; key v2 has 12 rows (inside the budget the amended intent sets for key rows) but only 8 open decisions, because 4 rows restate the issue text.
- The deployed copy matches the source — reached truth for this worktree only (`deploy-harness.sh` then `diff`, exit 0); consumers get it on their next re-sync.

### Rollback

<!-- Required for any high-risk / Rule-4 action: the exact command(s) to undo it.
     For reversible tiny/normal work, `git revert <sha>` is sufficient. -->

- Restore the old step 2: `git revert 91d45b1 4a64270` (the fix, then the rewrite); the qualifiers file then cites text that no longer exists, so also `git revert 84db611`.
- The spec files (`check_gh309.py`, `blind-run.md`, `ESCALATIONS.md`, `qualifiers-brainstorming.md`) are records; revert `ae0eba5` and `c76a485` only if the whole branch is withdrawn.
- Re-sync consumers after the revert: `bash scripts/deploy-harness.sh`.

### Harness-Delta

<!-- What friction did this task reveal about the workflow itself?
     fix-direct (done in this task) or backlog (-> compound -> docs/solutions/).
     Leave `- none` if the workflow needed no change. -->

- backlog — a blind-run answer key must mark every decision the fixture's own text already states as settled, or the user agent reopens them and inflates the turn count (runs 2 and 3). Add this to `docs/solutions/harness/skill-eval-blind-run-scoring.md` at compound time.
- backlog — the commit gate reads an untracked `SUMMARY.md` beside any staged `specs/<slug>/` file and blocks on missing high-risk evidence, so every bookkeeping commit before the evidence exists needs the SUMMARY moved aside. A `SUMMARY.md` that is untracked and unstaged should warn, not block.
- backlog — this session ran the old step 2 while rewriting it; the self-reference cost was one wasted turn (the "design tree field" question) and no defect.

### Intent Findings

Intent review, plan-blind. First pass against intent.md @ `2bc2cb2`, range `dbc8f5c..58084de`: six findings. Three were drift that changed behavior (criterion (b) narrowed by E002-A, rounds counted by E001-A, 8 of 12 key rows open), one excess (`check_gh309.py` greps step 2), one excess (`agents/README.md` paraphrase fix), one equivalent drift (confirmation wording after `91d45b1`). Cause: the user's E001-A and E002-A decisions had not been carried into intent.md. Fix: intent.md amended, user-approved, re-pinned at `32400ac`.

Second pass against intent.md @ `32400ac`, range `dbc8f5c..32400ac`: ✅ no intent divergence; all six first-pass findings resolved by explicit intent clauses; SC-1…SC-6 each proven by a passing Verify row.

### Context-Propagation Audit

Trigger: `workflow-engine` (diff touches `skills/brainstorming/SKILL.md`). Audited at `c76a485`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `skills/brainstorming/SKILL.md` step 2 (new procedure) | the brainstorming skill itself, loaded by the Skill tool | main session | always-loaded on invocation, from the deployed `.claude/skills/brainstorming/SKILL.md` | `bash scripts/deploy-harness.sh --target <worktree>` then `diff skills/brainstorming/SKILL.md .claude/skills/brainstorming/SKILL.md` exit 0 (2026-10-16) |
| step 2 wording | `skills/feature-intake/SKILL.md:66` (route), `skills/README.md:33,70,107,158,159,186` (inventory, handoff map), `harness-manifest.json:230` (skills list) | main session | n/a: none of these quotes or paraphrases step 2 | `grep -rn brainstorming` over those files; each hit names the skill only |
| old step-2 wording ("one clarifying question", "Do not over-probe") | tests, hooks, scripts, evals, rules, agents | all | n/a: no consumer pins it | `grep -rn` over `skills rules agents hooks scripts tests evals docs` returns no hit at HEAD |
| step 2 in a child context | none: no dispatch prompt pastes or reads step 2 | implementer, reviewer, scorer | n/a | `grep -rn "brainstorming" skills/*/…prompt*.md` returns no hit; the blind-run prompts in `blind-run.md` are a record, not a consumer |

| old step-2 rhythm ("one question at a time") | `agents/README.md:47,55` (why brainstorming is a skill, not an agent) | human reader, any session | prose paraphrase, not a consumer of the instruction itself | found by the correctness-review call-site-impact finder, missed by this audit's first grep (it searched "one clarifying question", not "one at a time"); both lines reworded to "in rounds" / "numbered question rounds" in the correctness fix commit |

Result: **PASS** after one repair. One consumer of the instruction (the skill itself), delivered by the deploy step and proven by diff; one paraphrase in `agents/README.md` repaired; no inline copy exists, so no drift test is needed. Lesson: grep the old wording's synonyms, not only its exact phrase.

### Correctness Review

Range `dbc8f5c..119640d` (spec-only commit `6fc40fb` after it), review package `.harness-state/sdd/package-branch.md`, six plan-blind FIND angles, ten deduplicated locations scored in fresh contexts, threshold 75 (`skills/correctness-review/review-config.json`). No location reached the threshold, so no fix round ran. Blocking findings: 0.

Advisory (below threshold, recorded for a human):

- score 50 — `skills/brainstorming/SKILL.md:26-27`. "Never ask the user for a fact" has no branch for a fact that no read or subagent can find (a production load figure, a deadline). The scorer notes such items usually enter the tree as constraints, which do go to the user. Follow-up candidate for #321: send an unfindable fact to the assumption record or allow a confirm-my-guess question.
- score 50 — `skills/brainstorming/SKILL.md:24`. The frontier is "each decision whose prerequisites the user already settled"; a decision settled by a recorded assumption is not literally "settled by the user", so its dependents could be orphaned. Follow-up candidate for #321: "settled, by the user or by a recorded assumption".
- score 50 — `specs/gh-309-grilling-rounds/check_gh309.py:198` (`Result: pass` membership test), `:170-175` (`any()` over `Decisions:`/`Rounds:` lines), `:188` (duplicate scoring rows: last wins). Each passes a contradictory hand-written record; the committed `blind-run.md` has exactly one line or row of each kind per run. Spec-local checker; not wired into CI.
- score 50 — `specs/gh-309-grilling-rounds/check_gh309.py:49`. `ROOT` comes from `git rev-parse` in the caller's cwd at import time with `check=True`: a traceback outside a checkout (even for `--selftest`), and the wrong tree when run from another checkout; `anchors()` lacks the `is_file` guard its siblings have.
- score 50 — `specs/gh-309-grilling-rounds/check_gh309.py:101`. Duplicate `(line, word)` qualifier entries collapse to the last one (same as Task 1.1 Minor 3).
- score 50 — `specs/gh-309-grilling-rounds/check_gh309.py:31`. `BASE = "996f50d"` with two-dot ranges: if `sdlc` gains a `skills/` commit that is merged into this branch before the Verify rows are re-run, `scope` and `qualifiers` count that commit as this branch's. Mitigation at finishing: re-check `git merge-base HEAD sdlc` (plan Global Constraint); a merge-base or three-dot range is the durable fix.
- score 25 — `specs/gh-309-grilling-rounds/check_gh309.py:141`. Qualifier hits in a `skills/brainstorming/` file other than `SKILL.md` can never be satisfied; fails closed and `scope` already forbids such files.
- score 0 (unmodified line, fixed anyway) — `agents/README.md:55` and `:47` still said "one question at a time"; reworded in the correctness fix commit and recorded in the propagation audit above.
