# ste100-harness-prose — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate — the work rewrites and extends skills/*/SKILL.md, rules/*.md, agents/*.md, and dispatch prompts; a bulk prose rewrite also risks silent behavior change (weak proof).
Flags: workflow-engine, existing behavior, weak proof, multi-domain
Affects: skills/, rules/, agents/ (agent-loaded prose); scripts/run-tests.sh (advisory lint)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development; compound for durable decisions
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/ste100-harness-prose/intent.md @ a5d4292cc6eb108d2b2770584ddb18a7a7794a80

check the skill asd-ste100 in @.agents/skills/asd-ste100/
/feature-intake thinking about apply it for our current harness workflow to help simplify text and help agent can read it with comfortable way.

Scope answer (2026-10-14): A + B + C

### Intake notes

- 2026-10-14: the first draft was low confidence (three materially different readings: A rewrite existing prose, B adopt the skill in authoring steps, C add a warn-only linter). The user approved the draft, then chose A + B + C. intent.md was narrowed and re-committed (08e920c → a5d4292). Confidence is now high.
- The two remaining intent.md open questions (measure before adoption, where to vendor the skill) are design forks for brainstorming, not intent ambiguity.
- Prior evidence that brainstorming must read: `specs/ste-terminology-evidence/DECISION.md` (§1 one-word-one-meaning had no measured effect; a blocking STE lint hook was rejected).
- `skills-lock.json` may trip the `external-provider` detectable gate as a dependency manifest. The lane is already high-risk, so this changes nothing at intake.

## What changed

This PR ships Phases 1–2 of the design. Phase 3 is a follow-up plan revision, by user decision on 2026-10-14.

- **Phase 1, adopt the skill and the linter (B + C).**
  - The `asd-ste100` skill is vendored into `skills/asd-ste100/` from upstream `3944283c18`, with three recorded deltas. `.agents/` and `skills-lock.json` are gone.
  - The SDD implementer, the task reviewer, the SDD controller and `compound` now apply it to new prose.
  - `review_package.py` adds per-file STE hard counts (`## STE lint`).
  - `scripts/check_ste_baseline.py` adds a warn-only per-file ratchet in `run-tests.sh`.
  - The deploy rewrites the linter path for consumers.
  - The skill audit exempts vendored skills from the 600-word ceiling.
- **Phase 2, pilot (A).**
  - Three high-traffic files were rewritten in STE-flavored mode: `rules/orchestration.md`, `skills/feature-intake/SKILL.md`, `skills/subagent-driven-development/SKILL.md`. Their hard counts went from 37/21/15 to 3/2/2.
  - An 80-trial paid pilot (comprehension probes plus real `feature-intake` classification) found no measured accuracy loss for any file. All three PASS. The total spend was $2.91 against a $25 cap. See `DECISION.md`.

### Rationale

`specs/ste-terminology-evidence/DECISION.md` showed that STE wording rules are worth adopting only where measurement supports them. So the bulk rewrite (A) is gated on a measured pilot, and the linter (C) stays warn-only.

The pilot's main lesson is about review, not the score. The meaning-equivalence task review caught two real meaning losses in the rewrite that no test caught:
- a sentence split dropped an "if intent.md is present" scope
- a word-ceiling cut dropped "for a new SUMMARY"

Both were fixed before the pilot ran. Phase 3 therefore needs the same per-file meaning review.

### Alternatives considered

- Bulk rewrite with no trial. Rejected by the user in favour of pilot-then-gate.
- Keeping the `npx skills` install. Rejected because it does not deploy to consumers and it collides with the Codex adapter's `.agents/` output.
- Splitting the vendored skill to fit the 600-word ceiling. Rejected by the user in favour of a vendored-skill exemption, which keeps re-vendoring trivial.
- A blocking STE gate. Rejected because the prior decision record forbids mechanising unmeasured rules.

### Deviations

