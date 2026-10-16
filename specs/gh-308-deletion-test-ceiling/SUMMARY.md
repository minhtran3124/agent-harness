# gh-308-deletion-test-ceiling — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate (edits skills/session-retro, skills/feature-intake, skills/finishing-a-development-branch, skills/asd-ste100 and the task-reviewer dispatch prompt); also adds a script to the review package
Flags: existing behavior, weak proof, multi-domain
Affects: skills/feature-intake (routes every change), skills/subagent-driven-development (task-reviewer-prompt.md, scripts/review_package.py), scripts/audit_skill_prompts.py
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/gh-308-deletion-test-ceiling/intent.md @ 0c403b7adca3d4e0cf1cbe08821cf94a953b279b

start for #308

Issue #308, as referenced (https://github.com/minhtran3124/agent-harness/issues/308):

> **Phase 0: make room.** Roadmap: https://claude.ai/artifact/AohXkjEsZKRDXhHheAsrtW
>
> Goal: Meet the 600-word skill ceiling with a deletion test. Delete whole sentences. Do not trim
> words.
>
> Steps: (1) In `scripts/audit_skill_prompts.py`, replace the word-count failure message with this
> procedure: list each sentence; ask: does the model already do this by default?; if yes, delete
> the whole sentence; do not shorten a sentence that contains a condition word. (2) Add the same
> procedure to the STE-flavored mode of `skills/asd-ste100/SKILL.md`. (3) Promote the two open
> rows dated 2026-10-15 in `docs/harness-experimental/improvement-backlog.md`: a
> meaning-equivalence instruction in the spec verdict of `task-reviewer-prompt.md`, and
> `scripts/check_scope_qualifiers.py` as an advisory section of the review package beside
> `## STE lint`. (4) Apply the procedure to `session-retro` (600 words), `finishing-a-development-branch`
> (589), `feature-intake` (598). Free at least 60 words in each.
>
> Lane: normal, with a context-propagation-audit. Dependencies: none; blocks #310, #312, #313.
> Proof: run `scripts/run_task_review_eval.py` and `scripts/score_task_review_eval.py` on the three
> edited skills with the condition-word list as the observable; pass = zero lost conditions;
> record beside the A/B in `rules/terminology.md`.

### Intake notes

- The issue body proposes lane `normal`. The manifest's `workflow-engine` hard gate (warn-mode at commit, but a hard gate for classification) covers `skills/*/SKILL.md` and dispatch prompts, so intake assigns `high-risk`. The human did not narrow scope.
- Confidence high: one clear reading; the issue lists the files, steps and proof.
- Assumed defaults carried from intent.md: `check_scope_qualifiers.py` is advisory only; the proof may need a new task-review eval fixture (xia2 decides).
- 2026-10-16 re-pin: intent.md 03e3555 → 0c403b7, amended per ESCALATIONS E001 decision A (design D1, D2, block-move rule, "at least 60 words under 600"). Re-classified: lane, confidence, flags and route unchanged.
- Self-reference risk: step 4 edits `feature-intake`, the skill that classified this work. The context-propagation audit must confirm its routing and gates survive the deletion.

### Correctness Review

Range `cc366fd..8d7ca01`, review package `.harness-state/sdd/package-branch.md`, six plan-blind FIND angles, threshold 75 (`skills/correctness-review/review-config.json`). Three deduplicated locations were scored in fresh contexts; none reached the threshold, so no fix round ran. Blocking findings: 0.

Advisory (below threshold, recorded for a human):

- score 25 — `skills/feature-intake/SKILL.md:34` (Step 4). The deleted "Low confidence always stops for a human." is still delivered by `rules/orchestration.md:125`, which Step 1 always reads and which is always-on. Residual gap: `skills/feature-intake/tests/confidence-escalation-cases.md` still says it pins the CE-02/CE-03 "escalates at any lane" behavior to Step 4, and Step 4 no longer states it. Follow-up: point those canaries at the `rules/orchestration.md` escalation section, or restore a short `low` → `Escalate: yes` clause once #308's headroom allows.
- score 0 (pre-existing) — `skills/finishing-a-development-branch/SKILL.md:58`. The stage/commit/push of `RUN.json` and `events.jsonl` after `run_state.py transition --to ready_to_merge … || true` is unconditional and names the files without `specs/<slug>/`; the base text had the same shape. When the transition fails silently (FORWARD_TRANSITIONS allows `ready_to_merge` only from `verifying`, `awaiting_ci`, `awaiting_review`; a tiny run stays `investigating`), the commit finds nothing. Follow-up: commit only when the two files changed, and write the full paths.
- score 0 (pre-existing, moved verbatim) — `skills/finishing-a-development-branch/references/run-state-handoff.md:9`. "the commit gate (Check 1.7)" names a label that `hooks/commit-gate.sh` does not contain; the gate is `check_run_state` (`hooks/commit-gate.sh:320`). Follow-up: rename the reference.

