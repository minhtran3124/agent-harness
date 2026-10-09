# gh-258-open-questions-register — Summary

Lane: high-risk
Confidence: medium
Reason: workflow-engine hard gate (new spec artifact consumed by skills/rules) plus a new gate in scripts/ (CI warn tier) and a new template under templates/ (CI block tier); multi-domain across artifact, skills and gate
Flags: workflow-engine, new gate, existing behavior, multi-domain
Affects: templates/ (new QUESTIONS template), scripts/ (new register check), skills/finishing-a-development-branch and skills/brainstorming (where the register is written and checked)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Scope-deciding sentences, in chronological order:

> check issue https://github.com/minhtran3124/agent-harness/issues/258, xem thu da implement het cac item trong table rollout chua?

> start for item #3 now

Item 3 of GitHub issue #258 (https://github.com/minhtran3124/agent-harness/issues/258), Target as written in the issue:

> - An optional `specs/<slug>/QUESTIONS.md` for multi-phase specs, next to `ESCALATIONS.md`, with the fields `OQ-n`, raised-by, closes-at (phase/task), decided-by (measurement | owner), default-until-closed, and status.
> - A traceability-tier gate: a phase cannot ship while a question with `closes-at` equal to that phase is still open. Warn-first.
> - This touches `scripts/` and the gate set, so it runs as its own high-risk-lane change. It is **not** part of the first batch.

Items 5, 6 and 7 of #258 are out of scope for this spec. The branch is cut from `spec-format`; the PR targets `--base spec-format`.

Confidence is `medium`, not `high`: the target is written in #258, but two details have a
documented default rather than a single reading, to be settled in brainstorming. (a) What a
"phase" is and when it "ships": the default is that `closes-at` names a `PLAN.md` task id or a
phase label the spec defines, and "ship" is the plan's `status: shipped` transition in
`finishing-a-development-branch`. (b) Where the gate runs: the default is a `scripts/` check
called by the finishing flow and CI, warn-first, not a new `hooks/commit-gate.sh` check
(which would add the high-blast gate).

## What changed

A multi-phase spec can keep an optional `specs/<slug>/QUESTIONS.md` of non-blocking unknowns, from the new `templates/QUESTIONS.template.md`. Each `## OQ-<n>` block names `raised-by`, `closes-at` (a phase slug, optionally `#<task>`), `decided-by` (`measurement` | `owner`), `default-until-closed`, `status` (`open` | `closed`) and, when closed, `closed-by`.

The new stdlib script `scripts/check_open_questions.py --slug <X>` reads every register. It reports open questions that close at `X`, and any malformed or unreadable register. It warns (exit 0) by default and blocks (exit 1) under `REQUIRE_QUESTIONS_CLOSED=1`. The script runs in two places:
- **Finish skill, step 3:** before a plan is marked `shipped`.
- **`scripts/ci-strict-gate.sh`:** a new section runs for every plan that becomes `shipped` in a PR. It sits before the gate's early exit and never bypasses the existing tiers.

The script also ships to consumer repos through `CONSUMER_SCRIPTS`. Brainstorming step 5 and the specs README point multi-phase specs at the register.

### Rationale

Warn-first was asked for, so the check is a standalone script called by the finish flow and by CI, not a `hooks/` check. A hook would add the high-blast gate for a block that is not wanted yet. `closes-at` names a spec slug because multi-phase work in this repo is already one slug per phase (`codex-support-phase-N`, `gh-129-…-phase-a…d`), so no new frontmatter field is needed.

### Alternatives considered

- Fold the check into `verify_summary.py --check`: rejected. It widens the script that decides what every gate accepts as evidence, and it would run outside ship time.
- A `hooks/commit-gate.sh` check on a staged `status: shipped`: rejected for now. It is high-blast, and its only advantage, a hard block, is not wanted while the gate is warn-first. It is the upgrade path once precision is measured.
- `closes-at` as a free-form phase label (`Phase 6`): rejected. It needs a new PLAN frontmatter field to map labels to specs.

### Deviations