- Rule 1 (`28dbfd4`): `scripts/test_audit_skill_prompts.py` expected 13 skills. The repo has 14 since `a4d596f`. The audit's own exit 1 had hidden the failure.
- User-approved (Rule 4 stop, Task 1.5): `scripts/deploy-harness.sh` gained one anchored rewrite for `skills/asd-ste100/scripts/ste-lint.py`. The file was added to Task 1.5's Files.
- User-approved (word ceiling): Task 1.6 was added to the plan. It holds the vendored exemption plus Minor wave-2 review fixes.
- Plan change: Task 1.6 step 4 wording. The SDD bullet reads "If changed-prose `## STE lint` counts are missing or unavailable…". Recorded in PLAN.md.
- Plan change: Task 2.3 reverts every Task 2.2 commit on a fail. Task 2.2 ended with three commits (`f49a9d1`, `dc867ed`, `87d204c`).
- Context-propagation repair (`f7e5dfe`): "apply" became "Read and apply" for `skills/asd-ste100/SKILL.md` in the implementer prompt and in `compound`.
- Intent-review fix (`a7081fb`), by user decision on 2026-10-15: `synonym-rotation` is excluded from the review-package count and from the baseline, because it is the measured-null §1 rule. The SDD `SKILL.md` "in a sentence" and "confirms" wording is restored. A focused correctness re-review of `f7e5dfe..a7081fb` found 0 bugs.
- Spec-folder files were committed at the end, not per task. The commit gate checks SC coverage on any commit that touches `specs/<slug>/` (see Harness-Delta).

### Verify

