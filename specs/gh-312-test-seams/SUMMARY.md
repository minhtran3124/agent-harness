# gh-312-test-seams — Summary

Lane: high-risk
Confidence: high
Reason: four risk flags (existing behavior, public contract, multi-domain, weak proof); the diff edits the implementer and reviewer contracts and scripts/check_plan_contract.py, and trips the warn-mode workflow-engine signal
Flags: existing behavior, public contracts, multi-domain, weak proof
Affects: plan format contract (rules/plan-format.md, scripts/check_plan_contract.py), writing-plans, subagent-driven-development implementer and task-reviewer prompts
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- The user's request VERBATIM at intake — do NOT paraphrase or summarize. Either form:
     the chat request verbatim (legacy slugs), or the line
     `Intent-source: specs/<slug>/intent.md @ <sha>` followed by the request verbatim: the
     intent's `## Original request`, else the chat request, else `none — intent.md is the request`.
     This is the oracle for intent-review (the final stage of subagent-driven-development):
     the third reviewer is blind to PLAN.md and checks the finished diff against this text
     (plus the pinned intent.md, when present). If the request came over several
     conversational turns, quote the scope-deciding sentences in chronological order.
     Capturing intent here, not in the plan, is what keeps the intent oracle independent of
     the plan oracle. -->

Intent-source: specs/gh-312-test-seams/intent.md @ 2cd64031717e1bd53a922359c2ffb847957f152a

ok

(Agreed plan from the previous turn: close #302, park #310, and start #312 with feature-intake
in a new worktree cut from `sdlc`. GitHub issue #312, "[P2] Lesson 2: agreed test seams from plan
to implementer to reviewer": Declare the test seams in the plan. Send them to the implementer and
to the reviewer. Ban tautological tests. Steps — 1. Plan: extend the `Interfaces` line in
`rules/plan-format.md` and `skills/writing-plans/SKILL.md` with a `Seams:` entry for each task. A
seam is the point where the test observes behavior. One seam is the ideal number. Add a one-line
note on what the seam catches and what it misses. 2. Implementer: in
`skills/subagent-driven-development/implementer-prompt.md`, replace "Write tests. Follow TDD if
the task says to." with these rules: write tests only at the declared seams; take each expected
value from an independent source: a known-good literal, a worked example, or the spec; if a test
breaks on a refactor and the behavior did not change, the test is implementation-coupled —
rewrite it. 3. Reviewer: add a seam-conformance check to the quality verdict in
`task-reviewer-prompt.md`. Each new test sits at a declared seam. The implementer copies no
expected value from the implementation. 4. Resume path: the context-propagation-audit must show
that the seam list survives `resume <slug>` from a fresh session. `task_brief.py` rebuilds the
brief. Lane: high-risk. Dependencies: #308. Proof: replay the recorded fixture-fitted case
through the task reviewer with the seam check; the issue passes when the reviewer flags at least
the implementation-coupled tests that the correctness review found later.)

Q1: bat buoc có check
Q2: đề xuất

Q1 - required check
Q2 - B

phân tích câu Q3

A

### Intake notes

<!-- Agent-written intake notes (confidence reasoning, assumed defaults, re-pin lines).
     Not part of the intent oracle. `- none` when empty. -->

- Confidence high: the user decided Q1 (blocking check), Q2 (format B, a separate `Seams:`
  field) and Q3 (option A, `Plan-contract: 2` marker) before approval.
- Re-pinned 8e8c1e1 → 2cd6403: intent amended with brainstorming round-1 decisions B1–B8.
- Worktree `.claude/worktrees/feat+gh-312-test-seams` cut from `sdlc` `430192d`; PR base `sdlc`.
- Observed at intake: `task_brief.py` copies the whole task block into the brief;
  `render_plan.py` appends an unknown bullet to the field before it;
  `scripts/test_check_task_review_adoption.py` runs `check_plan_contract.py` on a shipped
  contract plan in every test run.

## What changed

