# gh-258-sc-goalpost-guard — Summary

Lane: high-risk
Confidence: medium
Reason: changes scripts/verify_summary.py, the script that decides what every other gate accepts as evidence (CI warn tier for scripts/), adding a new warn-first gate over branch history; #258 itself names it a separate high-risk-lane change; flags existing behavior, weak proof, multi-domain
Flags: existing behavior, weak proof, multi-domain, new gate
Affects: scripts/verify_summary.py (evidence authority for commit-gate lane check, ci-strict-gate, finishing), SUMMARY.md / PLAN.md SC contract
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Scope-deciding sentences, in chronological order:

> check issue https://github.com/minhtran3124/agent-harness/issues/258, xem thu da implement het cac item trong table rollout chua?

> merged. start item 5 tiep theo

Item 5 of GitHub issue #258 (https://github.com/minhtran3124/agent-harness/issues/258), as written in the issue:

> **Purpose.** It stops a failing acceptance check from being quietly weakened until it passes.
>
> **Gap in our harness.** The `weakening-validation` signal is warn-mode and diff-based. Nothing ties a changed `SC-n` `Expected` value to the run where that row failed.
>
> **Target.** `scripts/verify_summary.py` warns when an `SC-n` row's `Check` or `Expected` changes in the same branch where that row is recorded as failing, unless `### Deviations` has an entry that names the row. Warn-first, the same rollout pattern as `weakening-validation`. Separate high-risk-lane change.

Items 6 and 7 of #258 are out of scope for this spec. The branch is cut from `spec-format`; the PR targets `--base spec-format`.

Confidence is `medium`, not `high`: the target is written in #258, but two details have a
documented default rather than a single reading, to be settled in brainstorming. (a) What
"recorded as failing" means: the default is that some commit in the branch (`merge-base..HEAD`)
has a `SUMMARY.md` `### Verify` row whose `Criterion` is that `SC-n` with a non-zero `Exit`
(or an `Exit` that differs from the row's `Expected`). (b) Where and when the warning runs: the
default is a `verify_summary.py` mode that needs a base ref, called where `--check` already runs
(the finish flow and `ci-strict-gate.sh`), warn-first with an env flag to block.

## What changed

<filled at ship time>

### Rationale

<filled at ship time>

### Alternatives considered

- none yet (brainstorming)

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| intake lane record | `python3 .claude/scripts/verify_summary.py --lane gh-258-sc-goalpost-guard` | 0 | |

### Minor review findings

- Task 1.1 (`2a47380`): `_run_sc_history` reports any later git failure (`rev-list`, `rev-parse --short`) as "not inside a git repository, or git cannot run". The exit code (2) is correct, but the message names the wrong cause, and `_git` drops git's stderr.
- Task 1.1 (`2a47380`): `test_base_without_sc_history_is_a_usage_error` calls `subprocess.run` directly instead of the env-scrubbing `run()` helper.
- Task 1.1 (`2a47380`): `REQUIRE_SC_STABLE` blocks only on exactly `"1"`, while `REQUIRE_NOT_AUTO_VERIFIED` accepts any truthy value (implementer note).

### Rollback

- `git revert -m 1 <merge-sha>` of the PR into `spec-format`.

### Not auto-verified

- none yet

### Harness-Delta

- backlog (high impact): a `deploy-harness.sh` run in the **main checkout** at 21:02:08 on 2026-10-09 (the `.claude/.harness-profile` mtime) rewrote 173 tracked Markdown files in this worktree. It replaced `scripts/` with `.claude/scripts/` and stripped harness-only regions; `skills/README.md` lost 127 lines. This worktree lives at `<repo>/.claude/worktrees/<name>`, inside the parent's derived `.claude/` tree, and the parent's derive-time transforms (`rewrite_derived_paths`, `strip_maintenance_docs`) walk that tree recursively. The rewrite reached this spec's `### Intent` block, which is the verbatim intent-review oracle. No code, test or run-state file was touched, and every commit made before 21:02 was clean. The controller saved the diff to `.harness-state/parent-deploy-clobber-2026-10-09.patch` and restored the files with `git restore --worktree -- .`. Fix direction: the deploy transforms must skip `.claude/worktrees/`. Also, `EnterWorktree` only accepts `.claude/worktrees/`, so every harness-native worktree is exposed to this.