The full suite (`bash scripts/run-tests.sh`) was run by the correctness-review call-site angle on `f7e5dfe`. It was ALL GREEN, with pytest 938 passed. It is cited here in prose because it exceeds the 60s cap for a Verify row.

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| skill in inventory | `python3 scripts/check_manifest.py` | 0 | inventory ↔ disk ↔ settings agree | SC-1 |
| allowed-tools present | `bash scripts/check-allowed-tools.sh` | 0 | all 14 skills declare allowed-tools | SC-1 |
| runtime-neutral scan | `python3 scripts/check_runtime_neutral_sources.py` | 0 | inventory passed | SC-2 |
| doc-truth + derived paths | `bash scripts/lint-doc-truth.sh` | 0 | source + derived paths exist | SC-2 |
| npx install gone | `test ! -e .agents` | 0 | | SC-3 |
| lock file gone | `test ! -e skills-lock.json` | 0 | | SC-3 |
| linter selftest | `python3 skills/asd-ste100/scripts/ste-lint.py --selftest` | 0 | selftest OK | SC-4 |
| baseline checker tests | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_check_ste_baseline.py -q` | 0 | 12 passed | SC-5 |
| no file above baseline | `python3 scripts/check_ste_baseline.py --strict` | 0 | 72 files, 0 above baseline or gone | SC-6 |
| review package STE section | `/tmp/harness-tests-venv/bin/python -m pytest skills/subagent-driven-development/scripts/test_review_package.py -q` | 0 | 9 passed (incl. synonym-rotation excluded) | SC-7 |
| four wiring instructions + mutations | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 19 passed, incl. 4 asd-ste100 assertions and 4 mutations | SC-8 |
| consumer deploy | `bash tests/scripts/consumer-subset.test.sh` | 0 | 19 passed, incl. ship + deployed-path + idempotency | SC-9 |
| pilot scorer selftest | `python3 specs/ste100-harness-prose/experiment/pilot.py --selftest` | 0 | 126/126 passed | SC-10 |
| pilot metrics re-derive | `python3 specs/ste100-harness-prose/experiment/pilot.py --score-only --output specs/ste100-harness-prose/experiment/runs/pilot-1` | 0 | trials=80, three PASS lines | SC-11 |
| SDD handoffs | `bash tests/scripts/sdd-artifact-handoffs.test.sh` | 0 | passed | SC-12 |
| SDD review routing | `bash tests/scripts/sdd-task-review-routing.test.sh` | 0 | passed | SC-12 |
| run-state chain | `bash tests/scripts/run-state-chain-validation.test.sh` | 0 | 14 passed | SC-12 |
| runtime entry bindings | `bash tests/scripts/runtime-entry-bindings.test.sh` | 0 | 7 passed | SC-12 |
| OQ-1 closed | `env REQUIRE_QUESTIONS_CLOSED=1 python3 .claude/scripts/check_open_questions.py --slug ste100-harness-prose` | 0 | blocking mode | SC-13 |
| DECISION matches scorer | `python3 specs/ste100-harness-prose/experiment/pilot.py --check-decision specs/ste100-harness-prose/DECISION.md --output specs/ste100-harness-prose/experiment/runs/pilot-1` | 0 | check-decision OK | SC-14 |
| smoke outputs parse | `python3 specs/ste100-harness-prose/experiment/pilot.py --check-parse --output specs/ste100-harness-prose/experiment/runs/smoke` | 0 | check-parse OK | SC-15 |
| skill audit with exemption | `python3 scripts/audit_skill_prompts.py` | 0 | asd-ste100 vendored, exempt | SC-16 |
| intent pin unchanged | `git diff --exit-code a5d4292 -- specs/ste100-harness-prose/intent.md` | 0 | no diff | |

### Not auto-verified

- Agents follow the wired asd-ste100 instructions. Reached traceability only: the propagation tests prove the instructions exist, not that agents apply them.
- The three pilot rewrites preserve meaning. Reached truth on 24 probes and 8 intake fixtures (80 paid trials, one model, n=10 per arm). Line-by-line equivalence was judged by an independent reviewer, not by a machine.
- STE improves agent accuracy. Not claimed. The pilot shows only no measured loss, at a ceiling.
- The vendored copy matches upstream except for the recorded deltas. Reached provenance: the controller diffed it against upstream `3944283c18` on 2026-10-14. Nothing re-checks it later.

### Rollback

- Whole branch: close the PR, or after merge run `git revert -m 1 <merge sha>`.
- Pilot rewrites only, newest first: `git revert --no-edit 87d204c`, then `dc867ed`, then `f49a9d1`.
- Vendored skill only: `git revert --no-edit a4d596f`, together with the wiring commits `2aeef17`, `f7e5dfe` and `a7081fb`, because the wiring names the skill.

### Harness-Delta

- backlog: the commit gate's SC-coverage check runs on any commit that touches `specs/<slug>/`, and it reads an unstaged SUMMARY from disk. So a reviewed plan cannot be committed before implementation exists. All spec files stayed untracked until the end.
- backlog: the worktree sandbox refuses `bash -c '<chain>'` and `bash <script>; echo`. PLAN Verify rows written in that form cannot be re-run literally from an agent session.
- backlog: a SKILL.md at the 600-word ceiling leaves an STE rewrite no room for scope words. Both meaning losses in Task 2.2 came from sentence splits or ceiling cuts. → `compound`.
- backlog: `rewrite_derived_paths` uses one pattern per skill-local script path. A general `skills/<name>/scripts/` rewrite would close the class.
- backlog: SDD `SKILL.md` is at 600/600 words and `feature-intake` at 599/600, so the next addition to either needs cuts.
- backlog: a manual `ste-lint.py` run (as `skills/asd-ste100/SKILL.md` documents it) counts `synonym-rotation`, but the gates do not. Agents that self-check by hand see higher counts than the review package shows.
- open (Phase 3 plan): tiny-lane direct edits to agent prose get no asd-ste100 instruction (intent finding 4, deferred by the user).

### Intent Findings

Intent review was run blind to the plan, over `a5d4292..f7e5dfe`. It returned six findings. Every SC-1–16 has a passing Verify row.

| # | Class | Finding | Route and outcome |
| --- | --- | --- | --- |
| 1 | drift (behavior) | The task reviewer blocks on a hard-count rise that includes `synonym-rotation`, which `ste-terminology-evidence` measured as having no effect. The intent says "do not mechanise an unmeasured rule into a blocking gate". | Escalated. User decision (2026-10-15): exclude `synonym-rotation` from the review-package count and from the baseline. Fixed in the final-review fix commit. |
| 2 | drift (behavior) | The SDD `SKILL.md` lost "in a sentence", and "confirms" became "verifies". | Fixed in the final-review fix commit. Two other items are equivalent drift: the model-selection clause still stands in `task-reviewer-prompt.md:5-7`, and the `sys.path` text was explanation only. |
| 3 | gap (deferred) | Only the 3 pilot files are rewritten (A-partial). | Deferred by user decision ("Ship 1–2, Phase 3 next"). It stays an open obligation until the Phase 3 PR. |
| 4 | gap (unclear) | Tiny-lane direct edits to `skills/`, `rules/`, `agents/` get no asd-ste100 instruction. | Escalated. User decision (2026-10-15): defer to the Phase 3 plan. `feature-intake` is at 599/600 words. |
| 5 | excess | `compound` applies STE to `docs/solutions/` records. The intent assumed knowledge-base entries are out of target. | Report only. It was a deliberate design choice (design D4). |
| 6 | drift (same) and small excess | The skill is vendored at `skills/asd-ste100/`, not `.agents/`. There is a general `UPSTREAM.md` exemption, and a `--strict` flag. | Advisory. It resolves intent open question 2. |

### Correctness Review

Range `a5d4292..f7e5dfe`. Six FIND angles, eight deduplicated locations, one independent scorer each (threshold 75). **No finding at or above the threshold. No blocking finding.** The call-site-impact angle also ran `bash scripts/run-tests.sh`: ALL GREEN, pytest 938 passed.

Advisory (below threshold, recorded, not fixed):

| Score | Location | Finding |
| --- | --- | --- |
| 50 | `review_package.py:34` | `git diff --name-only` C-quotes non-ASCII paths, so such a prose file gets no `## STE lint` line and the task blocks. No such path exists in the tree today. Fix later: `-c core.quotePath=false -z`. |
| 50 | `review_package.py:34` | `--diff-filter=d` drops deleted prose files. A reviewer who counts a deletion as a "changed prose file" withholds approval. Fix later: emit `- path: deleted`, or exempt deletions in the reviewer prompt. |
| 50 | `review_package.py:40` | `--no-renames` reports a renamed file as `base: new`, so a hard-count rise in a rename is only a warning. Fix later: `-M --name-status` and lint the old path at BASE. |
| 50 | `review_package.py:13` | In a consumer, `PROSE_ROOTS` matches the consumer's own top-level `skills/`, `rules/`, `agents/` docs, not the harness prose under `.claude/`. Consumer gate scope is a Rule 4 decision. Recorded for the Phase 3 plan. |
| 50 | `check_ste_baseline.py:121` | `--strict` exits 0 on a skip, so SC-6 can pass after checking nothing. Plan-mandated (the brief required exit 0 on a crash). Fix later: a non-zero exit on skip under `--strict` only. |
| 50 | `audit_skill_prompts.py:84` | Any `UPSTREAM.md` marker exempts a skill from the word ceiling. It needs a deliberate, visible commit and prints a notice. Fix later: an explicit allowlist. |
| 50 | `subagent-driven-development/SKILL.md:68` | "tell the user in a sentence" lost its length bound (word-ceiling cut in `2aeef17`). "Keep detail in SUMMARY and the ledger" still applies. |
| 25 | `implementer-prompt.md:67`, `compound/SKILL.md:41` | `skills/asd-ste100/SKILL.md` is not rewritten for consumers. It follows the existing `.claude/`-relative Read convention, which `lint-doc-truth.sh` checks. |

