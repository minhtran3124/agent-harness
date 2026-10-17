# gh-318-diagnosing-bugs — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate — the change adds skills/diagnosing-bugs/SKILL.md and edits skills/feature-intake, skills/subagent-driven-development, skills/compound and skills/README.md (workflow-as-code); the user approved the intent with its three assumed defaults.
Flags: existing behavior, public contracts, audit/security, weak proof, multi-domain
Affects: workflow-engine (skills/feature-intake bug-fix routing, skills/subagent-driven-development review gate, skills/compound input, skills/README.md bug-fix path and handoff map)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no
<!-- Optional Codex diagnosis metadata is an all-or-nothing pair:
     Runtime-mode and Runtime-evidence-id. Add it only from codex_harness_doctor.py. -->

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

Intent-source: specs/gh-318-diagnosing-bugs/intent.md @ a82f1ba5b7c12130a6a3d64136901e19eb6938a9

run feature-intake for https://github.com/minhtran3124/agent-harness/issues/318

### Intake notes

<!-- Agent-written intake notes (confidence reasoning, assumed defaults, re-pin lines).
     Not part of the intent oracle. `- none` when empty. -->

- Confidence high: the user replied `approve` on 2026-10-17 to the draft with its three
  `(assumed)` defaults. (1) The skill sets `disable-model-invocation: true`, and `feature-intake`
  chains it by telling the agent to Read and follow `skills/diagnosing-bugs/SKILL.md`, not
  through the Skill tool. (2) `hitl-loop.template.sh` is written new in this repo, because
  `scripts/hitl-loop*` does not exist here and copying Pocock's text is out. (3) The task
  review of the diagnosis (Phases 1–4, `diagnosis.md`) happens before the Phase 5 fix task is
  dispatched.
- Input-type is `harness improvement`, not `bug fix`: the work adds a capability (a diagnosis
  step); no existing behavior is wrong.
- Dependencies met at intake: #308 is closed (completed); #313 step 1 merged in PR #328.
  `feature-intake` SKILL.md body is 461 words (`wc -w` on the non-frontmatter lines), so there is
  headroom under the 600-word ceiling.
- Issue #313 step 2 (routing to diagnosing-bugs) waits for this issue; check it during planning.
- Branch at intake: `sdlc`. `using-git-worktrees` cuts the implementation branch from it.

## What changed