All from the correctness fix round the user chose ("Sửa cả 8"), commits `3aa6b94`, `0328cfb`, `142c29e` and `f24e6e1`:
- Rule 1: `plan_shipped` in `scripts/ci-strict-gate.sh` stopped reading at the closing frontmatter, so `git show` could die of SIGPIPE (141) under `pipefail` and a shipping phase read as not shipped. It now reads all input.
- Rule 1: `scripts/ci-strict-gate.sh` read any exit 1 as "findings": a crash blocked in warn mode, and exits 2/127 passed under `REQUIRE_QUESTIONS_CLOSED=1`. Exit codes are now captured: findings, check errors and a missing script are separate causes, each named in its own BLOCKED line.
- Rule 1: the status match is case- and leading-whitespace-insensitive, like `render_plan.py`.
- Rule 1: the shipping plan list uses `git -c core.quotePath=false`, so non-ASCII slug paths are found; `closes-at` validation now accepts non-ASCII slugs too (`0328cfb`).
- Rule 1: a heading that starts with `OQ-` at any `#` depth or case but is not exactly `## OQ-<n>` is reported as malformed instead of dropping its block; a prose heading such as `## Notes on OQ-1` is not (`0328cfb`).
- Rule 1: registers are read as `utf-8-sig`, so a byte-order mark no longer hides the first block.
- Rule 3: `from __future__ import annotations` added to `scripts/check_open_questions.py` and its test file (Python 3.8; closes the Task 1.1 Minor).
- Rule 1: a field repeated in one block is reported as `duplicate field <name>`; the first value is still used for matching.
- Rule 1: the re-check found that `0328cfb` had loosened `closes-at` so far that `` `phase-6` ``, `"phase-6"` or `phase-6.` passed as valid and an open question was silently missed. `closes-at` is now Unicode word characters plus `.`/`-`, and the slug and the task part each start and end with a letter or digit (`142c29e`, `f24e6e1`).

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 .claude/scripts/verify_summary.py --lane gh-258-open-questions-register` | 0 | | |
| check script exit codes match the error-behavior table | `python3 -m pytest scripts/test_check_open_questions.py -q` | 0 | 37 passed (run with the shared venv first on PATH; CI installs pytest on python3) | SC-1 |
| ci-strict-gate shipping section, old and new cases | `bash tests/scripts/ci-strict-gate.test.sh` | 0 | 35 passed: 19 existing + (a)–(e) + fix-round cases (f) SIGPIPE, (g) exit codes, (h) capitalised status, (i) non-ASCII slug | SC-2 |
| deployed consumer copy reads the consumer's specs/ | `bash tests/scripts/consumer-subset.test.sh` | 0 | 17 passed | SC-3 |
| finish skill runs the check before shipping | `bash tests/scripts/finishing-branch-contract.test.sh` | 0 | 5 passed | SC-4 |
| template, brainstorming sentence, specs README row | `bash tests/scripts/brainstorming-contract.test.sh` | 0 | 10 passed | SC-5 |
| source and derived doc paths exist | `bash scripts/lint-doc-truth.sh` | 0 | | SC-6 |
| skills within the 600-word ceiling | `python3 scripts/audit_skill_prompts.py` | 0 | finishing 528, brainstorming 441 | SC-7 |

Full suite (design SC-6; not a Verify row, per `rules/plan-format.md` Guardrail 4): `bash scripts/run-tests.sh` → 836 passed, ALL GREEN at `f24e6e1`, 2026-10-09.

### Correctness Review

Range `bb3aad7..1423884` (`.harness-state/sdd/package-branch.md`), six FIND angles, 8 locations after dedup, one independent scorer each, threshold 75. All 8 scored 50 and none reached 75. The user chose to fix all 8 ("Sửa cả 8"), at `3aa6b94` and `0328cfb` (see `### Deviations`).

A focused re-check of `1423884..0328cfb` found:
- 7 of 8 closed;
- item 2 closed except one case, below;
- one regression the fix round introduced, the over-loose `closes-at`. It was fixed at `142c29e` and re-checked as closed. The task-start nit from that re-check was fixed at `f24e6e1`, with a test.

Remaining advisories (not fixed):
- Under `REQUIRE_QUESTIONS_CLOSED=1`, an uncaught Python exception in the check exits 1, so CI's BLOCKED line says "open questions" rather than "errored". It still blocks, the safe direction, and the traceback is on stderr. Re-check confidence 25.
- `Status: shipped` with a capitalised key counts as shipped in CI but not in `render_plan.py`. It errs toward running the check. Confidence 0–25.
- A `#`-led line inside a fenced code block in a register is parsed as a heading. Confidence 25.
- A later `- status:` bullet under a block is now a duplicate-field finding (intended by fix 8).
- Paths containing `"`, `\` or control characters are still quoted by git even with `core.quotePath=false`. Negligible.

### Intent Findings

Intent review (plan-blind) over `bb3aad7..1423884`: no ambiguity, nothing escalated. Every intent clause is satisfied: optional register next to `ESCALATIONS.md`, the six requested fields, a traceability-tier ship check keyed on `closes-at`, warn-first, its own high-risk change, items 5–7 untouched. The reviewer re-ran SC-2..SC-7 and the full suite (ALL GREEN, pytest 818 passed).

- **gap (proof only):** design SC-6, "`bash scripts/run-tests.sh` stays green", has no `### Verify` row. Resolved by recording it here: `rules/plan-format.md` Guardrail 4 forbids a whole-suite Verify row; the suite runs at finish and in CI, and the result is noted under `### Verify`.
- **excess (report only):** a seventh field, `closed-by`, is required on closed blocks. The issue lists six fields; the design's field table (approved 2026-10-09) added `closed-by` so a closed question names its evidence. Kept; removing it is a human call.
- **drift (advisory):** malformed registers anywhere are reported on every ship (design D5), so under `REQUIRE_QUESTIONS_CLOSED=1` one broken register in another spec fails every shipping phase. Stated in design "What we do not claim".
- **drift (advisory, equivalent):** `closes-at` accepts `<slug>` or `<slug>#<task>`; a free-form phase label is not accepted (design D1, A2 accepted risk).
- **drift (advisory, equivalent):** in consumer repos the check runs only through the finish skill's prose step; only this repo's CI runs it mechanically. Stated in design "What we do not claim".