Finder notes (no trigger, not scored): the `(shipped in 23438c1)` note in `docs/harness-experimental/improvement-backlog.md` cites a follow-up fix commit, not the commit that first added the guardrails; the hint lines of the audit message carry no `prompt-audit:` prefix (same as the Task 1.1 Minor).

### Intent Findings

Intent review, plan-blind, oracle = `intent.md` @ `03e3555` plus the chat request; range `cc366fd..8d7ca01`. Nine findings. Rows 1–5 are routed to `ESCALATIONS.md` E001 (one decision: amend and re-pin `intent.md`, or do the missing work). Rows 6–9 are recorded here.

- Escalated (E001): (1) gap — `skills/asd-ste100/SKILL.md` does not state the procedure (design D1 replaced it with a KB entry). (2) gap — no blind task-review run recorded in `rules/terminology.md` (design D2). (3) drift — design and plan SCs carry neither item. (4) gap, marginal — `feature-intake` freed 59 words, not 60 (it is 61 under 600, so the success line holds). (5) drift — `feature-intake` replaced the artifact list with a pointer instead of deleting whole sentences only.
- Advisory drift, behaviorally equivalent: (6) `finishing-a-development-branch` moved two blocks to `references/run-state-handoff.md` and reworded one antecedent; all four condition words are cited at HEAD. (7) the audit hint is one line plus a pointer to the KB entry, and does not spell out "list each sentence" or "ask whether the model already does it by default"; the KB entry has the full procedure. (8) the qualifier script and reviewer meaning step predate this branch (`23438c1` is an ancestor of `cc366fd`); this branch only marks the backlog rows done.
- Excess, report-only: (9) `harness-manifest.json` consumer fix (follows from the pointer deletion), the new reference file, and its `scripts/ste-baseline.json` entry.
- Not checkable from the diff: "PR targets `sdlc`" (`unknown` until the PR exists).
- Corrected after review: the SC-4 Verify note listed the counts unlabeled and in a different order; it now names each skill.

Second pass, after E001 decision A and the re-pin to `0c403b7` (range `cc366fd..8d7ca01`): six findings.

- (1) drift, fixed in `4a3b4a1` — the reference and the audit hint gave a second deletion criterion ("restates a file the skill already points to") that the amended intent does not state. Recast as an instance of the single default-behavior test, limited to files the skill makes the model read (a required Read step or an always-loaded rule); a bare pointer does not count. The hint now also says "list each sentence". Every `feature-intake` deletion relied on Step 1's required Read or an always-loaded rule, so the trims still meet the narrowed rule.
- (2) advisory drift — the hint left out "list each sentence"; closed by the same fix.
- (3) advisory drift — the finishing move covers "why" text that every PR path reaches, and one antecedent was reworded ("Then stage exactly `RUN.json` and `events.jsonl`"); the `feature-intake` artifact list became a new pointer sentence. No condition lost.
- (4) advisory drift, not triggered — design SC-3 / plan SC-4 and reference step 5 allow a "kept long on purpose" shortfall the intent does not; all three skills met the budget, so it was not used.
- (5) excess, report-only — the `harness-manifest.json` consumer fix.
- (6) unknown — "PR targets `sdlc`"; checked at finish.

Third pass, range `cc366fd..4a3b4a1`: seven findings.