### Context-Propagation Audit

**Verdict: PASS after one repair** (`f7e5dfe`). Diff audited: `a5d4292..f7e5dfe`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `implementer-prompt.md` `## Prose style` (apply asd-ste100 to changed prose, exclusions) | implementer subagent | fresh child | pasted (inside the fenced dispatch template) | `context-propagation-regression.test.sh` assertion + mutation; observed in the Task 1.6 and 2.2 dispatches |
| `skills/asd-ste100/SKILL.md` content (modes, rules) | implementer subagent; `compound` writer | fresh child; main | explicit Read by path, after repair | repaired in `f7e5dfe` from "apply" to "Read and apply"; the path resolves under `.claude/` in a consumer (lint-doc-truth derived check) |
| `task-reviewer-prompt.md` STE lint rule | task-reviewer subagent | fresh child | pasted (dispatch template) | propagation assertion + mutation; observed: the reviews of 1.4, 1.6 and 2.2 applied it to the package's `## STE lint` section |
| `## STE lint` counts | task-reviewer subagent | fresh child | file path (review package from `review_package.py`) | `test_review_package.py` (7 cases); observed on real ranges a7253ae..2aeef17 and 0cc7ab7..87d204c |
| SDD `SKILL.md` re-run-then-block rule | SDD controller | main | skill loaded on invoke | propagation assertion + mutation |
| `compound/SKILL.md` record rule | `compound` main writer (its subagents return text only and write no files) | main | skill loaded on invoke | propagation assertion + mutation; `compound-contract.test.sh` 4 passed |
| Rewritten `rules/orchestration.md` | every session | main | always-on rule (no `paths:`), unchanged mechanism | `rule-loading-tiers.test.sh` 3 passed |
| Rewritten `feature-intake` / SDD `SKILL.md` | main session | main | skill loaded on invoke, unchanged mechanism | `render_skill_prompt.py --check-all` all contracts present; pilot measured comprehension |
| `asd-ste100` skill registration | consumer repos | install | deploy sync of `skills/` + linter path rewrite | `consumer-subset.test.sh` 19 passed |

Failed row, repaired: the implementer prompt and `compound` said "apply `skills/asd-ste100/SKILL.md`" with no Read. A fresh child context has no other route to the file, so delivery was assumed. Both now say "Read and apply". The test patterns still match.