A plan task can now declare its test seams. `rules/plan-format.md` and `writing-plans` define a
`- Plan-contract: 2` marker (a bullet in `## Global Constraints`) and a one-line `- **Seams:**`
field after `Interfaces` (`catches:`/`misses:` per seam, ` | ` between seams, or
`none — <reason>`). `scripts/check_plan_contract.py` rejects a marked plan whose task has no
valid seam, a misplaced seam, or an unknown marker version; unmarked plans (all 85 committed
plans) keep today's result. The implementer prompt now tests only at declared seams, takes
expected values from an independent source, tests on real inputs when they exist, and returns
`NEEDS_CONTEXT` for an unusable seam. The task-reviewer quality verdict now flags off-seam tests,
copied expected values and fixture-only tests as Important. `check_task_review_contract.py` pins
the key phrases of both prompts. A canary passed, and a replay of gh-175 Task 2.1 flagged the
fixture-fitting cause that its correctness review later confirmed.

### Rationale

<!-- Why this approach — the decision + the key constraint/signal that drove it.
     This is the audit record for autonomous (no-human) work: write it so the
     decision can be reconstructed later WITHOUT re-reading the diff. -->

The delivery paths already existed: `task_brief.py` copies `## Global Constraints` and the whole
task block into every brief (same-session and resume), and the renderer and resume parser fold an
unknown bullet into the field before it. So the change is prose in two prompts plus one checker
rule, with an opt-in marker so committed and in-flight plans stay valid (user decisions Q1–Q3,
B1–B8, approach A).

### Alternatives considered

<!-- Other options weighed + why not. `- A separate `**Seams:**` parser field in `render_plan.py`/`resume_decision.py`: rejected, it
  touches a high-blast file for display only.
- A warn-only check: rejected by the user (Q1, blocking check).
- Grandfathering by `status: shipped`, a git-date cutoff, or backfilling the 36 contract plans:
  rejected for the opt-in marker (Q3).
- A shared reference file or brief-injected rules: rejected for inline prompt rules with phrase
  pins (approach A), because delivery must not depend on a subagent Read.` if it was the single obvious
     approach (typical for tiny lane). -->

- none

### Deviations

<!-- Every Rule 1–3 auto-fix per rules/auto-correct-scope.md, labeled by rule.
     Leave a single `- Rule 1 — `scripts/check_plan_contract.py`: an empty `catches:` directly before `misses:` was
  accepted; the clause capture now stops at the next clause keyword, with a test. Task 1.1 review
  Minor finding. Commit `a4cf8fa`.
- Rule 1 — `implementer-prompt.md`: the bug-fix seam rule now says "When the brief has no
  `Plan-contract: 2` line, skip this rule only.", so bug fixes on unmarked plans do not stall
  (D11 skips the declared-seam rule without the marker). Task 1.3 review Minor finding. Commit
  `113a374`.
- Research brief addition (implements D1, no new decision): the checker rejects a `Seams:`
  bullet that is not the next field bullet after `Interfaces`, because both parsers fold a
  misplaced bullet into the field before it (after `Verify`, into the re-run command).` line if there were none. -->

- none

### Verify

