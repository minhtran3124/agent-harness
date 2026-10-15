# ste100-prose-rollout — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate (rewrites rules/, skills/, agents/ and the task-reviewer prompt; changes review_package.py)
Flags: existing behavior, weak proof, multi-domain
Affects: skills/subagent-driven-development (task reviewer, review package), rules/, skills/*/SKILL.md, agents/
Input-type: spec slice
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/ste100-prose-rollout/intent.md @ 48e7e05

let start for phase 3 now

### Intake notes

- Phase 3 of `specs/ste100-harness-prose/design.md`, allowed by `specs/ste100-harness-prose/DECISION.md` (pilot PASS).
- User decisions 2026-10-15: stack on PR #293 (branch `docs/ste100-prose-rollout` from `docs/ste100-harness-prose`, retarget to `sdlc` after #293 merges); scope "All agent prose, no fixtures"; extras: reviewer meaning check, tiny-lane STE line, qualifier-drop script.
- Confidence high: the user picked each scope option explicitly. The template and zero-count exclusions are marked `(assumed)` in intent.md, which the user approved.

## What changed

Phase 3 of the ASD-STE100 adoption. First, four guardrails:

- `check_ste_baseline.py --against <ref>`, with `--strict` now failing on a skipped run;
- the advisory `check_scope_qualifiers.py` and its `## Scope qualifiers` review-package section;
- a meaning-equivalence instruction and a `meaning:` result key in the task-reviewer prompt;
- a tiny-lane STE line in `feature-intake`. Room for it came from replacing the duplicate research-depth section with a pointer.

Then 9 sequential waves rewrote 43 agent-prose files in `rules/`, `agents/` and `skills/`. Their hard STE findings fell from 267 to 7, and the 7 left are mostly frontmatter that must not change. Each file has a task-review meaning verdict of `pass`. The xia2 structural suite was re-run (Run 5, 30/30 stable).

### Rationale

The pilot (PR #293) showed that the method keeps comprehension. It also showed that a rewrite can drop scope silently. So the guardrails landed first, and every rewrite wave went through a per-file meaning review. The waves were sequential, to avoid the shared-git-index hazard and to keep each review small. No paid pilot was run (design D6); the per-file meaning verdict is the gate.

### Alternatives considered

- Parallel implementers within a wave. Rejected because of the shared git index hazard (design D5).
- The tiny-lane line in `rules/auto-correct-scope.md`. Rejected because that file is path-scoped and a tiny-lane agent may not load it (design D4).
- `scripts/check_scope_qualifiers.py` beside `review_package.py` so it deploys to consumers. The user chose to keep it harness-only.
- A new paid comprehension pilot. Rejected by the user (design D6).

### Deviations

- Plan gap (2026-10-15, found in Task 1.3): Global Constraints forbade editing fenced code, but the dispatch prompts in `*-prompt.md` keep their prompt prose inside a fence. Clarified in PLAN.md Global Constraints: the fenced dispatch block is prose (Strict mode), with commands, paths, placeholders and YAML keys kept unchanged. Phase 1 (Task 1.4 of `ste100-harness-prose`) and Task 1.3 already edited fenced prompt text this way.
- Plan gap (Task 2.5): `skills/xia2/README.md` ("When you change `SKILL.md`") says a change to HARD-GATE wording, `## Decide depth`, or `references/depth-classifier.md` **must** re-run the structural suite in `skills/xia2/tests/structural/depth-modes-test-cases.md`. The B5 rewrite changed all three. A fresh agent ran Run 5. That file was added to Task 2.5's Files. Intent excluded eval fixtures from the *rewrite*; this is a validation record, not a rewrite.
- Task 1.5: `check_rollout.py --task-scope` also ignores `.harness-state/` (gitignored runtime state, `.gitignore:30`), beyond the brief's `specs/ste100-prose-rollout/` exclusion.

### Context-Propagation Audit

Range `48e7e05..44ee25d`. Independent audit agent, 2026-10-15. **PASS**, with no failed rows.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| task-reviewer meaning instruction + `meaning:` key | task-reviewer child | reviewer | pasted prompt (SDD `SKILL.md` dispatch) | `context-propagation-regression.test.sh` anchors and 2 mutations; `render_skill_prompt.py --check-all` |
| `review_package.py` `## Scope qualifiers` | task-reviewer child | reviewer | file at `REVIEW_PACKAGE_PATH` | `test_review_package.py` (order, unavailable, no-prose); `task-reviewer-readonly.test.sh` |
| `check_scope_qualifiers.py` (harness-only) | consumer review package | consumer | not deployed by design; degrades to `unavailable` | `parents[3]` path math vs `CONSUMER_SCRIPTS`; absent-module test |
| `meaning:` key | SDD controller | main | indirect: a `fail` requires an Important finding, so `spec_verdict: fail` | `sdd-task-review-routing.test.sh` |
| feature-intake tiny-lane line | tiny-lane agent | main | skill load | regression test (tiny..normal range) with a mutation |
| `rules/research-depth.md` mapping (replaces the feature-intake section) | xia2, intake | main | always-on rule + explicit Read in xia2 `## Decide depth` | `rule-loading-tiers`, 4 anchors with 4 mutations, `research-depth-drift` |
| `check_ste_baseline.py --against` / strict skip | SC-6, plan Done rows; `run-tests.sh:84` (default mode) | harness | direct call | `test_check_ste_baseline.py`; CI default unchanged |
| 43 STE rewrites | every consumer | all | unchanged | 466 path/backtick tokens from removed lines are all present at HEAD; no Read lost; no frontmatter lines in the diff |
| deployed `.claude/` copies | this checkout | runtime | stale until `bash scripts/deploy-harness.sh` | activation step; `consumer-subset.test.sh` 19 passed |

Advisory:
- No component reads `meaning:` on its own; blocking runs through the Important finding.
- The tiny-lane line names the `skills/asd-ste100/SKILL.md` source path. This matches the existing convention in `implementer-prompt.md` and `compound`.

### Correctness review

Range `48e7e05..44ee25d`, plus the uncommitted `specs/ste100-prose-rollout/check_rollout.py`. There were six FIND angles: enclosing-function (4), removed-behavior (1), call-site-impact (2), stack-defects (6), guard-completeness (3) and prior-art (0). After dedupe by location, 8 independent scorers ran. The threshold is 75, so **no finding is blocking**. Advisory findings (score < 75):

| Score | Location | Finding |
| --- | --- | --- |
| 50 | `scripts/check_ste_baseline.py:88-96` | Regression: `read_baseline_text` catches `OSError` only, so a non-UTF-8 baseline (or `--against` blob) raises an uncaught `UnicodeDecodeError`. The default run then exits 1 with a traceback, where BASE skipped. Reproduced. The trigger is rare, because the tool writes the file itself. Fix: catch `ValueError` in both branches. |
| 50 | `scripts/check_scope_qualifiers.py:64` | `git diff` runs without `--no-color` / `--no-ext-diff`. Under `color.ui=always` or an external diff driver the parser matches nothing and prints a false `- none`. |
| 50 | `scripts/check_scope_qualifiers.py:41-46` | The path comes only from `+++ b/`. `diff.noprefix=true` labels hunks `None`, the path is not reset at `diff --git`, and a filename with a space keeps a trailing TAB. |
| 50 | `scripts/check_scope_qualifiers.py:60-61` (same filter as `review_package.py:36-37` `prose_paths`, which predates this PR) | The default `core.quotePath` quotes non-ASCII names, so the file is silently skipped. No such path exists in the tree. Fix: `--name-only -z`. |
| 50 | `scripts/check_scope_qualifiers.py:86-87` | The final `print` is outside the `try`. A stdout encoding override that differs from the locale gives exit 1 with `UnicodeEncodeError`. Reproduced with `PYTHONIOENCODING=ascii`. |
| 50 | `scripts/check_ste_baseline.py:92` | `--against ""` reads the staged index copy (`git show :path`), so `--strict` can pass against an editable baseline. Every in-repo use pins `48e7e05`. |
| 50 | `specs/ste100-prose-rollout/check_rollout.py:57` | `unfenced()` matches 3-character fences only, so a 4-backtick fence with an inner 3-backtick line closes early. No such fence exists in SUMMARY.md or PLAN.md. |
| 0 | `scripts/check_ste_baseline.py:125-126` | This line is unchanged by the PR, so it is advisory to a human. Under `--strict --against <ref>`, a prose file deleted or renamed since the ref gives a WARN that `--update` cannot clear. Workaround: re-pin the ref. |

Non-runtime note: `docs/solutions/harness/ste100-adoption-decisions.md:104` still says `--strict` exits 0 on a skip. It is updated in the compound step.

### Intent Findings

Range `48e7e05..44ee25d`. The intent reviewer was blind to PLAN.md. It found no behavioral gap: every intent clause is delivered.

| # | Class | Finding | Route |
| --- | --- | --- | --- |
| 1 | gap (record only) | SUMMARY had no row for the plain `check_ste_baseline.py --strict` and no evidence for `run-tests.sh`. The reviewer re-ran both at HEAD, and both pass. | Fixed: Verify row added, and the run-tests evidence is stated in prose under `### Verify`. |
| 2 | drift, equivalent | Waves B1 and B5 have 3 files, not 4–6. B1 holds the three largest rules (57 findings); B5 holds the three xia2 files. | Advisory. Design D5 (3–6, budget) records the reason. |
| 3 | drift | `task-reviewer-prompt.md` step 3 required "kept" to cite the same qualifier word. A condition kept in other words could then force a blocking finding from the advisory section, against "It never fails a build or a review by itself." | Fixed in `5f408ff`: "kept" cites the HEAD line that keeps the condition, in the same or in other words. |
| 4 | excess | `check_ste_baseline.py --strict` now exits 1 on a skip, and `--against` with `--update` exits 2. `--against` is what proves the per-file criterion; the strict-skip change was not asked for. | Report-only. Recorded in design D7. |
| 5 | excess | `specs/ste100-prose-rollout/check_rollout.py`: spec-local verification tooling with no public surface. | Report-only. |
| 6 | excess | Eval fixture `skills/xia2/tests/structural/depth-modes-test-cases.md` got Run 5 (lint 8→35). This was required by the xia2 README re-run rule. | Report-only. Recorded under `### Deviations`. |
| 7 | drift, equivalent | Pilot file `feature-intake/SKILL.md` lost its "Research-depth handoff" section to make room. The content lives in the always-on `rules/research-depth.md` (anchored by tests). "Never re-scores risk" maps to "Intake owns risk classification", which no test anchors. | Advisory. Design D4, approved by the user. |

Note: the intent's Problem text says "290 … across 46 files". That figure came from an intake count that left out the `skills/*/templates/` folder but still counted the three other template files the intent names (`agents/PROJECT.template.md`, the brainstorming design template, the xia2 research-brief template; 23 findings). The in-scope set after every exclusion the intent lists is 43 files with 267 findings (measured 2026-10-15 at `48e7e05`; intent re-review finding R1).

### Meaning verdicts

| File | Task | Verdict | Note |
| --- | --- | --- | --- |
| `rules/plan-format.md` | 2.1 | pass | 21→0 |
| `rules/auto-correct-scope.md` | 2.1 | pass | 20→0 |
| `rules/terminology.md` | 2.1 | pass | 16→0; fix round 1 kept `p = 0.087` on the comparison |
| `rules/behavior.md` | 2.2 | pass | 9→0 |
| `rules/research-depth.md` | 2.2 | pass | 10→0 |
| `rules/review-policy.md` | 2.2 | pass | 5→0 |
| `rules/wave-parallelism.md` | 2.2 | pass | 8→0 |
| `rules/architecture.md` | 2.2 | pass | 1→0 |
| `agents/PROJECT.md` | 2.3 | pass | 12→0 |
| `agents/README.md` | 2.3 | pass | 6→0 |
| `agents/coding.md` | 2.3 | pass | 2→0 |
| `agents/reviewer.md` | 2.3 | pass | 2→0 |
| `agents/task-reviewer.md` | 2.3 | pass | 2→1; the 1 left is a frontmatter semicolon, which must not change |
| `agents/test-runner.md` | 2.3 | pass | 2→0 |
| `skills/brainstorming/SKILL.md` | 2.4 | pass | 8→1; the 1 left is in the frontmatter description |
| `skills/writing-plans/SKILL.md` | 2.4 | pass | 6→0 |
| `skills/writing-plans/references/review-loop.md` | 2.4 | pass | 1→0 |
| `skills/feature-intake/references/draft-intent.md` | 2.4 | pass | 14→0; reviewer traced every conditional branch |
| `skills/feature-intake/references/re-pin.md` | 2.4 | pass | 3→0 |
| `skills/xia2/SKILL.md` | 2.5 | pass | 8→1 (the 1 left is in the frontmatter); structural suite Run 5: 30/30 stable |
| `skills/xia2/README.md` | 2.5 | pass | 12→0 |
| `skills/xia2/references/depth-classifier.md` | 2.5 | pass | 4→0 |
| `skills/correctness-review/SKILL.md` | 2.6 | pass | 5→1; the 1 left is in the frontmatter |
| `skills/correctness-review/correctness-reviewer-prompt.md` | 2.6 | pass | 2→0 |
| `skills/correctness-review/correctness-scorer-prompt.md` | 2.6 | pass | 6→0; about 25 fenced prose lines rewritten; the 50-point cap keeps its scope |
| `skills/intent-review/SKILL.md` | 2.6 | pass | 10→0 |
| `skills/intent-review/intent-reviewer-prompt.md` | 2.6 | pass | 6→0; about 30 fenced prose lines rewritten; the semicolons left are in frozen placeholders and YAML |
| `skills/context-propagation-audit/SKILL.md` | 2.6 | pass | 4→1; the 1 left is in the frontmatter |
| `skills/subagent-driven-development/implementer-prompt.md` | 2.7 | pass | 1→0; about 30 fenced prose lines rewritten; "While you work" (21 words) kept as it was at BASE |
| `skills/subagent-driven-development/task-reviewer-prompt.md` | 2.7 | pass | 1→0; about 15 fenced lines; the Task 1.3 meaning sentence kept long, because a split separates its scope from its action |
| `skills/subagent-driven-development/references/resume.md` | 2.7 | pass | 4→0 |
| `skills/subagent-driven-development/references/review-chain.md` | 2.7 | pass | 2→0 |
| `skills/compound/SKILL.md` | 2.9 | pass | 4→0 |
| `skills/compound/README.md` | 2.9 | pass | 2→0 |
| `skills/compound/subagents/context-analyzer-prompt.md` | 2.9 | pass | 3→0 |
| `skills/compound/subagents/decision-extractor-prompt.md` | 2.9 | pass | 5→0; fix round 1 restored one line in the fenced output template |
| `skills/compound/subagents/related-docs-finder-prompt.md` | 2.9 | pass | 1→0 |
| `skills/finishing-a-development-branch/SKILL.md` | 2.8 | pass | 10→0; 584→589 words |
| `skills/finishing-a-development-branch/references/pr-body.md` | 2.8 | pass | 1→0 |
| `skills/session-retro/SKILL.md` | 2.8 | pass | 8→2; 599→600 words (at the ceiling); the per-candidate sentence (30 words) is kept long because a split would pass 600 |
| `skills/visual-planner/SKILL.md` | 2.8 | pass | 8→0 |
| `skills/visual-planner/references/review-sidecar.md` | 2.8 | pass | 2→0 |
| `skills/using-git-worktrees/SKILL.md` | 2.7 | pass | 10→0; the base-compare step now sits explicitly under "Otherwise" (the reviewer judged this equivalent to BASE); the nested-worktree sentence is kept long because "silently" covers both verbs |

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Baseline checker `--against` and strict skip | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_check_ste_baseline.py -q` | 0 | 18 passed | SC-1 |
| Scope-qualifier module | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_check_scope_qualifiers.py -q` | 0 | 10 passed, including the Step 6 (listed) and Step 1 (pinned limit) replays | SC-2 |
| Review package section | `/tmp/harness-tests-venv/bin/python -m pytest skills/subagent-driven-development/scripts/test_review_package.py -q` | 0 | 12 passed | SC-3 |
| Instruction delivery and mutations | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 29 passed | SC-4 |
| Skill word ceiling | `python3 scripts/audit_skill_prompts.py` | 0 | `problems: []`; session-retro 600, finishing 589, feature-intake 584 | SC-5 |
| Per-file ratchet vs start | `python3 scripts/check_ste_baseline.py --strict --against 48e7e05` | 0 | 72 files checked, 0 above baseline or gone | SC-6 |
| In-scope sum below start | `python3 specs/ste100-prose-rollout/check_rollout.py --sum-below 267` | 0 | sum of 43 entries = 7 | SC-7 |
| Frontmatter unchanged | `python3 specs/ste100-prose-rollout/check_rollout.py --frontmatter 48e7e05` | 0 | OK | SC-8 |
| Meaning verdict per file | `python3 specs/ste100-prose-rollout/check_rollout.py --verdicts` | 0 | 43 of 43, all `pass` | SC-9 |
| Prose contract and drift tests | `bash -c 'for t in inline-policy-drift writing-plans-contract research-depth-drift brainstorming-contract correctness-prompt-composition final-review-package-contract intent-prompt-contract scorer-threshold-contract finishing-branch-contract compound-contract task-reviewer-readonly runtime-entry-bindings; do bash tests/scripts/$t.test.sh >/dev/null 2>&1 && continue; echo FAIL $t; exit 1; done'` | 0 | The worktree sandbox refuses this `bash -c` text as a direct call, so the identical loop text ran from a script file. `ci-strict-gate.sh` re-runs the literal row. | SC-10 |
| Agent and frontmatter contracts | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_check_frontmatter_contract.py scripts/test_render_agent_definitions.py scripts/test_check_task_review_contract.py scripts/test_check_runtime_neutral_sources.py -q` | 0 | 50 passed | SC-11 |
| Rollout checker self-test | `python3 specs/ste100-prose-rollout/check_rollout.py --selftest` | 0 | OK | SC-12 |
| Ratchet vs current baseline (intent "What success looks like") | `python3 scripts/check_ste_baseline.py --strict` | 0 | 72 files checked, 0 above baseline or gone | |