- (1) gap, fixed by recording — the per-file task-review meaning verdicts were not in the spec record; now in `### Task review meaning verdicts` above (all `pass`).
- (2) advisory drift, not triggered — the KB entry keeps the "kept long on purpose" exit; the intent sets a fixed target. All three skills met the target.
- (3) advisory drift — the finishing move covers main-path rationale, not a branch-only block; the instructions stay inline and all 4 condition words are kept whole.
- (4) advisory drift — "So stage exactly those two paths" became "Then stage exactly `RUN.json` and `events.jsonl`"; no condition word involved.
- (5) advisory drift — the hint merges "ask whether" into "delete a whole sentence the model already does by default"; the KB entry has the full procedure.
- (6) excess, report-only — the `harness-manifest.json` consumer fix.
- (7) excess, report-only — the KB entry adds an upstream attribution and two operating tips (grep tests and hooks before deleting; no `prompt` in new reference names).

### Follow-up on PR #319

Request, verbatim (chat, after PR #319 opened), quoting two of the recorded advisories:

> """
>   - Bước commit run-state trong finishing không có điều kiện, và nhãn "Check 1.7" đã cũ. Cả hai lỗi này có từ trước nhánh này.
>   - Một comment trong test đã cũ.
> """
> fix both first, do on this PR

Fixed in `b08da10`:

- `skills/finishing-a-development-branch/SKILL.md` "Push and PR": the run-state commit now runs only if `git status --short` shows a change to `specs/<slug>/RUN.json` or `specs/<slug>/events.jsonl`, and names both with full paths (536 words, budget 540). Closes the score-0 correctness advisory at `SKILL.md:58`.
- `skills/finishing-a-development-branch/references/run-state-handoff.md`: "Check 1.7" → "`check_run_state` in `hooks/commit-gate.sh`". Closes the score-0 advisory at `run-state-handoff.md:9`. Dated historical records that still say "Check 1.7" (`docs/harness-experimental/trust-metrics.md:115`, older `specs/*`) are left as written.
- `tests/scripts/context-propagation-regression.test.sh:237-239`: comment only; it no longer says feature-intake points to `rules/research-depth.md`. Closes the Task 2.2 Minor.

Reviews of `098c160..b08da10`: task review spec pass, quality approved (`meaning: pass` for both prose files, STE 0 → 0); focused correctness re-review 0 bugs (traced success, no run, a state that cannot move to `ready_to_merge`, and a re-run); intent review against the request above: no divergence.

- Bookkeeping: the "unless" citation in `qualifiers-finishing-a-development-branch.md` quoted the old "(Check 1.7)" wording, so `check_gh308.py qualifiers` (SC-5) failed after `b08da10`; the citation now quotes text present at HEAD. The condition itself is unchanged. SC-5 and `verify_summary.py --check` exit 0 again.
- Minor (task review, recorded): the new condition tests whether the files are dirty, not whether the transition changed them; uncommitted edits made before the transition would also be committed. Step 3 commits both files just before, so the window is small.

## What changed

The 600-word skill ceiling now has a written procedure: `docs/solutions/harness/deletion-test-for-word-ceiling.md` (a knowledge entry, adapted from Pocock's `writing-for-agents` deletion test plus the local condition-word guard), and the over-ceiling message of `scripts/audit_skill_prompts.py` points to it. The procedure was applied once: `finishing-a-development-branch` 589 → 524 words (run-state rationale moved whole to `references/run-state-handoff.md`), `feature-intake` 598 → 539 (sentences that restate rules it already reads were deleted; Steps 1, 3, 6, 7 and the tiny route untouched), `session-retro` 600 → 525 (opening framing and a list that repeats the lever table deleted). The two 2026-10-15 `ste-rewrite-drops-scope-qualifiers` backlog rows are marked done, because their guardrails already shipped. A spec-local `check_gh308.py` makes the budget, qualifier, backlog and STE-ratchet criteria decidable. One registry entry in `harness-manifest.json` was corrected (Deviations).

### Rationale

The recorded failures came from trimming words to meet the ceiling, which drops cheap condition words. Deleting whole sentences, or moving whole blocks behind a pointer, either keeps a condition intact or removes it where the qualifier check and the reviewer's meaning step can see it. The procedure lives in a harness-owned KB entry because `skills/asd-ste100` is a vendored upstream copy whose `UPSTREAM.md` allows no further differences (user chose option A, design D1). Proof reuses the shipped qualifier check and reviewer meaning verdict rather than a new eval (user chose option A, design D2).

### Alternatives considered

- Procedure only in the audit message — smallest, but nothing else can link to it.
- Edit `asd-ste100` and record a fourth upstream difference — keeps issue step 2 literally, but adds re-vendor work on every upstream change.
- A new blind task-review eval recorded beside the A/B in `rules/terminology.md` — rejected; that file records controlled-language experiments and the change would add another workflow-engine file.
- A new mechanical "deletion-only" checker — no recorded failure it alone would catch beyond the qualifier check and reviewer.

### Deviations

- Rule 1 — `harness-manifest.json` contract `research-depth-policy` still listed `skills/feature-intake/SKILL.md` as a consumer after Task 2.2 deleted the pointer to `rules/research-depth.md`; `scripts/check_manifest.py` checks only that consumer paths exist, so it did not catch it. Dropped feature-intake from that list (xia2 reads the rule itself). Found by the context-propagation audit. Outside the plan's Files set.

### Context-Propagation Audit

Trigger: the branch changes `skills/feature-intake/SKILL.md`, `skills/session-retro/SKILL.md`, `skills/finishing-a-development-branch/SKILL.md` and adds `skills/finishing-a-development-branch/references/run-state-handoff.md` (workflow-engine gate). Search surface for consumers: `scripts/`, `tests/`, `hooks/`, `rules/`, `skills/`, `agents/`, `docs/`, `adapters/codex/`, `harness-manifest.json` (grep for each moved/deleted phrase and for `research-depth-policy`).

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| finishing run-state rationale (moved to `references/run-state-handoff.md`) | `finishing-a-development-branch` | main session | explicit Read via three pointers (SKILL.md:48, :60, :72); the instructions it explains stay inline | inspected SKILL.md at HEAD; redeploy put `.claude/skills/finishing-a-development-branch/references/run-state-handoff.md` in the target with 3 pointers; `scripts/render_codex_adapter.py:253` copies each skill folder whole |
| finishing `--to ready_to_merge --event pr.opened \|\| true` and the stage/commit-again step | same | main session | inline (unchanged) | `tests/scripts/finishing-branch-contract.test.sh` exit 0 |
| "The lane is risk. Confidence is ambiguity." (deleted) → `rules/orchestration.md` | `feature-intake` | main session; intake eval child (`scripts/run_intake_eval.py`, `--setting-sources project`, not `--bare`); Codex session | always-loaded (no `paths:`), and explicit Read in Step 1 | `head` of `rules/orchestration.md` has no `paths:`; Step 1 at HEAD names it; eval runner rejects `--bare` (L112-113) |
| "Low confidence always stops for a human." (deleted) → `rules/orchestration.md` escalation list | same | same | same | same; the Codex plugin ships no rules, so Codex relies on the Step 1 explicit Read |
| "All lanes require branch isolation." (deleted) → `rules/auto-correct-scope.md` | same | same | explicit Read in Step 1 (rule is path-scoped); also the tiny route "branch" and `hooks/branch-isolation-guard.sh` | Step 1 at HEAD names it; `head` shows `paths:` frontmatter, so the explicit Read is the delivery |
| Artifact-by-signal list (replaced by pointer) → `rules/orchestration.md` | same | same | explicit Read in Step 1 + one-line pointer | SKILL.md:69 at HEAD |
| xia2 lane-to-depth pointer (deleted) → `rules/research-depth.md` | `xia2` (the real consumer) | main session; xia2 child | explicit Read in xia2 "Decide depth" | `skills/xia2/SKILL.md:17,50,60`; manifest registry corrected (Deviation above) |
| "`$ARGUMENTS` is the requested change." (deleted) | `feature-intake` | main session; Codex session | runtime argument delivery: in this session, skills without a `$ARGUMENTS` placeholder received an appended `ARGUMENTS:` block (writing-plans, subagent-driven-development); 12 of 14 skills already have no placeholder | observed in this session (main context only); Codex argument handling: `unknown` — no `ARGUMENTS` match in `adapters/codex/` or `scripts/render_codex_adapter.py` |
| session-retro framing and friction list (deleted) | `session-retro` | main session only (`disable-model-invocation: true`) | inline lever table, clean-run stop, routing line kept | inspected SKILL.md at HEAD; eval-corpus behaviors present (`scripts/generate_skill_eval_corpus.py:65-70`) |

Result: **PASS**, with one repaired row (the manifest registry) and one `unknown` row. The `$ARGUMENTS` row is not load-bearing for Claude Code: the same argument delivery already serves 12 of 14 skills that never had the placeholder. For Codex it is unknown, and it was unknown before this change for those 12 skills as well; recorded for intent and correctness review.

### Task review meaning verdicts

Per-file `meaning:` verdicts returned by the independent task reviewer (read-only `task-reviewer` agent, `skills/subagent-driven-development/task-reviewer-prompt.md`) for each changed skill file. Each review read its own `BASE..HEAD` package, including the `## Scope qualifiers` section, and resolved every listed condition word.

| Task | Range reviewed | File | meaning | Scope-qualifier lines resolved |
| --- | --- | --- | --- | --- |
| 2.1 | `995c433..970a276` | `skills/finishing-a-development-branch/SKILL.md` | pass | 4 of 4 kept (unless, only, never, without), each cited at `references/run-state-handoff.md:9,13,14,16` |
| 2.1 | `995c433..970a276` | `skills/finishing-a-development-branch/references/run-state-handoff.md` | pass | new file; holds the 4 moved sentences |
| 2.2 | `44d7061..63f1ef1` | `skills/feature-intake/SKILL.md` | pass | section was `- none`; each removed line compared by hand to the rule file that keeps it |
| 2.3 | `970a276..44d7061` | `skills/session-retro/SKILL.md` | pass | section was `- none`; each removed sentence compared by hand to the HEAD line that keeps it |

Tasks 1.1, 1.2 and 3.1 changed no file under `skills/`, `rules/` or `agents/` (`meaning: []`). The intent-alignment fix `4a3b4a1` changed no skill file (`meaning: pass` for its two non-skill files).

### Task review minor findings

- Fix `4a3b4a1` (Minor, quality): `scripts/audit_skill_prompts.py` — the hint names only "a file the skill makes it read"; the reference also counts an always-loaded rule. The hint points to the reference, which has both cases.

- Task 1.1 (Minor, quality): `scripts/audit_skill_prompts.py:90` — the two indented `hint:` lines of the over-ceiling message carry no `prompt-audit:` prefix; only the first line does. No line-oriented consumer of that prefix found in `tests/**`, `scripts/*.sh`, `hooks/**`, `.github/**`. Cosmetic; forwarded to final review.
- Task 1.2 (Minor, quality): `specs/gh-308-deletion-test-ceiling/check_gh308.py:58-60,170-174` — a failing helper process (`ste-lint.py` with no JSON, a failed `git show`) ends in a traceback instead of a one-line failure. The exit stays non-zero, so there is no false pass. Forwarded to final review.
- Task 1.2 (Minor, spec): `budget`, `backlog` and the working-tree side of `ratchet` read files on disk, not HEAD. Their results stand as SC-4/SC-6/SC-7 evidence only on a clean tree; each Verify row below for them is run with only this SUMMARY untracked.
- Task 2.1 (Minor, quality): `skills/finishing-a-development-branch/references/run-state-handoff.md:13,15` — "this hop" lost its antecedent when the sentence moved (it meant the `ready_to_merge` transition), and "The open PR gets the new commit." now precedes the sentence that names the commit. Meaning unchanged; readability only.
- Task 2.1 (Minor, quality): `skills/finishing-a-development-branch/SKILL.md:48-49` — a line now ends mid-sentence ("…is" / "authoritative."); re-wrap.
- Task 2.3 (Minor, spec): `skills/session-retro/SKILL.md` — the deleted opening "`compound` records what a session learned." was the earliest text separating this skill from `compound`; the routing line at SKILL.md:52-53 now carries it alone. The skill is `disable-model-invocation: true`, so a wrong auto-trigger cannot happen. Watch the eval corpus near-miss prompt (`scripts/generate_skill_eval_corpus.py:67`).
- Task 2.3 and Task 2.2 (resolved): both reviewers could not run the SC commands; the controller re-ran SC-4, SC-5, SC-8 to SC-13 on a clean tree, all exit 0. Task 2.2's `cannot_verify` was resolved to `pass` on that evidence after one focused retry.
- Task 2.2 (Minor, quality): `tests/scripts/context-propagation-regression.test.sh:237` — the comment still says feature-intake points to `rules/research-depth.md`; this task deleted that pointer. The test checks only the rule file and passes. The file is outside every task's Files list.
- Task 2.2 (open question, no finding): the deleted sentence "`$ARGUMENTS` is the requested change." has no consumer in `scripts/`; how the Codex adapter substitutes arguments was not checked.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| audit tests incl. the new pointer assertion | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_audit_skill_prompts.py` | 0 | 11 passed; the new assertion failed before the audit edit (Task 1.1 report) | SC-1 |
| reference listed in the index | `grep -q deletion-test-for-word-ceiling docs/solutions/INDEX.md` | 0 | | SC-2 |
| index matches a fresh rebuild | `python3 scripts/rebuild_solution_index.py --check` | 0 | INDEX.md is current | SC-3 |
| three skills within budget | `python3 specs/gh-308-deletion-test-ceiling/check_gh308.py budget` | 0 | session-retro 525, feature-intake 539, finishing-a-development-branch 524 words; exited 1 on the wave-1 tree (600, 598, 589 in the same order) | SC-4 |
| every listed condition word resolved | `python3 specs/gh-308-deletion-test-ceiling/check_gh308.py qualifiers` | 0 | 4 words for finishing, each cited at HEAD in run-state-handoff.md; none for the other two | SC-5 |
| backlog rows done | `python3 specs/gh-308-deletion-test-ceiling/check_gh308.py backlog` | 0 | | SC-6 |
| STE ratchet per skill and scoped baseline diff | `python3 specs/gh-308-deletion-test-ceiling/check_gh308.py ratchet` | 0 | hard counts 0 / 2 / 2 unchanged; one baseline key added | SC-7 |
| qualifier canaries and review package | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_check_scope_qualifiers.py skills/subagent-driven-development/scripts/test_review_package.py` | 0 | 36 passed | SC-8 |
| finishing contract pins | `bash tests/scripts/finishing-branch-contract.test.sh` | 0 | | SC-9 |
| intake tiny-route propagation | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | | SC-10 |
| consumer render_plan rewrite | `bash tests/scripts/consumer-subset.test.sh` | 0 | | SC-11 |
| consumer verify_summary rewrite | `bash tests/scripts/deploy-worktree-isolation.test.sh` | 0 | | SC-12 |
| prompt audit | `python3 scripts/audit_skill_prompts.py` | 0 | `problems: []` | SC-13 |
| manifest consistency after the registry fix | `python3 scripts/check_manifest.py` | 0 | | |
| follow-up: finishing budget after the conditional commit | `python3 specs/gh-308-deletion-test-ceiling/check_gh308.py budget finishing-a-development-branch` | 0 | 536 words at `b08da10` | SC-4 |
| follow-up: doc-truth lint (new `hooks/commit-gate.sh` reference) | `bash scripts/lint-doc-truth.sh` | 0 | at `b08da10` | |

All rows were first run at `8d7ca01` with only this SUMMARY untracked, then re-run at `4a3b4a1` (after the intent-alignment fix) with only `RUN.json` and `events.jsonl` modified (`git status --short`); every row exited 0 both times. The full suite (`bash scripts/run-tests.sh`) runs at finish.

### Not auto-verified

- A trimmed skill makes its executing agent behave the same as before — reached provenance (qualifier list, per-file reviewer meaning verdicts, correctness review); not re-run because no behavioral eval of the three skills was run (design D2).
- A scope split that keeps a condition word but narrows its reach is absent — reached provenance (reviewer meaning check only); `check_scope_qualifiers.py` cannot list it (documented known limit).
- Codex sessions receive `feature-intake` arguments after the `$ARGUMENTS` sentence was deleted — unknown; not checked (Context-Propagation Audit row).
- Each per-file task-review `meaning: pass` in `### Task review meaning verdicts` — reached traceability; the controller transcribed the verdicts from the reviewers' returned results, which are not stored in the repository. The final intent review confirmed the file and range coverage and the condition-word citations, not the verdict values.
- The KB entry's procedure is followed by future trims — traceability only; the audit message points to it but nothing checks that it was followed.

### Rollback

- Revert the branch's code and prose commits, newest first: `git revert --no-edit 8d7ca01 2b267f5 63f1ef1 c043969 44d7061 cf36783 970a276 aad04a6 0cb0a06 77a27ef`.
- Or, before merge, close the PR and delete `feat/gh-308-deletion-test-ceiling`; `sdlc` is untouched.
- Nothing outside git changes: no hook, setting or deployed consumer file is modified by this branch.

### Harness-Delta

- none
