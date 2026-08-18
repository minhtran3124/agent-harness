# fix-post-merge-runstate-staging — Summary

Lane: normal
Confidence: high
Reason: Fixes an existing standing automation so it stops discarding its own output — 2 of 10 flags (existing behavior, weak proof: the workflow had zero test coverage). No hard gate: `.github/workflows/` is not a `high-blast` path, and `automation-readiness.md`'s consult gate is about *adding* automation, not repairing one.
Flags: existing behavior, weak proof
Affects: post-merge bookkeeping automation — the run-state `shipped` transition (GitHub issue #129 Phase C)
Input-type: maintenance

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`.

### Intent

External review (Codex, **P1** on PR #176) found that the `Run-state checkpoint — mark shipped` step
mutates `specs/<slug>/RUN.json` and appends to `specs/<slug>/events.jsonl`, but the bookkeeping PR stages
only four files and `git commit` carries no `-a`. The transition is therefore **discarded with the
runner** while the step reports success — so every applicable run stays non-terminal forever and is
permanently advertised by `run_state.py list --active`.

Verified before accepting, and the defect has a second half the review also named: `changed` — which
decides whether the PR opens at all — was computed **before** the transition ran, so a run-state-only
change read as "nothing to record". The Phase-C step has therefore never been capable of working, on any
branch.

## What changed

`.github/workflows/post-merge-maintenance.yml`:

1. The run-state step now runs **before** the bookkeeping dirty-tree check, so `changed` accounts for its
   writes and a run-state-only change still opens the PR.
2. It gained `id: runstate` and publishes `slug` to `$GITHUB_OUTPUT` **only when the transition
   succeeded** (the transition is now the `elif` condition rather than a `|| echo` tail).
3. The PR step stages `specs/$RUNSTATE_SLUG/{RUN.json,events.jsonl}` when that slug is set, and says so
   in the generated PR body.

`tests/scripts/post-merge-runstate-staging.test.sh` (new, auto-discovered by `run-tests.sh`): rather than
grepping for wording, it **measures** which files a real `shipped` transition writes — by running the
engine in a temp specs root and diffing checksums — then asserts the workflow stages every measured file.
Adding a third artifact to the engine now fails here instead of vanishing in CI. It also pins the
ordering and the success-gated output.

### Rationale

Option A of the fork raised with the user: make the existing design work rather than removing the
`shipped` step. Consequence accepted deliberately — `shipped` reaches the repo only when the bookkeeping
PR merges, one beat later than the merge it records. The alternative (dropping the step) would leave
issue #129 Phase C half-built.

### Alternatives considered

- **Drop the `shipped` transition from this workflow** (fork option B). Rejected by the user: Phase C's
  purpose is a durable terminal state, and nothing else writes it.
- **`git commit -a`.** Rejected: it would sweep in anything else the runner happened to dirty. Explicit
  staging of a known slug keeps the bookkeeping commit auditable.
- **Grep-based test** asserting the `git add` line mentions both filenames. Rejected as the weak form —
  it cannot notice the engine gaining a third artifact. Measuring the write set does.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| behavior | `bash tests/scripts/post-merge-runstate-staging.test.sh` | 0 | 6 passed — write set measured, both files staged, ordering + success-gate pinned | |
| behavior | `python3 -c "import yaml;yaml.safe_load(open('.github/workflows/post-merge-maintenance.yml'))"` | 0 | valid YAML | |
| mutation | `bash -c 'grep -c "RUNSTATE_SLUG/RUN.json" .github/workflows/post-merge-maintenance.yml'` | 0 | staging line present (removing it fails the test above — mutation-checked) | |

### Rollback

- `git revert <sha>` — single workflow file plus a new test; no schema, no data change.

### Harness-Delta

- backlog — this workflow had **zero** test coverage before today, despite owning VERSION, CHANGELOG, the
  trust-metrics ledger and the run-state terminal transition. Worth auditing whether any other
  `.github/workflows/*` step mutates files it never stages.
