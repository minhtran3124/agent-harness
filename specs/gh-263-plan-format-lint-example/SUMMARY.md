# gh-263-plan-format-lint-example — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate — the fix edits `rules/plan-format.md`, a rule that writing-plans and the plan reviewer Read before authoring and reviewing Success Criteria
Flags: workflow-engine
Affects: rules/plan-format.md (Success Criteria schema example)
Input-type: maintenance
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

> fix #263 trước đi

Issue #263 (https://github.com/minhtran3124/agent-harness/issues/263): the fenced Success Criteria example in `rules/plan-format.md` (lines 99–100 on `main`) uses `python3 scripts/verify_summary.py --lint specs/<slug>`, which exits 2 ("unrecognized arguments: --lint"), not the `exit 1` / `exit 0` its Expected cells claim. Target: replace it with a command that exists and behaves as the Expected column says. The issue marks extending a lint to catch this class as optional.

Confidence is `high`: observed at intake, `python3 scripts/check_plan_contract.py <PLAN.md>` exits 1 on a contract plan with no SC rows ("Success Criteria table has no SC rows") and 0 on a well-formed one, which matches the example's two Expected cells. The optional lint is a scope question for brainstorming, not an ambiguity in the fix.

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
| intake lane record | `python3 scripts/verify_summary.py --lane gh-263-plan-format-lint-example` | 0 | intake-time check only | |

### Not auto-verified

- none

### Rollback

- Prose-only change to one fenced example in `rules/plan-format.md`; undo with `git revert -m 1 <merge-sha>` of the PR.
- Consumers that re-synced keep the corrected example until their next re-sync after a revert; a locally edited `rules/plan-format.md` is kept and the incoming copy lands beside it as `.harness-incoming`.

### Harness-Delta

- none
