# gh-261-sdd-report-handoff — Summary

Lane: high-risk
Confidence: medium
Reason: workflow-engine hard gate — the fix edits the SDD dispatch prompts (`implementer-prompt.md`), `skills/subagent-driven-development/SKILL.md` and the always-on `rules/orchestration.md` subagent contract
Flags: workflow-engine, existing behavior
Affects: subagent-driven-development implementer → task-reviewer handoff; rules/orchestration.md "Subagent contract"
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> ok open issues cho
> """
> - Subagent không ghi được report vào .harness-state/sdd/, nên mình phải tự chép report của chúng.
> - Hook branch-isolation chặn ghi file ở thư mục gốc của scratchpad.
> - Ví dụ verify_summary.py --lint trong plan-format.md gọi một flag không tồn tại
> """

> sau đó fix #261 tiếp đi

Issue #261 (https://github.com/minhtran3124/agent-harness/issues/261): the SDD implementer handoff tells each implementer to write its report to `[IMPLEMENTER_REPORT_PATH]` under `.harness-state/sdd/`, but on the gh-258 run all four implementers were refused. The Write tool refused, and the Bash heredoc fallback was refused by the worktree-isolation check. The controller transcribed each inline report by hand. Target: decide which side owns the report file, either (a) the controller writes it from the implementer's inline return, or (b) subagents can write the path. Then make the prompts, SKILL and rule say so, and pin the contract with a test.

Confidence is `medium`: the goal is clear, but (a) and (b) are materially different designs. The documented default is (a), which #261 itself prefers: it does not depend on a runtime policy outside the harness, so it also holds on Codex. Brainstorming confirms the choice.

## What changed

<filled at finishing-a-development-branch>

### Rationale

<filled at finishing-a-development-branch>

### Alternatives considered

- none

### Deviations

- Rule 3: the full suite failed `scripts/test_audit_skill_prompts.py`. The SDD `SKILL.md` was already at the 600-word progressive-disclosure ceiling on `main`, and the new bullet took it to 646. The SKILL bullet now keeps only the core rule. The header, rewrite-after-fix and no-file-on-`BLOCKED`/`NEEDS_CONTEXT` details moved to the always-on `rules/orchestration.md` Subagent contract, departing from design §4.2's placement (behavior unchanged). Commit `974e686`.
- Rule 1: the task re-review noted that the moved details live only in `rules/orchestration.md`, which the Codex adapter does not load through `agents/PROJECT.md`. The SKILL bullet now names `rules/orchestration.md` by path (598 words). Commit `cf0567d`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane gh-261-sdd-report-handoff` | 0 | intake-time check only | |
| handoff presence/absence checks | `bash tests/scripts/sdd-artifact-handoffs.test.sh` | 0 | sdd-artifact-handoffs: passed | SC-1 |
| task-reviewer contract unchanged | `python3 scripts/check_task_review_contract.py` | 0 | task-review-contract: passed | SC-2 |
| isolated-prompt deliveries hold | `python3 scripts/render_skill_prompt.py --check-all` | 0 | all contracts present | SC-3 |
| backlog closed, guardrail existing, affects orchestration | `python3 -c "import sys;b=open('docs/harness-experimental/improvement-backlog.md').read();s=open('docs/solutions/harness/sdd-report-file-handoff-refused-for-subagents.md').read();sys.exit(0 if 'done (2026-10-09, gh-261)' in b and 'existing:' in s and 'proposed:' not in s and 'rules/orchestration.md' in s else 1)"` | 0 |  | SC-4 |
| INDEX matches a fresh rebuild (date line ignored) | `python3 -c "import subprocess,sys;n=subprocess.run([sys.executable,'scripts/rebuild_solution_index.py','--dry-run'],capture_output=True,text=True).stdout;f=open('docs/solutions/INDEX.md').read();k=lambda t:[l for l in t.splitlines() if not l.startswith('> Last updated')];sys.exit(0 if k(n)==k(f) else 1)"` | 0 |  | SC-5 |
| SKILL.md word ceiling | `python3 scripts/audit_skill_prompts.py --json` | 0 | SDD SKILL.md 598 words (ceiling 600) |  |

### Context-Propagation Audit

**Result: PASS**, with one advisory. Search surface: `grep -rnI` for `IMPLEMENTER_REPORT_PATH`, `report-<task>`, `report file`, `harness-state/sdd`, `orchestration.md` over `skills/`, `rules/`, `agents/`, `adapters/`, `scripts/`, `tests/`, plus `adapters/codex/project/harness-instructions.md` and `agents/PROJECT.md`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `implementer-prompt.md` Report Format ("do not write a report file") | implementer | subagent (isolated) | pasted (the dispatched prompt text) | `sdd-artifact-handoffs.test.sh` presence check |
| SDD `SKILL.md` bullet ("the controller writes it verbatim to `report-<task>.md`") | SDD controller | main | the skill body, loaded on invocation | `sdd-artifact-handoffs.test.sh` presence checks |
| `rules/orchestration.md` Subagent contract (header, rewrite after fix, no file on BLOCKED/NEEDS_CONTEXT) | SDD controller (Claude) | main | always-on rule (no `paths:` frontmatter) | `tests/scripts/rule-loading-tiers.test.sh` exit 0 |
| same | SDD controller (Codex advisory) | main | explicit path in the SKILL bullet (`per rules/orchestration.md`, `cf0567d`); Codex rules otherwise come from `agents/PROJECT.md`, which does not name `orchestration.md` | **Advisory:** the pointer is present, but Codex Reading it is not proven (traceability only) |
| `IMPLEMENTER_REPORT_PATH` input | task reviewer | subagent (isolated) | unchanged; the controller now fills the path | `check_task_review_contract.py` exit 0 |
| solution entry Guardrail `existing:` | planning / compound sessions | main | `docs/solutions/INDEX.md` plus the `session-knowledge.sh` pointer | SC-5 (INDEX matches rebuild) |

### Not auto-verified

- The controller copies the report verbatim. Judgment-tier: the "transcribed by controller" header marks where the file came from; nothing compares it to the implementer's return.
- A Codex controller reads `rules/orchestration.md` through the SKILL pointer. Traceability only: the pointer is present, and no Codex run was observed.

### Minor review findings

- Task 1.1 (`7523f0c`): an overlong SKILL.md line. Resolved by the fix-round rewrite (`974e686`, `cf0567d`).
- Task 1.2 (`6a36b3c`): the closed backlog row's Proposal cell still says "plus a context-propagation regression presence case". Left as the historical proposal; the solution entry's Guardrail says where the checks actually live.
- Task 1.1 fix round: the details split across SKILL.md and orchestration.md. Addressed by the explicit path pointer (`cf0567d`).

### Rollback

- Prose and contract-test change to the SDD handoff; undo with `git revert -m 1 <merge-sha>` of the PR.
- Consumers that re-synced keep the new handoff text until their next re-sync after a revert. A locally edited protected file (`rules/orchestration.md` is not bootstrap-owned; skills are synced) lands beside the incoming copy as `.harness-incoming`.

### Harness-Delta

- `scripts/rebuild_solution_index.py --check` also compares the `> Last updated:` date, so on `main` it reports "INDEX.md is stale" any day after the last rebuild, even when every entry is current (observed 2026-10-09: the only diff was the date). This PR's SC-5 compares everything except that line. backlog: make `--check` ignore the date line.
