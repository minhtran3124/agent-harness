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
- Extra stale-fact fixes found while applying: `xia2/README.md` reference to a non-existent `systematic-debugging` skill and remaining "Decision Procedure / Tiebreaker / Common signals" terms.

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
- That the deployed `.claude/` copies match — not redeployed; stale until the user runs `deploy-harness.sh`.
- `evals/context-boundaries/probes/{scorer-agent,implementer-subagent}.md` still describe the old dispatch — recorded runs, not re-run.

### Rollback

- `git revert <sha>` for each commit on `refactor/opus-5-5-prompt-audit` (prose-only changes; no data or config migration).

### Harness-Delta

- backlog — `hooks/branch-isolation-guard.sh` resolves the branch from `CLAUDE_PROJECT_DIR`, so every Edit/Write inside a linked worktree is denied as "on shared branch main" when the session launched from the main checkout; it should resolve the branch from the edited file's own worktree (`git -C "$(dirname <path>)"`).