<!-- Evidence over assertion: one row per check that was actually RUN.
     A claim of "done" is only valid with a re-runnable command + its result.
     Do not list a command that was not run.
     The trailing `Criterion` column is optional: name an `SC-n` from PLAN.md §3
     when the row satisfies one; every SC must be covered by >=1 passing row
     (enforced by scripts/verify_summary.py). Leave blank for rows that map to no SC. -->

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| checker unit tests (error table + field order) | `python3 -m pytest scripts/test_check_plan_contract.py -q` | 0 | 33 passed | SC-1 |
| checker corpus test | `python3 -m pytest scripts/test_check_plan_contract.py -q -k corpus` | 0 | every committed specs/*/PLAN.md passes | SC-2 |
| prompt phrase pins | `python3 -m pytest scripts/test_check_task_review_contract.py -q` | 0 | 4 passed | SC-3 |
| brief carries marker and seams | `python3 -m pytest skills/subagent-driven-development/scripts/test_task_brief.py -q` | 0 | 4 passed | SC-4 |
| canary record | `grep -q "^Canary result: pass$" specs/gh-312-test-seams/canary.md` | 0 | both planted tests flagged Important | SC-5 |
| gh-175 replay record | `grep -q "^Replay result: " specs/gh-312-test-seams/canary.md` | 0 | evidence only | SC-6 |
| STE baseline | `python3 scripts/check_ste_baseline.py --strict --against 430192d` | 0 | 73 files, 0 above baseline | SC-7 |
| render this plan | `python3 skills/visual-planner/render_plan.py specs/gh-312-test-seams/PLAN.md specs/gh-312-test-seams/PLAN.html` | 0 | tasks=5 waves=2 | SC-8 |
| seam text in PLAN.html | `grep -q "catches: a wrong accept or reject" specs/gh-312-test-seams/PLAN.html` | 0 | | SC-9 |
| red/green prose anchors | `python3 -m pytest scripts/test_verify_summary.py -q -k "red_green_prose or input_type_reaches"` | 0 | 2 passed | SC-10 |
| context-propagation anchors | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 29 passed | SC-11 |
| SDD handoff anchors | `bash tests/scripts/sdd-artifact-handoffs.test.sh` | 0 | passed | SC-12 |
| this plan passes the new checker | `python3 scripts/check_plan_contract.py specs/gh-312-test-seams/PLAN.md` | 0 | | |
| word ceiling | `python3 scripts/audit_skill_prompts.py` | 0 | writing-plans 482 words | |

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

- The reviewer catches off-seam tests and copied expected values in general — reached truth on
  one canary sample only; model judgement cannot be proved by one run (design "What we do not
  claim").
- The gh-175 replay shows the seam check would have caught the gh-175 fixture fitting — reached
  provenance (a recorded reviewer run on the historical diff, against today's larger corpus);
  evidence, not a gate.
- The checker proves a seam is the right seam — not claimed; it checks presence and shape only
  (traceability).
- Implementers follow the new test rules in real runs — not verified; the next SDD runs on marked
  plans are the evidence.
- STE quality of the new prompt prose — reached traceability only: `ste-lint.py` skips fenced
  text, and both dispatch prompts are almost all fenced, so SC-7 does not see the new sentences
  (checked by hand by the implementer and the task reviewer).
- Consumer repos with in-flight contract plans keep working — not observed; the marker keeps
  unmarked plans on today's checks by design.

### Rollback

<!-- Required for any high-risk / Rule-4 action: the exact command(s) to undo it.
     For reversible tiny/normal work, `git revert <sha>` is sufficient. -->

- `git revert --no-edit 113a374 a4cf8fa f8019a6 d60491e 21799ef bb99661` (implementation
  commits, newest first), then re-sync consumers with `bash scripts/deploy-harness.sh`. Plans that
  already carry `- Plan-contract: 2` keep parsing under the old checker, which ignores the marker
  and the `Seams:` bullet.

### Harness-Delta

<!-- What friction did this task reveal about the workflow itself?
     fix-direct (done in this task) or backlog (-> compound -> docs/solutions/).
     Leave `- backlog — `ste-lint.py` skips fenced blocks, so the STE baseline and the reviewer's `## STE
  lint` counts do not cover dispatch prompts that live inside a fence (Task 1.3). Recorded before
  as `docs/solutions/harness/ste-ratchet-blind-to-fenced-prompt-prose.md`; this run is another
  occurrence. → compound.
- backlog — the system `python3` here has no pytest; Verify rows that say `python3 -m pytest` ran
  through `${TMPDIR:-/tmp}/harness-tests-venv/bin/python`. Every implementer hit it.

### Correctness Review

Six plan-blind FIND angles over `430192d..6f7d7ed` (`specs/**` excluded), then one independent
scorer per deduplicated location. Threshold 75 (config default). No location reached it, so no
fix round ran. `removed-behavior` found nothing.

Advisory findings (below threshold), recorded for a follow-up issue:

- 50 — `scripts/check_plan_contract.py:31`: `MARKER` accepts only `- Plan-contract:`; a `*`
  bullet, a bold `- **Plan-contract:** 2` or an indented marker is silently not a marker, so the
  seam rule and the unknown-version check are skipped while the brief still carries the line and
  the prompts apply the seam rules. Fix direction: widen `MARKER` or reject near-miss spellings.
- 0 (unmodified line) — `skills/subagent-driven-development/scripts/task_brief.py:16`:
  `section()` does not mask fences, so a fenced `- Plan-contract: 2` example in Global
  Constraints reaches the brief while the checker treats the plan as unmarked. Same root cause as
  the row above: the checker and the prompts do not share one marker definition.
- 50 — `scripts/check_plan_contract.py:52`: `value.split(" | ")` splits inside a backticked
  seam name (false reject), and a second seam after an unspaced `|` or after a `none — reason`
  value is not checked (false accept).
- 50 — `scripts/check_plan_contract.py:48`: the `none` branch accepts a seam named `none-…`
  and rejects an en dash (`none – reason`).
- 50 — `scripts/check_plan_contract.py:54`: one `re.search` per clause accepts a missing `;`
  between the clauses and a second, empty `misses:`.
- 50 — `scripts/check_task_review_contract.py:17`: the phrase pins do not cover the marker
  qualifiers ("skip this rule only", "Skip this step when the brief has no `Plan-contract: 2`
  line"), so a later edit that drops one still passes.
- 0 (unmodified line) — `skills/visual-planner/render_plan.py:243`: `Seams` renders inside the
  Interfaces cell with a literal `- **Seams:**` prefix. Accepted by design D1 (no high-blast
  renderer change); a display-only follow-up.

### Context-Propagation Audit

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `rules/plan-format.md` seam field + marker | `writing-plans` | main | explicit Read (`skills/writing-plans/SKILL.md:10`) plus inline step-3 summary | Read anchor present; SC-7 |
| `rules/plan-format.md` seam field + marker | plan document reviewer | reviewer | explicit Read (`plan-document-reviewer-prompt.md:5`) | Read anchor present |
| seam field + marker (shape) | `check_plan_contract.py` | SDD preflight, `writing-plans` step 5 | code | SC-1, SC-2 |
| task `Seams:` line + `- Plan-contract: 2` | implementer | implementer (same session and `resume <slug>`) | pasted: `task_brief.py` copies `## Global Constraints` and the whole task block, rebuilt from PLAN.md on every dispatch | SC-4 (`test_task_brief.py` on this plan) |
| task `Seams:` line + marker | task reviewer | reviewer | pasted via the same brief (`TASK_BRIEF_PATH`) | SC-4; canary and replay briefs held both lines |
| implementer test rules 1–7 | implementer | implementer | pasted (dispatch prompt template) | SC-3 phrase pins (`IMPLEMENTER_REQUIRED`) |
| reviewer seam check + search allowance | task reviewer | reviewer | pasted (dispatch prompt template) | SC-3 phrase pins (`REQUIRED`); canary run |
| old wording "Write tests. Follow TDD if the task says to." and paraphrases | any other file | any | — | `rg -i "write tests\|follow tdd\|test-first"` and `rg "Interfaces"` over the repo minus `specs/`, `openwiki/`, `.claude/`, `docs/research/`, `CHANGELOG.md`, `evals/`: only the changed files; quality-verdict descriptions in `agents/task-reviewer.md`, `skills/README.md`, `HARNESS.md`, `CLAUDE.md` name "spec and quality verdicts" without listing checks, so none contradicts the change |

Resume path: `resume <slug>` returns `execute-plan`, and the controller dispatches each pending
task through the same `task_brief.py` call (`skills/subagent-driven-development/SKILL.md:51`), so
the seam lines reach a fresh session's subagents with no session state. No inline policy subset
is unanchored: the prompt rules are consumer rules pinned by a drift test, and the field
definition reaches authors through an explicit Read.

**Verdict: PASS.**` if the workflow needed no change. -->

- none
