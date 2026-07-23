# fix-bookkeeping-trigger-loop — Summary

Lane: normal
Confidence: high
Reason: one-line trigger-list fix in `.github/workflows/post-merge-maintenance.yml`; 2 flags (existing behavior — changes when the automation fires; weak proof — nothing tests the trigger list). No mechanical hard gate: `.github/` is not in the high-blast path regex and is not a workflow-engine surface.
Flags: existing-behavior, weak-proof
Affects: post-merge bookkeeping automation (VERSION / CHANGELOG / trust-metrics / audit-log recording)
Input-type: maintenance
Route: normal — branch → direct edit → verify → PR. No PLAN (1 file, ≤3 steps per `rules/plan-format.md`).
Escalate: no

### Intent

> merge PR 160
>
> ok, update for loop branch

(In response to the report that PR #160 merged into `loop` but produced no bookkeeping PR,
because the workflow's `branches:` trigger list was `[main, v3]`.)

## What changed

- `.github/workflows/post-merge-maintenance.yml` — `branches: [main, v3]` → `[main, loop]`.
  `v3` no longer exists on the remote (`git ls-remote --heads github v3` → 0 refs); `loop` is the
  branch PRs actually merge into today (PR #158, #160).
- Extended the comment above the list with the failure mode itself (**this list rots silently** —
  a PR merged into a missing branch fires nothing, with no error) and the third instance in the
  history it already recorded.

### Rationale

The workflow is `pull_request_target` on `[closed]`, filtered by base branch. A base branch absent
from that list is not a failure — it is a **non-event**: no run, no log, no signal. The file's own
comment already documented two rounds of this rot (`[v2]` outliving v2, silently skipping PRs
#66/#68/#69/#70); `[main, v3]` outliving v3 is the third, and it silently skipped PR #160. Fixing
the value without recording the pattern would invite a fourth.

Per `docs/solutions/harness/automation-readiness.md` (critical), the two design questions for a
standing automation:

1. **Fail-safe / stop condition** — unchanged by this edit and already sound: the job opens a PR
   rather than pushing to a protected branch, guards against its own bookkeeping PRs
   (`!startsWith(head.ref, 'chore/bookkeeping-')`), and never checks out PR-head code. The defect
   being fixed is precisely the *silent* failure the doc warns about, so this edit moves the
   automation toward failing visibly (it now fires and can report) rather than not firing at all.
2. **Warranted / objectively verifiable** — the task recurs on every merge and its output is an
   auditable PR. No new automation is added here.

### Alternatives considered

- **Add `loop` and keep `v3`** — rejected: `v3` has no ref on the remote, so keeping it preserves
  the exact rot this change is about. Removing it is not adjacent cleanup; it is the same line's
  semantics (`v3` *was* the integration branch that `loop` replaced).
- **Build the ratchet now** (a CI check that fails when a recently-merged PR's base branch is
  absent from the trigger list) — deferred to the backlog, not skipped. It is a *new standing
  automation*, which `automation-readiness.md` says to consult on at design time rather than
  bolt onto an unrelated one-line fix; and the user's ask was scoped to making `loop` work.
  Recorded in `docs/harness-experimental/improvement-backlog.md`.
- **Backfill PR #160's missed bookkeeping in this PR** — kept separate: it is a data change to
  `VERSION` / `CHANGELOG.md` / the ledger, and mixing it with the trigger fix would double-count
  against `docs/solutions/harness/manual-version-bump-collides-with-event-sourced-bookkeeping.md`.
  Flagged to the human as a follow-up decision.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Workflow YAML parses; trigger list is `[main, loop]` | `python3 -c "import yaml;d=yaml.safe_load(open('.github/workflows/post-merge-maintenance.yml'));print(d[True]['pull_request_target']['branches'])"` | 0 | prints `['main', 'loop']` | |
| `v3` has no ref on the remote (justifies removal) | `git ls-remote --exit-code --heads github v3` | 2 | no such branch | |
| Harness suite unaffected | `bash scripts/lint-doc-truth.sh` | 0 | doc-truth green | |

Full suite: `bash scripts/run-tests.sh` ran ALL GREEN — re-run by the CI `tests` job; not a Verify
row per `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`.

### Rollback

- `git revert <sha>` — single-line config change, no state. To restore the previous behavior
  exactly, set `branches: [main, v3]` back (note: this re-introduces the silent-skip bug).

### Harness-Delta

- backlog — the trigger list has now rotted three times with no mechanical guard. Ratchet row
  added to `docs/harness-experimental/improvement-backlog.md`; candidate for `/compound` once the
  guard lands.
