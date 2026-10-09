# gh-277-strict-gate-no-merge-base — Summary

Lane: normal
Confidence: high
Reason: no manifest hard gate (scripts/ci-strict-gate.sh is not high-blast; tests/ is not hooks/); two files, no new public callable, so not tiny; flags existing behavior (the gate's verdict changes on an edge case) and cross-platform (git's no-merge-base failure must be detected on ubuntu and macos CI)
Flags: existing behavior, cross-platform
Affects: scripts/ci-strict-gate.sh (CI strict gate, PR-only), tests/scripts/ci-strict-gate.test.sh
Input-type: maintenance
Route: using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> /feature-intake https://github.com/minhtran3124/agent-harness/issues/277

Issue #277, "ci-strict-gate exits 0 having checked nothing when BASE and HEAD share no merge base" (scope-deciding sentences):

> An unresolvable diff is an error, not an empty diff. The gate should exit non-zero with a message naming the missing merge base, or at least fail when any `REQUIRE_*` flag is set.
>
> - Separate a failing `git diff` from an empty one. Capture the exit code instead of `|| true`, and fail closed when it is non-zero.
> - Add a `ci-strict-gate.test.sh` case: an orphan HEAD against a base with no common history gives exit 1 and a message mentioning the merge base.
>
> Verifies: a diff the gate cannot compute is never treated as "nothing to check". Does not verify: that the chosen base is the right one; `resolve-base-ref.sh` owns that.

Interpretation picked: the issue offers two readings — always fail closed, or fail only under a
`REQUIRE_*` flag. The fix direction and the requested test (exit 1 with no flag named) select
**always fail closed** on a non-zero `git diff`; the weaker reading is not implemented.

## What changed

- `scripts/ci-strict-gate.sh`: the PR diff is now `DIFF=$(git diff --name-only "$BASE"...HEAD 2>/dev/null); DIFF_RC=$?`. A non-zero status exits 1 with a `ci-strict-gate:` error on stderr — `no merge base between '<base>' and HEAD` when `git merge-base` also fails, otherwise git's own failure text. A status-0 empty diff still exits 0. The comment above the base check no longer describes the removed `|| true`. Commit `fa6162f`.
- `tests/scripts/ci-strict-gate.test.sh`: an `orphan_run` helper (orphan branch that commits `hooks/foo.sh`, gate run against the original base sha) and two cases — default mode and `REQUIRE_SC_STABLE=1` — each asserting exit 1 and `no merge base between`. Red phase: both failed against the old script (`47 passed, 2 FAILED`).

### Rationale

- The test asserts on the script-owned phrase `no merge base between`, not bare `merge base`: git's own fatal (`...HEAD: no merge base`) already contains `merge base`, so a fix that only dropped `|| true` would have passed a weaker assertion without the required message.
- stderr stays out of `DIFF` on the success path, so git warnings (for example rename-limit notices) never enter the changed-file list.
- The `MERGE_BASE=$(git merge-base "$BASE" HEAD 2>/dev/null || true)` line is left unchanged: a `"$BASE"...HEAD` diff succeeds only when a merge base exists, and the gate now exits 1 whenever that diff fails, so every run reaching that line has a merge base and its fallback cannot fire.

### Alternatives considered

- Fail only when a `REQUIRE_*` flag is set — rejected at intake: the issue's own test case expects exit 1 with no flag, and a strict gate that passes having inspected nothing is the defect in every mode.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Gate contract tests incl. the two orphan-HEAD cases | `bash tests/scripts/ci-strict-gate.test.sh` | 0 | prints `ci-strict-gate.test.sh: 49 passed` | SC-1 |
| No or-true fallback left on the DIFF line | `grep -n -e 'DIFF=.*true' scripts/ci-strict-gate.sh` | 1 | no matching line | SC-2 |
| Script parses | `bash -n scripts/ci-strict-gate.sh` | 0 | syntax check | SC-1 |

The full suite (`bash scripts/run-tests.sh`) was green at baseline before the change; it re-runs at branch finish.

### Task review findings

- Minor (task 1.1 review, quality) — `scripts/ci-strict-gate.sh:91-94`: the generic branch (merge base exists but `git diff` still fails) is untested, and it re-runs `git diff` to print git's stderr, so the shown text comes from a second run. The exit is 1 either way, so the gate still fails closed. Forwarded to final review.

### Advisory Findings

Correctness review over `920c289..f280c27` (six finders, four deduplicated candidates, each scored independently; threshold 75). None reached the threshold, so none entered the fix loop.

- Score 0 (pre-existing; reproduced) — `scripts/ci-strict-gate.sh:86`: the main diff omits `-c core.quotePath=false`, so a non-ASCII gated path such as `hooks/café.sh` is listed as `"hooks/caf\303\251.sh"`, misses the anchored tier regex, and the gate exits 0 with no proof. Probe: non-ASCII `hooks/` path exit 0; ASCII control exit 1. Lines 130 and 206 already pass the flag.
- Score 0 (pre-existing; reproduced) — `scripts/ci-strict-gate.sh:86`: default rename detection lists only the destination of a rename, so `git mv hooks/foo.sh lib/foo.sh` shows `lib/foo.sh` alone and the gate exits 0. Probe: move-out exit 0; plain delete control exit 1. Fix direction: `--no-renames`.
- Score 0 (unmodified lines) — `scripts/ci-strict-gate.sh:130,206`: the OQ_PLANS and SC_SLUGS diffs re-run `"$BASE"...HEAD` with `2>/dev/null ... || true`; a failure after the guarded main diff succeeded would empty them and skip those checks. Only a transient failure reaches it.
- Score 50 — `scripts/ci-strict-gate.sh:93`: the generic-failure branch re-runs `git diff` to print git's stderr instead of keeping the first run's, so a non-repeating failure prints a header with no cause. Exit stays 1. (Same as the task-review Minor.)

The two reproduced bypasses were moved to their own issue, #281 (user decision: keep this PR matched to #277).

Also checked and clean: a criss-cross history with two merge bases gives `git diff A...B` exit 0, so it does not newly fail.

### Intent Findings

Intent review (plan-blind) over `920c289..fa6162f`: no gap, drift, or excess. All six intent clauses are met. The extra `REQUIRE_SC_STABLE=1` case and the generic-failure branch trace to the issue text. SC-1 and SC-2 are each proven by a mapped Verify row.

### Not auto-verified

- The generic `git diff` failure branch (merge base present, diff fails) — traceability only (read in review); no fixture triggers it.
- macOS behaviour — the orphan case ran on Linux (git 2.43.0) only; CI's macos job covers it at PR time.

### Rollback

- `git revert <sha>`

### Harness-Delta

- backlog — the worktree-isolation guard refuses compound Bash commands it cannot parse (a zsh `${pipestatus}` pipe, a `python3` heredoc whose text contains "git", a `$(git ...)` inside an argument), forcing commands to be split. Friction, not a blocker.
