# gh-129-durable-run-state-phase-b — Summary

Lane: high-risk
Confidence: high
Reason: 3 risk flags fire — public contracts (`scripts/deploy-harness.sh`'s `SYNCED_DIRS_RE` governs what every consuming repo receives; extending it to `runtime/` changes that distribution contract), existing behavior (modifying tested `deploy-harness.sh`/`install-harness.sh`), weak proof (the issue itself calls for new install/resync regression coverage for this path, implying current coverage doesn't reach it). No literal detectable hard gate from `harness-manifest.json` fires (not auth/authorization/data-loss-migration/audit/external-provider/public-contract-keyword/high-blast-path/workflow-engine), but orphan pruning is a destructive file operation and this repo has two prior recorded incidents in this exact area (`docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md`, `docs/solutions/harness/resync-protected-files-decisions.md`) — classifying high-risk by judgment given the distribution blast radius, not a mechanical hard-gate hit.
Flags: public-contracts, existing-behavior, weak-proof
Affects: scripts/deploy-harness.sh, scripts/install-harness.sh, harness-manifest.json (the deploy/resync distribution contract)
Input-type: spec slice

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<paste the original request, verbatim>
"newbranch for phase b, and start /feature-intake"

Context established earlier in the same conversation: the user is working through GitHub issue
#129 ("Durable Run State Contract") phase by phase. Phase A (the engine + CLI) is complete,
reviewed, and merged via PR #164 into the epic/integration branch `feat/gh-129-durable-run-state`
(itself branched from `loop`, not `main` — the plan is to land Phase A/B/C/D there and test them
together before one final merge decision into `loop`). This request starts Phase B.

Phase B scope (from issue #129, "Phase B — Portable deployment"):
- Sync `runtime/` into `.claude/runtime/`.
- Extend installer/resync manifests and orphan pruning.
- Add install and resync regression coverage.
- Register runtime contract paths in the harness manifest.

Explicitly out of scope for this phase (deferred per the issue): Phase C (wiring into
feature-intake / finishing-a-development-branch / SessionStart / harness-status), Phase D
(design.md/PLAN.md documentation rollout, cross-OS CI validation of the full contract).

## What changed

Relocated the Phase A engine from `scripts/run_state.py`/`scripts/test_run_state.py` to
`runtime/run_state.py`/`runtime/test_run_state.py` (pure `git mv`, zero content change), and
registered `runtime/` into the existing generic deploy/install/test surfaces:
`scripts/deploy-harness.sh` (`SYNCED_DIRS_RE` + the sync loop — no new pruning logic needed, the
existing mechanism is already dir-agnostic), `scripts/install-harness.sh` (`PAYLOAD` array), and
`scripts/run-tests.sh` (`PYTESTS` list — this also closed a real wiring gap: Phase A's 29 tests
were never actually included in the repo's aggregate test run, only when targeted directly).
Added `tests/scripts/runtime-sync.test.sh` (6 cases, mirroring `deploy-prune.test.sh`) proving
`runtime/` sync + orphan-prune + consumer-addition-survival behavior. `harness-manifest.json`
`contracts` registration is explicitly deferred to Phase C (see Rationale).

### Rationale

`scripts/check_manifest.py`'s Check C rejects a `contracts` entry with an empty `consumers`
list — since nothing in this repo calls `runtime/run_state.py` until Phase C wires an actual
caller, there was no defensible way to register the manifest entry now without either weakening
that check (out of scope for this phase) or listing a stretch/placeholder consumer. Confirmed
with the user during `/brainstorming`: defer to Phase C. Everything else in the issue's Phase B
scope reuses the harness's existing, already-tested sync/prune mechanism rather than building
anything new — research (`research-brief.md`) confirmed the "orphan pruning" gap the issue
references was already fixed before this phase started.

### Alternatives considered

- Building a `runtime/`-specific parallel sync mechanism instead of registering into the
  existing one — rejected: would duplicate `copy_dir`/`prune_orphans` for no benefit and break
  the "one generic mechanism, N registered dirs" pattern already used for 5 other dirs.
- Registering the `harness-manifest.json` contract now with a placeholder/stretch consumer —
  rejected in favor of deferring to Phase C (see Rationale); a stretch consumer would satisfy
  the mechanical check without being true.

### Deviations

- Rule 2 — Fixed a stale "5 synced dirs" comment (now 6) directly adjacent to the Task 1.2 edit
  it was made stale by; flagged by code-quality review. `scripts/deploy-harness.sh`. Commit
  `a13ddf8`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| unit | `python3 -m pytest runtime/test_run_state.py -q` | 0 | 29 tests pass at the new location | SC-1 |
| unit | `bash -c "! test -e scripts/run_state.py && ! test -e scripts/test_run_state.py"` | 0 | old paths genuinely gone | SC-2 |
| integration | `bash -c 'T=$(mktemp -d); bash scripts/deploy-harness.sh --target "$T" >/dev/null 2>&1; [ -f "$T/.claude/runtime/run_state.py" ]; rc=$?; rm -rf "$T"; exit $rc'` | 0 | fresh deploy places runtime/ under .claude/ | SC-3 |
| unit | `grep -q "templates runtime settings.json" scripts/install-harness.sh` | 0 | PAYLOAD includes runtime | SC-4 |
| unit | `grep -q "runtime/test_run_state.py" scripts/run-tests.sh` | 0 | wiring gap closed | SC-5 |
| integration | `bash tests/scripts/runtime-sync.test.sh` | 0 | 6/6 cases pass; mutation-tested by code-quality review (4/6 cases correctly fail when runtime/ registration is removed) | SC-6 |
| repo | `bash scripts/run-tests.sh` | 0 | ALL GREEN — 214 python tests (185 + 29, wiring gap closed) + all shell suites |  |

### Rollback

- `git revert 8981203..HEAD` (or revert the individual task commits: `8981203` move,
  `caf67be` deploy-harness.sh, `bfc7979` install-harness.sh, `d9ae778` run-tests.sh, `a13ddf8`
  comment fix, `3c162e0` new test file) — all reversible; no data migration, no destructive
  operation, no external state change.

### Harness-Delta

- none
