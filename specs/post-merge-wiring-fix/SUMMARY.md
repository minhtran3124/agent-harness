# post-merge-wiring-fix — Summary

Lane: normal
Confidence: high
Reason: One-line trigger change + comment rewrite in a CI workflow. Behavior-affecting (revives a dead pipeline) but touches no strict-gate path; ground truth verified before the change (main has the full toolchain the old comment claimed absent).
Flags: none
Affects: .github/workflows/post-merge-maintenance.yml (event-sourced bookkeeping pipeline)
Input-type: harness improvement

### Intent

"merge PR #70 và tiếp tục C3" — per docs/reviews/over-engineering-review-2026-07-16.md §2 C3: post-merge-maintenance.yml fires only on `branches: [v2]` but PRs now merge to `main`; bookkeeping.sh + audit-trend JSONL are inert. Fix: one line (`branches: [main]`) — or retire the pipeline.

## What changed

`pull_request_target` trigger switched from `branches: [v2]` to `branches: [main]`, and the stale doctrine comment (claiming main "intentionally lacks scripts/bookkeeping.sh") rewritten as history + the actual rule ("keep this list to the branch(es) PRs are actually merged into"), citing the 4 silently skipped merges.

### Rationale

Chose "fix wiring" over "retire": the pipeline's consumers are real (trust-metrics ledger has 32+ substantive rows, harness-status/bookkeeping read it), the failure was pure wiring — the v2 → main promotion moved the merge target without updating the trigger. Ground truth checked before editing (the unverified-premise lesson): main HAS scripts/bookkeeping.sh, trust-metrics.md, audit-log.jsonl, VERSION 2.0.0; PRs #66/#68/#69/#70 merged to main while the last v2 merge was #65. A temp-copy smoke run of bookkeeping.sh from a main checkout succeeded (VERSION 2.0.0→2.1.0, ledger + CHANGELOG + trend line written).

### Alternatives considered

- Retire the pipeline (review's alternative): rejected for now — the ledger is the best-maintained record surface in the repo; killing automation because its trigger rotted punishes the wrong component. Revisit under issue #67 Phase 2 if the bookkeeping PRs prove noisy.
- Backfill the 4 missed PRs: deferred — the wired workflow only covers future merges; a manual `bookkeeping.sh` run per missed PR can restore continuity if wanted (offered to the user, not done unilaterally: 4 VERSION bumps is an opinionated rewrite of history).

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| trigger now targets main | `grep -q "branches: \[main\]" .github/workflows/post-merge-maintenance.yml` | 0 | the fix |
| stale v2 trigger gone | `grep -q "branches: \[v2\]" .github/workflows/post-merge-maintenance.yml` | 1 | no match |
| stale absence claim gone | `grep -q "intentionally lacks" .github/workflows/post-merge-maintenance.yml` | 1 | comment rewritten |
| toolchain exists on main (old comment's premise is false) | `test -f scripts/bookkeeping.sh -a -f docs/harness-experimental/trust-metrics.md -a -f docs/harness-experimental/audit-log.jsonl` | 0 | ground truth |
| loop guard intact | `grep -q "chore/bookkeeping-" .github/workflows/post-merge-maintenance.yml` | 0 | no bookkeeping-PR loops |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

Session-only evidence: temp-copy smoke run of `bookkeeping.sh --pr 70 ...` from a main
checkout exited 0 and wrote VERSION 2.1.0 + ledger/CHANGELOG/trend deltas (not in the
table because re-running it in CI would mutate the checkout).

### Rollback

- `git revert <commit>` — restores the [v2] trigger (returns the pipeline to inert; nothing else depends on the change).

### Harness-Delta

- Found during the edit: `specs/correctness-review-angles/PLAN.md` is stuck `status: active` (its work shipped long ago), making blast-radius-check warn on every unrelated edit — stale-active plans are a recurring hazard; candidate for a finishing-skill check or /compound entry.