- New `skills/diagnosing-bugs/` (600/600 words, `disable-model-invocation: true`): redaction rule first; isolation; six gated phases with `Done when:` lines; the loop runs with no pipe; `H1`–`H5` are written into `diagnosis.md` and committed before the first probe; `[DEBUG-xxxx]` probes; a `task-reviewer` diagnosis review that names `references/diagnosis-review-prompt.md`; Phase 5 red test then fix; Phase 6 cleanup. References: `phases.md`, `diagnosis-template.md`, `diagnosis-review-prompt.md`; `scripts/hitl-loop.template.sh` (original); `tests/routing-cases.md`. Registered in `harness-manifest.json`; audit test pins 15 skills / 12 prompts.
- `skills/feature-intake/SKILL.md`: `Input-type: bug fix` routes to the skill by the Read tool, never the Skill tool (closes #313 step 2).
- `skills/subagent-driven-development/`: `references/bug-fix.md` (diagnosis path in Context; seam-point check before dispatch; two-check budget), a pointer in `SKILL.md` (paid by a #308 deletion), Phase 6 in `references/review-chain.md`; `implementer-prompt.md` and `task-reviewer-prompt.md` accept a diagnosed `Seam: none — <reason>` with `Red test exempt`, and the red test targets `Confirmed:`.
- `rules/plan-format.md`: the diagnosed no-seam exception. `skills/writing-plans/SKILL.md` copies `Seam:` into `Seams:`. `skills/compound/SKILL.md` takes the bug root cause from `Confirmed:`.
- `skills/README.md`, `skills/xia2/README.md`: `systematic-debugging` replaced by `diagnosing-bugs` (bug-fix path, reference row, handoff map).
- `scripts/deploy-harness.sh` (DC1): derived Markdown rewrites the `skills/diagnosing-bugs/` prefix to `.claude/skills/diagnosing-bugs/`; `tests/scripts/consumer-subset.test.sh` pins it.
- Proof under `specs/gh-318-diagnosing-bugs/proof/`: routing logs from real `claude -p` runs with their extractor, and the replay transcript, order checker and fix diff.

### Rationale

The harness classified `Input-type: bug fix` but routed it to no diagnosis step, and the README pointed at an optional external skill. The skill closes Pocock's #578 (not model-invoked; intake chains it by Read), #124 (a `task-reviewer` gate before the fix) and #674 (redaction first). Proof runs drove four user-approved decision changes: DC1 deploy path rewrite, DC2 SC-28 accepts a Bash read, DC3 and DC4 move the ranked list into a committed `diagnosis.md` before any probe after two runs probed first. The 7.1 replay held the order but its setup leaked the answer, so DC5 ran one clean replay: no fix history, no test hints. There the model found the true cause on its own, held the order (red loop, committed list, probe, review), and its fix turned the test green.

### Alternatives considered

- Design approach B (a `scripts/check_diagnosis.py` checker) and C (a diagnosis mode inside `feature-intake`) were rejected in `design.md`.
- DC2: strengthen the routing line to force the Read tool, or record SC-28 as failed — rejected for widening SC-28 to a Bash read.
- DC4: record list-before-probe as a known limitation — rejected for the committed-list gate.

### Deviations

- Decision changes DC1–DC6 (user approved; `design.md` `## Decision changes`, D14–D17): deploy rewrite; SC-28 widened; D6 → D16 → D17 list-before-probe gate; DC5 clean replay without fix history or test hints; DC6 post-run loop-input rule (stated as post-run). Plan tasks 4.1, 4.2, 5.1, 6.1, 6.2, 7.1, 8.1 added.
- Controller fixture (Task 3.1): `scripts/x.sh` added as a fixture commit in the scratch project; without it intake rightly stopped at low confidence.
- Task 4.2 (Rule 1): `proof/transcript.py --help` returned 2; a help branch was added.
- Task 3.2 loop input `loop.sh` was a post-run judgment call (not Rule 1); Tasks 5.1 and 7.1 pinned the rule before the run.
- Minor findings and fix rounds: `specs/gh-318-diagnosing-bugs/review-ledger.md`.
- Correctness review round 1 (Rule 1, `168345c`): L1 the HITL template now has an exit contract (1 red on `SYMPTOM_SEEN=yes`, 0 green, 2 no terminal / end of input / bad answer); L2 internal names use a `__hitl_` prefix that `capture` rejects; L4 `Red test exempt:` goes in SUMMARY `### Verify`; L5 the tiny lane cuts `fix/<slug>` only from a shared branch. #308 deletions: Phase 4 "Start no probe before that commit." (kept in Phase 3 and `diagnosis-template.md`).
- Re-score follow-up (Rule 1, `a411aa9`): N1 the human runs the HITL copy (an agent Bash call has no terminal, so the copy exits 2); D-b the retry after a failed diagnosis review is restored and defines failure. #308 deletion: Phase 6 "The session that completed the fix does this phase." (`references/review-chain.md` assigns Phase 6 to the SDD controller; the tiny lane has one session).

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane evidence | `python3 .claude/scripts/verify_summary.py --lane gh-318-diagnosing-bugs` | 0 | intake-time check only | |
| skill flag | `grep -qx "disable-model-invocation: true" skills/diagnosing-bugs/SKILL.md` | 0 | | SC-1 |
| word ceiling | `python3 scripts/audit_skill_prompts.py` | 0 | diagnosing-bugs 599, sdd 596, intake 564 | SC-2 |
| audit surface | `python3 -m pytest -q scripts/test_audit_skill_prompts.py` | 0 | 15 skills, 12 prompts | SC-3 |
| manifest | `python3 scripts/check_manifest.py` | 0 | | SC-4 |
| tool conformance | `python3 scripts/check_skill_tool_conformance.py` | 0 | | SC-5 |
| allowed-tools | `bash scripts/check-allowed-tools.sh` | 0 | | SC-6 |
| runtime-neutral | `python3 scripts/check_runtime_neutral_sources.py` | 0 | | SC-7 |
| doc truth | `bash scripts/lint-doc-truth.sh` | 0 | | SC-8 |
| skill bash lint | `bash scripts/lint-skill-bash.sh` | 0 | syntax only, no shellcheck here | SC-9 |
| hitl syntax | `bash -n skills/diagnosing-bugs/scripts/hitl-loop.template.sh` | 0 | | SC-10 |
| redaction | `grep -q "<REDACTED>" skills/diagnosing-bugs/SKILL.md` | 0 | | SC-11 |
| intake route | `grep -q "skills/diagnosing-bugs/SKILL.md" skills/feature-intake/SKILL.md` | 0 | | SC-12 |
| no external skill | `grep -q systematic-debugging skills/README.md skills/xia2/README.md` | 1 | no match | SC-13 |
| handoff row | `grep -qE "^diagnosing-bugs +──►" skills/README.md` | 0 | | SC-14 |
| plan-format seam none | `grep -q "Seam: none" rules/plan-format.md` | 0 | | SC-15 |
| implementer seam none | `grep -q "Seam: none" skills/subagent-driven-development/implementer-prompt.md` | 0 | | SC-16 |
| reviewer seam none | `grep -q "Seam: none" skills/subagent-driven-development/task-reviewer-prompt.md` | 0 | | SC-17 |
| phrase pins | `python3 scripts/check_task_review_contract.py` | 0 | | SC-18 |
| seam check ref | `grep -q "Seam:" skills/subagent-driven-development/references/bug-fix.md` | 0 | | SC-19 |
| sdd pointer | `grep -q "references/bug-fix.md" skills/subagent-driven-development/SKILL.md` | 0 | | SC-20 |
| phase 6 in chain | `grep -qF "[DEBUG-" skills/subagent-driven-development/references/review-chain.md` | 0 | | SC-21 |
| writing-plans seam | `grep -q "diagnosis.md" skills/writing-plans/SKILL.md` | 0 | | SC-22 |
| compound input | `grep -q "diagnosis.md" skills/compound/SKILL.md` | 0 | | SC-23 |
| STE baseline | `python3 scripts/check_ste_baseline.py --strict --against 09a7985` | 0 | 79 files, 0 above | SC-24 |
| plan contract | `python3 scripts/check_plan_contract.py specs/gh-318-diagnosing-bugs/PLAN.md` | 0 | | SC-25 |
| quick question reached intake | `grep -qE "^[A-Z][A-Za-z]+ .*feature-intake" specs/gh-318-diagnosing-bugs/proof/quick-question.md` | 0 | real claude -p run | SC-26 |
| quick question no skill read | `grep -qE "^[RB][a-z]+ .*diagnosing-bugs/SKILL\.md" specs/gh-318-diagnosing-bugs/proof/quick-question.md` | 1 | no match | SC-27 |
| bug fix read the skill | `grep -qE "^[RB][a-z]+ .*diagnosing-bugs/SKILL\.md" specs/gh-318-diagnosing-bugs/proof/bug-fix-routing.md` | 0 | Bash sed read (DC2) | SC-28 |
| no Skill call | `grep -qx "Skill diagnosing-bugs" specs/gh-318-diagnosing-bugs/proof/bug-fix-routing.md` | 1 | no match | SC-29 |
| replay order | `python3 specs/gh-318-diagnosing-bugs/proof/check_replay.py specs/gh-318-diagnosing-bugs/proof/replay.md` | 0 | LOOP-RED@9 HYPOTHESIS@12 PROBE@13 REVIEW@20 | SC-30 |
| no debug tags in fix | `grep -qF "[DEBUG-" specs/gh-318-diagnosing-bugs/proof/replay-diff.patch` | 1 | no match | SC-31 |
| context propagation pins | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | | SC-32 |
| consumer deploy path | `bash tests/scripts/consumer-subset.test.sh` | 0 | 21 passed | SC-33 |
| list before probe | `grep -q "before the first probe" skills/diagnosing-bugs/SKILL.md` | 0 | | SC-34 |
| loop with no pipe | `grep -q "with no pipe" skills/diagnosing-bugs/SKILL.md` | 0 | | SC-35 |
| commit before probe | `grep -q "Commit diagnosis.md before the first probe" skills/diagnosing-bugs/SKILL.md` | 0 | | SC-36 |
| clean replay order | `python3 specs/gh-318-diagnosing-bugs/proof/check_replay.py specs/gh-318-diagnosing-bugs/proof/replay-clean.md` | 0 | LOOP-RED@8 HYPOTHESIS@11 PROBE@12 REVIEW@24; DC6 post-run loop rule | SC-37 |
| clean replay no debug tags | `grep -qF "[DEBUG-" specs/gh-318-diagnosing-bugs/proof/replay-clean-diff.patch` | 1 | no match | SC-38 |
| clean replay no fix commit | `grep -q "ac7f472" specs/gh-318-diagnosing-bugs/proof/replay-clean.md` | 1 | no match | SC-39 |

### Not auto-verified

- The lane and flags are correct for the final diff — reached traceability; commit-gate risk corroboration re-checks the lane at commit time.
- Unaided diagnosis — shown in one clean run only (DC5, `proof/replay-clean.md`): an ancestry-only clone where `git cat-file -e ac7f472` exited 128, and a comment-stripped test overlay with 0 `have_tty`. The model committed H1–H4, confirmed H1 (the true cause) by its own probe, and its one-line fix turned the test green (21 passed). Tier: traceability for order; the green test was re-run once by the implementer before cleanup and is not re-runnable from the repo. One sample, one model (claude-sonnet-5-5), CLI 2.1.302.
- The earlier replays (3.2, 5.1, 7.1) were not blind. Their test overlay named the cause and fix in comments, and 7.1 also reached fix commit ac7f472 through the shared worktree object store and copied it. They count as order evidence only (`proof/replay.md`).
- SC-37 passes only under the DC6 loop-input rule, which was changed after the run. The strict conversion fails, and it is kept as `proof/replay-clean-strict.md`. The rule as applied gives `"$PWD"`, not the script name; the conversion is byte-identical either way.
- The PROBE marker also matches commands that only search for `[DEBUG-` (Phase 6 cleanup lines). It did not move the first PROBE in any run.
- The clean run controlled only two leak channels: fix history and test comments. Not controlled: the guard's own history, which the model read with `git log -L` (it showed 104d85e), and the model's prior knowledge. The clean-clone state (`git cat-file -e ac7f472` exit 128) and the green test (21 passed at 88f4ab4) are implementer-reported. Neither can be re-run from the repo, because the clone was deleted.
- The `"$PWD"` loop input is a broad match. Its byte-identity with the `loop.sh` conversion is the implementer's scratch `cmp`. `proof/replay-clean-strict.md` is byte-identical to the original conversion (`git diff --exit-code c5e9d82:…/replay-clean.md 017e017:…/replay-clean-strict.md`, exit 0, run by the controller).
- The model's fix covers `deploy-harness.sh` only. It flagged the same `-r /dev/tty` pattern at `scripts/install-harness.sh:133` and left it unfixed (out of scope here).
- Phase order (red loop, committed list, probe, review) — traceability, one sample on one model (claude-sonnet-5-5) and CLI 2.1.302. Two earlier runs probed first (`review-ledger.md`).
- SC-28 shows a tool call named the skill path, not that the read succeeded (`is_error=False` was checked by hand). SC-27 and SC-29 cover main-thread calls only.
- The SC-30 HYPOTHESIS marker does not check which file a call writes. The first HYPOTHESIS line was checked by hand: it writes and commits `diagnosis.md`.
- Codex handling of `disable-model-invocation` — unknown.
- Whole suite (cited in prose, not a Verify row, per `rules/plan-format.md` Guardrail 4): `bash scripts/run-tests.sh` exit 0 at `a411aa9`, "1059 passed, 1 skipped … ALL GREEN"; also exit 0 at `f27c305` (intent reviewer) and `168345c`. Truth tier at those commits only.
- HITL template exit codes (L1) were exercised under a real terminal via `pty.fork()` by the fixer and the re-scorer (yes 1, no 0, other 2, end of input 2). No committed test pins them; the no-terminal case was run only by the fixer.

### Correctness Review

Run on `09a7985..f27c305`; blocking threshold 75.

| Id | Finding | Score | Outcome |
| --- | --- | --- | --- |
| L1 | HITL template always exited 0, so a human-action loop could not go red | 75 | fixed `168345c`; re-score 10 |
| L4 | `Red test exempt:` written outside `### Verify`, where `verify_summary.py` reads it | 75 | fixed `168345c`; re-score 15 |
| L5 | tiny lane `git checkout -b` collided with the branch intake already cut | 75 | fixed `168345c`; re-score 20 ("shared branch" defined only in `rules/auto-correct-scope.md`) |
| L2 | internal template names could collide with a `capture` name | 50 | fixed `168345c`; re-score 10 (a capture can still set `PATH`/`IFS`) |
| L3 | the Phase 6 `[DEBUG-` search matches its own command text | 50 | advisory, not fixed |
| L6 | an untagged throwaway harness survives the Phase 6 search; a harness-based loop deleted in Phase 4 leaves Phase 6 nothing to re-run | 50 | advisory, not fixed |
| L7 | `run_review_prompt_eval.py` leaves the `DIAGNOSIS_PATH` placeholder unfilled (unmodified line) | 0 | advisory, one-line fix for a follow-up |
| L8 | legacy seam exemption scope at `implementer-prompt.md:64` | 50 | advisory, not fixed |
| N1 | (re-score) the agent cannot run the HITL copy; nothing said who runs it | 40 | fixed `a411aa9` |
| D-b | (re-score) the deleted review-retry sentence did not survive the #308 test | 55 | fixed `a411aa9` |
| N2 | (re-score) yes/no match is case-sensitive; `Yes` exits 2 (fails safe) | 15 | advisory, not fixed |
| R1 | (re-score of `a411aa9`) Phase 6 and `review-chain.md:5` say "Run the Phase 1 loop again"; for a HITL loop the agent must ask the human, and neither place says so | 30 | advisory, follow-up (needs words at the 600 ceiling) |
| R2 | (re-score of `a411aa9`) the template never prints its exit code, so a pasted HITL run shows red only by `SYMPTOM_SEEN=yes`; "run it" could mean the template, not the copy | 30 | advisory, not fixed |
| R3 | (re-score of `a411aa9`, predates it) `review-chain.md:6` searches the "branch diff" and omits "untracked files included", which SKILL.md Phase 6 names | 15 | advisory, not fixed |

Re-score of `a411aa9`: N1 30, D-b 10, Phase 6 deletion 15 (the rule holds via `review-chain.md:3-8` and the tiny lane's single session), Phase 1 wording 5. None blocking.

### Intent Findings

Intent review at `f27c305`, blind to PLAN tasks: no blocking gap.

| # | Class | Finding | Outcome |
| --- | --- | --- | --- |
| 1 | drift (equivalent) | the gate before Phase 5 is a separate `task-reviewer` diagnosis review, not SDD's per-task review | user-approved D5; recorded |
| 2 | drift | the skill never waits for the user's re-rank, even when present; adds commit-before-probe | user-approved D6 → D16 → D17; recorded |
| 3 | drift (equivalent) | "chain-invoked" is a Read-and-follow, not a Skill call | user-approved D1/D15, DC2; recorded |
| 4 | drift (behavior) | HITL loop cannot go red by exit code | same as L1; fixed `168345c` |
| 5 | excess | seam-point check before dispatch, `rules/plan-format.md` exception, writing-plans copy, task-reviewer `DIAGNOSIS_PATH` | report-only (D12/D13) |
| 6 | excess | `scripts/deploy-harness.sh` rewrite | report-only; user-approved DC1 |
| 7 | excess | `tests/routing-cases.md` manual canary table | report-only |
| 8 | gap (evidence) | no record of `bash scripts/run-tests.sh` | recorded in prose under `### Not auto-verified` |

### Context-Propagation Audit

Result: **PASS** at `bdc0025` (first pass at `8a7ec89`: FAIL on F1 and F2, repaired by Task 9.1, then re-audited).

| Source | Consumer | Context | Delivery | Proof | Result |
| --- | --- | --- | --- | --- | --- |
| feature-intake `## Routes` bug-fix line | feature-intake | main, new session | skill body | `proof/bug-fix-routing.md` (Skill feature-intake, then a read of the diagnosing-bugs SKILL.md, no Skill call) | PASS |
| same line, consumer copy | consumer install | main | deploy rewrite | `deploy-harness.sh` rewrite; `consumer-subset.test.sh` | PASS |
| diagnosing-bugs SKILL.md phases | session that ran intake | main | explicit Read | `proof/replay-clean.md` | PASS |
| `diagnosis-review-prompt.md` | task-reviewer | fresh reviewer | explicit Read, required by SKILL.md (Task 9.1) | diagnosing-bugs SKILL.md Diagnosis review; `agents/runtime-bindings.json` (Read tool) | PASS (F1 repaired) |
| SDD pointer to `references/bug-fix.md` | SDD controller | main, `resume <slug>` | skill body, then explicit Read | SDD SKILL.md "Execute waves" | PASS |
| review-chain diagnosed Phase 6 | SDD controller | main, `resume-review-chain` | explicit Read | SDD SKILL.md, `references/resume.md` | PASS |
| implementer `Seam: none` exemption, `Confirmed:` target | coding implementer | implementer | template pasted; diagnosis path in Context | `implementer-prompt.md`; `bug-fix.md` | PASS |
| task-reviewer step-4 skip | task-reviewer | fresh reviewer | `DIAGNOSIS_PATH` input (Task 9.1); `none` fails closed | `task-reviewer-prompt.md`; `bug-fix.md` `## Task review` | PASS (F2 repaired) |
| `rules/plan-format.md` exception | writing-plans, plan reviewer, SDD preflight | main, reviewer | explicit Read | writing-plans SKILL.md; plan-document-reviewer-prompt.md; SDD SKILL.md Preflight | PASS |
| writing-plans seam copy | writing-plans | main | skill body; backstop: SDD seam check | writing-plans SKILL.md; `bug-fix.md` | PASS |
| compound root cause from `Confirmed:` | compound passes | main | skill body (passes run in the main loop) | compound SKILL.md | PASS |
| deploy rewrite of `skills/diagnosing-bugs/` | consumer Markdown | consumer | prefix regex over derived `.md` | `deploy-harness.sh`; `consumer-subset.test.sh` pins two paths | PASS |
| READMEs | none at runtime | — | documentation; `skills/xia2/README.md` is harness-only | `deploy-harness.sh` `HARNESS_ONLY_DOCS` | PASS (not load-bearing) |

Open notes (not FAIL): SDD SKILL.md "Pass brief/report/package paths" does not name `DIAGNOSIS_PATH` (the template carries it; a missing value fails closed); no test pins the rewrite of the review-prompt path; no drift test ties the three "same reason" rules together; nothing resumes an interrupted diagnosis (Phases 1–4) in a new session; a `Loop:` command in a session scratchpad may not exist for a resumed Phase 6.

### Rollback

- `git revert <sha>` for each implementation commit; the new skill directory is additive, so reverting removes it.
- `scripts/deploy-harness.sh` rewrite: `git revert 5af53e6 d4d7507`, then re-sync consumers with `bash scripts/deploy-harness.sh --target <consumer>`.

### Harness-Delta

- backlog: `/feature-intake` was not registered as a slash command in this cloud session, though `.claude/skills/feature-intake/SKILL.md` was loaded and invocable through the Skill tool. The cause was not found in the repo.
- backlog (→ compound): replay proofs leak the answer — a `git worktree` shares the object store (`git log --all` reaches the fix commit), and the chosen test overlay names the fix in comments. Use an ancestry-only clone and a hint-free overlay.
- backlog: a prose order rule ("post the list before probing") did not hold in 2 of 2 runs; a committed artifact did hold in 1 of 1.
- backlog: in a worktree-isolated session the sandbox refuses compound shell lines and text that names git; briefs should say so up front.
- backlog: a Done line that names a command (`transcript.py --help`) was not run by the task that wrote the file.
- backlog (→ compound): "no real terminal run is possible here" was false — `pty.fork()` gives a child a controlling terminal. A pty-driven test in `tests/scripts/` could pin the HITL exit contract (yes 1, no 0, other 2, end of input 2, no terminal 2).
- backlog: at the 600-word ceiling every fix needs a #308 deletion; one deletion (the review-retry sentence) failed the test on re-score. A re-scorer should check each deletion, not only the fix.
