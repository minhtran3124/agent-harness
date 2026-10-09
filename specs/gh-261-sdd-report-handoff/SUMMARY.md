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

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane gh-261-sdd-report-handoff` | 0 | intake-time check only | |

### Not auto-verified

- none

### Rollback

- Prose and contract-test change to the SDD handoff; undo with `git revert -m 1 <merge-sha>` of the PR.
- Consumers that re-synced keep the new handoff text until their next re-sync after a revert. A locally edited protected file (`rules/orchestration.md` is not bootstrap-owned; skills are synced) lands beside the incoming copy as `.harness-incoming`.

### Harness-Delta

- `scripts/rebuild_solution_index.py --check` also compares the `> Last updated:` date, so on `main` it reports "INDEX.md is stale" any day after the last rebuild, even when every entry is current (observed 2026-10-09: the only diff was the date). This PR's SC-5 compares everything except that line. backlog: make `--check` ignore the date line.