### Context-Propagation Audit

**Result: PASS.** Range `ce074a0..HEAD`. Search surface:
- `git diff --stat ce074a0..HEAD -- . ':!specs'`, which lists 12 files.
- `grep -rln "finishing-a-development-branch\|brainstorming/SKILL\|QUESTIONS"` over `adapters/`, `agents/`, `scripts/render_codex_adapter.py` and `scripts/render_skill_prompt.py`. No isolated prompt or agent definition names the changed text.
- `scripts/render_codex_adapter.py`. The Codex plugin ships `./skills/` whole.

No changed sentence is pasted into a subagent prompt. Every consumer reads it in the main session.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `finishing-a-development-branch/SKILL.md` step 3 (run the check, PR-body list) | finish controller | main | the skill body, loaded on invocation | `finishing-branch-contract.test.sh` (5 passed) |
| same | consumer repo finish controller | main | deployed skill with `scripts/` rewritten to `.claude/scripts/`; script shipped through `CONSUMER_SCRIPTS` | `consumer-subset.test.sh` (17 passed): the deployed copy resolves and reads the consumer's `specs/`; `lint-doc-truth.sh` exit 0 |
| `brainstorming/SKILL.md` step 5 (record non-blocking unknowns) | brainstorming controller | main | the skill body, loaded on invocation | `brainstorming-contract.test.sh` (10 passed) |
| `templates/QUESTIONS.template.md` (fields, blocking-question sentence) | brainstorming controller writing a register | main | explicit path in the step-5 sentence (same convention as `templates/SUMMARY.template.md` in feature-intake); `templates/` deploys to consumers | `brainstorming-contract.test.sh` template case; `lint-doc-truth.sh` exit 0 |
| `templates/structure/specs-README.md` row | humans and agents browsing `specs/` | main | the README copied by init-structure | `brainstorming-contract.test.sh` README case |
| `scripts/ci-strict-gate.sh` shipping section | CI `strict-gate` job | CI (harness repo only; not deployed) | runs on every PR (`harness-ci.yml`) | `ci-strict-gate.test.sh` (35 passed after the fix round) |
| isolated prompt contracts (unchanged) | design reviewer, task reviewer, scorers | subagent | `CONTEXT_MATRIX` | `render_skill_prompt.py --check-all`: "all contracts present" |

**Advisory (not a failure):** the Codex plugin ships the skill text unchanged. The finish skill's `python3 scripts/check_open_questions.py` call therefore depends on how the Codex alpha provides helper scripts, which is the same dependency the skill's other `scripts/` helpers already have. This branch does not change it. Traceability tier only; no Codex run was observed.

### Minor review findings

- Task 1.1 (`1dd461d`): a `--root` that is not a directory finds no register and exits 0 silently, the same as "no register anywhere" (`scripts/check_open_questions.py`). Open; both callers run from the repository root.
- Task 1.1 (`1dd461d`): the test file needed `from __future__ import annotations` for Python below 3.10. Closed by `3aa6b94`.
- Task 1.1 (`1dd461d`): any `#` line ends an OQ block, so a subheading inside a block drops later fields, and an `## OQ-n` inside a code fence is parsed. Open (also a correctness advisory, confidence 25); the template's bullet-only shape avoids both.
- Task 2.1 (`2e8b098`): the combined BLOCKED line named the wrong cause when the script was missing. Closed by `3aa6b94`, which gives each cause its own BLOCKED line.
- Task 2.2 (`97b8a2c`): finishing step 3 says what to do in warn mode but not that an exit 1 under `REQUIRE_QUESTIONS_CLOSED=1` stops the flow (`skills/finishing-a-development-branch/SKILL.md:63-64`).
- Task 2.3 (`a6e01d0`): the template field-key anchors in `brainstorming-contract.test.sh` are bare fixed strings, so they prove each key appears somewhere in the template, not inside an `## OQ-<n>` block.

### Rollback

- `git revert -m 1 <merge-sha>` of the PR into `spec-format`.

### Not auto-verified

- That a closed question was answered correctly, or that its `closed-by` evidence is true. Traceability tier only: the check reads the fields, not the evidence.
- That every shipping path is checked. A direct commit of `status: shipped` with no finish step and no PR is not seen; only a `hooks/` check would see it. Judgment-tier, stated in the design.
- That a Codex controller runs the finish-step check. Traceability only: the skill text ships whole, but no Codex run was observed.
- Python 3.8 compatibility. Traceability only: the `from __future__` line is present, but no 3.8 interpreter was available to run the script.

### Harness-Delta

- backlog (Task 2.3 implementer): the worktree-isolation Bash guard refuses compound commands (`bash x; echo exit=$?`, heredocs, `cd … &&`), and implementers learn this by trial. Briefs could state it up front. Every implementer and reviewer in this run hit it at least once.
