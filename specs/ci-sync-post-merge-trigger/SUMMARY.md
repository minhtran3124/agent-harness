# ci-sync-post-merge-trigger — Summary

Lane: normal
Confidence: high
Reason: Changes when a standing automation fires, on the branch whose copy is authoritative — 2 of 10 flags (existing behavior, weak proof); no hard gate (`.github/workflows/` is not a `high-blast` path, and the change is a verbatim sync of an already-reviewed file).
Flags: existing behavior, weak proof
Affects: post-merge bookkeeping automation (VERSION / CHANGELOG / trust-metrics / run-state `shipped`)
Input-type: maintenance

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`.

### Intent

Merging PR #173 into `loop` fired **no** bookkeeping run — no VERSION bump, no CHANGELOG entry, no
trust-metrics row, and no run-state `shipped` transition. Diagnosis: `pull_request_target` always loads
the workflow definition from the repo's **default branch**, and `main`'s copy still reads
`branches: [main, v3]` — `v3` no longer exists on the remote. The corrected list (`[main, loop]`) was
committed only on `loop`, where the trigger never reads it. Fourth instance of this rot: `v2` → `v3` →
`loop` → and now "fixed on the wrong branch".

## What changed

`.github/workflows/post-merge-maintenance.yml` on `main` replaced with `loop`'s copy, verbatim. Two
deltas come with it:

1. `branches: [main, v3]` → `[main, loop]`, plus the comment block that states the rule this bug keeps
   violating — *this file must be synced on `main`; editing the list only on an integration branch has
   no effect* — and the full rot history.
2. The `Run-state checkpoint — mark shipped` step (issue #129 Phase C), which `main` never received.

### Rationale

Syncing the whole file rather than one line is the minimal *coherent* unit: `main` owns the definition
that actually runs, so any part of it missing there is dead. Safe despite `main` being 161 commits
behind, because the workflow checks out `ref: github.event.pull_request.base.ref` — the definition comes
from the default branch, the **code** comes from the PR's base branch. Verified: `scripts/bookkeeping.sh`
is byte-identical on both branches, and `runtime/run_state.py` (absent on `main`) will be present in the
checkout of `loop`, so the new step resolves.

### Alternatives considered

- **One-line trigger edit only.** Rejected: leaves `main` without the run-state `shipped` step, so every
  future merge would still leave its run non-terminal and permanently listed by `list --active`.
- **Promote `loop` → `main` (161 commits).** The real reconciliation and the root cause — while that gap
  exists, every `pull_request_target` workflow runs from stale definitions. Out of scope here: it is a
  release decision, not a bug fix. Tracked separately.
- **Backfill PR #173's missed bookkeeping by hand.** Rejected per
  `docs/solutions/harness/manual-version-bump-collides-with-event-sourced-bookkeeping.md`: a manual bump
  makes `bookkeeping.sh` bump *again* from that value later, skipping a version and orphaning the
  `## [Unreleased]` bullet. #173's bookkeeping is a deliberate, recorded loss.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| behavior | `grep -q 'branches: \[main, loop\]' .github/workflows/post-merge-maintenance.yml` | 0 | the trigger the default branch will actually read | |
| behavior | `grep -q 'Run-state checkpoint' .github/workflows/post-merge-maintenance.yml` | 0 | the Phase-C step main was missing | |
| lint | `python3 -c "import yaml;yaml.safe_load(open('.github/workflows/post-merge-maintenance.yml'))"` | 0 | valid YAML | |
| behavior | `git diff --quiet github/loop -- .github/workflows/post-merge-maintenance.yml` | 0 | byte-identical to loop's reviewed copy — the sync is exact, not a re-authoring | |

### Rollback

- `git revert <sha>` — single-file, no schema or data change. Reverting restores `[main, v3]`, which
  simply resumes firing nothing for `loop` merges.

### Harness-Delta

- backlog — the ratchet row already queued on 2026-07-23 (assert every recently-merged PR's base appears
  in the **default-branch** copy of this trigger list) is now proven necessary by a fourth occurrence,
  and this instance shows the subtlety: the previous fix *was* written with the default-branch rule in
  its comment and still landed only on the integration branch. The check must read `main`'s copy, not the
  working tree's.