The full suite (`bash scripts/run-tests.sh`) is not a Verify row: `rules/plan-format.md` keeps it out of rows and runs it at `finishing-a-development-branch`. Each rewrite wave ran it as its Action. Results are in the per-task reports, and the controller re-ran it before the push.

### Not auto-verified

- Strict-mode quality of fenced dispatch-prompt text (implementer, task-reviewer, intent-reviewer, scorer prompts: 61–100 non-blank fenced lines each, measured 2026-10-15 at HEAD) — reached traceability only; `ste-lint.py` skips fenced blocks, so SC-6/SC-7 do not count it. The task reviewer's judgement and meaning check are the only review.
- The rewritten review prompts (correctness scorer and finder, intent reviewer, task reviewer) keep reviewer behavior — reached traceability (meaning review + contract tests) only. The paid review-chain A/B eval (`evals/skills/review-chain`, `scripts/run_review_prompt_eval.py`, about $11 per run) is the regression baseline for edits to `/correctness-review` and `/intent-review`. It was not run, because the user chose no new paid pilot (design D6).

### Rollback

- One rewrite wave: `git revert <sha>` for that wave's commits (2.1: `933c2d1 01f4f72 d78fc3e`; 2.2: `9e1e66e`; 2.3: `fac8408`; 2.4: `7d52a7b`; 2.5: `4be88e9 38fbd98`; 2.6: `68b4b08`; 2.7: `7b4ae99`; 2.8: `635948c`; 2.9: `315f9f2 44ee25d`). Then run `python3 scripts/check_ste_baseline.py --update` and revert entries outside that wave.
- Guardrails: `git revert 5f408ff 2370e6b ad43f73 cbea6a2 01debfb bb0448f` (newest first).
- Whole PR: `git revert --no-commit 48e7e05..HEAD`, then commit. After any revert, run `bash scripts/deploy-harness.sh` so the deployed `.claude/` copies match.

