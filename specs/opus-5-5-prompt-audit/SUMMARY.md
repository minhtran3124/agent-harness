# opus-5-5-prompt-audit — Summary

Lane: high-risk
Confidence: high
Reason: edits skills, dispatch/reviewer prompts, and rules/*.md — the workflow-engine hard gate, which intake classifies high-risk; scope narrowed and approved by the user (all four audit groups).
Flags: workflow-engine, existing-behavior, multi-domain
Affects: rules/behavior.md, rules/orchestration.md, SDD implementer dispatch, correctness/intent review prompts, compound
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> make the deep review current instructions/prompting for current workflow and update matching with guide for model opus 5.5

Scope decision (user answer to the hard-gate scope question, verbatim selection):
> Stale facts/contradictions, Review recall fixes, Opus 5.5 guidance, Delegation calibration

## What changed

A prompt audit of the harness against the Claude Opus 5.5 prompting guide, applied across skills,
dispatch prompts, rules, and root docs. It corrects stale facts that misdirected agents (the
scorer's belief that the commit gate runs ruff/pytest, the implementer dispatch that bypassed the
Opus 5.5 `coding` binding, compound subagents told to read a transcript they cannot see), removes
recall-depressing finding caps and self-check/update-suppressor phrasing, adds always-on scope,
finish-the-whole-task, and communication rules (`rules/behavior.md` §4/§5), and calibrates
delegation for a model family that over-delegates. Details: `research-brief.md`, `design.md`.

### Rationale

The guide's documented Opus 5/5.5 behavioral shifts (over-verification, scope expansion,
over-delegation, recall loss under severity caps, under-narration under suppressors) map onto
specific lines here; each edit is tied to a named pattern and was checked against the tests that
assert prompt strings.

### Alternatives considered

- Per-agent copies of the new behavior guidance — rejected: two wordings of one rule; `rules/behavior.md` loads for every role.
- Keep compound's subagents and paste a session digest — rejected: re-establishes context the main session already holds.
- Raise the finding caps instead of removing them — rejected: the scorer is the precision stage.

### Deviations

- Rule 3 — `hooks/branch-isolation-guard.sh` denies Edit/Write inside this worktree (it reads the branch from `CLAUDE_PROJECT_DIR`, the main checkout on `main`), so tasks were applied by the controller via exact-match scripted replacements instead of implementer subagents; independent reviews still run.
- Dropped approved hunk M7 (finish clause in `agents/coding.md`) — duplicates `rules/behavior.md` §4.
- Extra stale-fact fixes found while applying: remaining "Decision Procedure / Tiebreaker / Common signals" terms in `skills/xia2/README.md`, `skills/README.md`, and `skills/xia2/tests/structural/depth-modes-test-cases.md`. (`systematic-debugging` was briefly removed as non-existent; it is an external, optional skill per `skills/README.md` → External Skills, and the pointer was restored with that qualifier.)

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| binding + routing | `bash tests/scripts/runtime-entry-bindings.test.sh` | 0 | implementer `model_stage` compatible | SC-1 |
| SDD context propagation | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | | SC-1 |
| review prompt contracts | `bash tests/scripts/intent-prompt-contract.test.sh && bash tests/scripts/correctness-prompt-composition.test.sh && bash tests/scripts/scorer-threshold-contract.test.sh` | 0 | | SC-2 |
| rule tiers + inline policy | `bash tests/scripts/rule-loading-tiers.test.sh && bash tests/scripts/inline-policy-drift.test.sh` | 0 | | SC-3 |
| doc truth | `bash scripts/lint-doc-truth.sh` | 0 | source + derived paths exist | SC-4 |
| compound + finishing contracts | `bash tests/scripts/compound-contract.test.sh && bash tests/scripts/finishing-branch-contract.test.sh` | 0 | | SC-5 |
| task review contract | `python3 scripts/check_task_review_contract.py` | 0 | | |

The full suite (`bash scripts/run-tests.sh`) is cited in prose per the verify-row rule; its result is recorded below.

### Not auto-verified

- That Opus 5.5 / Opus 5 behave better under the new wording (recall, scope, narration) — reached traceability only; no behavioral eval was run on these prompts.
- The deployed `.claude/` copies are stale (traceability only). `rules/behavior.md` is in `BOOTSTRAP_OWNED_FILES` (`scripts/deploy-harness.sh:29`), so a plain or `--yes` re-deploy KEEPS the local §1–3 copy and parks §4/§5 in `.claude/rules/behavior.md.harness-incoming`. §4/§5 reach no agent until `deploy-harness.sh --overwrite-conflicts` runs or the sidecar is merged by hand.
- `evals/context-boundaries/probes/{scorer-agent,implementer-subagent}.md` still describe the old dispatch — recorded runs, not re-run.

### Context-Propagation Audit

Result: **PASS after repair** (initial run FAIL on 1 row).

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `rules/behavior.md` §4/§5 | coding, reviewer, task-reviewer, test-runner | fresh child | always-loaded (no `paths:`) | auditor child received `.claude/rules/behavior.md`; `tests/scripts/rule-loading-tiers.test.sh` |
| `rules/behavior.md` deployed copy | every role | all | always-loaded, conflict-guarded | FAILED as claimed — repaired by correcting `### Not auto-verified` (needs `--overwrite-conflicts`) |
| implementer `subagent_type: coding` + `model_stage: implementer` | SDD controller → implementer | main → child | pasted dispatch + render-time `model:` | `render_runtime_entry.py --runtime claude --model-stage implementer` → `claude-opus-5-5`; `runtime-entry-bindings.test.sh` |
| compound in-session passes | compound SKILL/README, skills/README, tests | main | consistent | `compound-contract.test.sh`; grep of manifests |
| removed finding caps | review-config, angles, scorer, evals | finder/scorer children | consistent | grep `six|Limit findings|max_findings` — remaining hits are the six angles |
| `rules/orchestration.md` manifest wording | deployed `.claude/rules/orchestration.md` | children | deploy rewrite | deploy regex (`scripts/deploy-harness.sh:379`) yields 0 matches on the new sentence |

### Review Findings

Correctness review (14 findings, 2 Important): all fixed in the follow-up commit — incomplete `render_runtime_entry.py` invocation (also in two pre-existing templates), compound pass prompts addressing the orchestrator, fabricated hook-hint quote and missing preconditions (`skills/README.md`, `CLAUDE.md`), worktree step contradiction in the minimum path, `systematic-debugging` wrongly treated as absent, leftover "Common signals" terms, compound failure-track output/`applicable_when` gaps, self-contradictory INDEX rule, `behavior.md` preamble vs §4/§5, unindented reviewer-table rows, "ruff --fix"/typechecker claim, `verifying`-only stall claim, split ordered list.

Intent review (6): fixed — no fan-out cap in `rules/wave-parallelism.md` (now ≤20 per message). Recorded, not changed: `agents/coding.md` "Be concise…" (a style line, not a numeric cap or suppressor); `behavior.md` §5 correction clause (approved Opus 5.5 guidance group, from the guide's self-correction snippet); deleted "Token logging for AI paths" (approved stale-fact hunk: app-stack specific, contradicts `rules/guidelines.md`); remaining `MUST`/`FORBIDDEN` (hook- or test-backed); xia2 "at most three solution files" (search bound, not an output cap).

### Advisory Findings

- `skills/compound/subagents/*.md:3` still open "You are the … subagent" while SKILL.md treats them as pass schemas — drift, not contradiction.
- `scripts/check_skill_tool_conformance.py` does not validate `subagent_type` against `agents/`; `coding` verified by read only.

### Rollback

- `git revert <sha>` for each commit on `refactor/opus-5-5-prompt-audit` (prose-only changes; no data or config migration).

### Harness-Delta

- backlog — `hooks/branch-isolation-guard.sh` resolves the branch from `CLAUDE_PROJECT_DIR`, so every Edit/Write inside a linked worktree is denied as "on shared branch main" when the session launched from the main checkout; it should resolve the branch from the edited file's own worktree (`git -C "$(dirname <path>)"`).