### Harness-Delta

- backlog (Task 1.3): `ste-lint.py` skips fenced blocks, so the STE baseline ratchet cannot see dispatch-prompt prose, which lives inside a fence. Candidate: a `--include-fences` mode, or lint the `prompt: |` body of `*-prompt.md` files as prose.
- backlog (Task 2.5): the review package's `## STE lint` covers every `.md` under `skills/`, including eval fixtures (`skills/*/tests/**`), but `check_ste_baseline.py` globs stop at `skills/*/*/*.md` and intent excludes fixtures. A fixture edit then shows a lint rise that the reviewer rule calls Important. Align the two scopes.
- backlog (Task 2.5, xia2 Run 5): these ambiguities in the depth classifier predate this PR, and Run 5 recorded them as A1–A5 in `skills/xia2/tests/structural/depth-modes-test-cases.md`. "high-blast file" is undefined, so the TC-19/TC-21 canaries depend on a step-5 blast-radius check. "Shared" is undefined in the Quick condition. "Shared runtime configuration" (classifier) and "…contract" (rule) differ. The SKILL.md tiny→Quick line lacks the rule's "otherwise Standard".
- backlog (all tasks): plan Verify rows written as `bash -c '…'` are refused by the worktree sandbox, so implementers split them by hand. The case-sensitive `grep -qF` anchors also mean an anchored phrase cannot start a capitalised list item. Rewrite briefs should say so.
