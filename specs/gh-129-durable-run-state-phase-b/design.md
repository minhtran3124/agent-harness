# Phase B — Portable Deployment (design)

Spec for `specs/gh-129-durable-run-state-phase-b/`. Phase B of GitHub issue #129 (Durable Run
State Contract). Builds on the merged Phase A engine (PR #164, on the epic branch
`feat/gh-129-durable-run-state`).

## 1. Problem

Phase A shipped the durable run-state engine at `scripts/run_state.py` +
`scripts/test_run_state.py` — deliberately deferring the issue's stated design ("source lives
under `runtime/` and is deployed to `.claude/runtime/`") to this phase. Right now the engine
only exists in *this* repo; it has no path to reach a consuming project's `.claude/` tree the
way `skills/`, `agents/`, `hooks/`, `rules/`, and `templates/` already do via
`scripts/deploy-harness.sh`.

## 2. Scope (from issue #129, "Phase B — Portable deployment")

- Sync `runtime/` into `.claude/runtime/`.
- Extend installer/resync manifests and orphan pruning.
- Add install and resync regression coverage.
- ~~Register runtime contract paths in the harness manifest~~ — **deferred to Phase C**, see §4.2.

**Out of scope:** Phase C (wiring `run_state.py` into `feature-intake` / `SessionStart` /
`finishing-a-development-branch` / `harness-status` — including the `harness-manifest.json`
`contracts` registration, deferred here because it needs a real consumer to be valid), Phase D
(docs rollout, cross-OS CI validation of the full multi-phase contract).

## 3. What already exists (research finding — this narrows the phase significantly)

Investigated `scripts/deploy-harness.sh` (430 lines) before designing anything:

- **Orphan pruning already exists and is generic.** `docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md`
  documents a bug that was **already fixed** (`confirmed_at: 2026-07-17`), not a live gap. The
  fix — a per-deploy manifest (`$OUT/.harness-deployed`, written by `record_deployed()`) diffed
  against the previous deploy's manifest, shape-guarded by `SYNCED_DIRS_RE` — already covers
  *any* directory that flows through the `for d in skills agents hooks rules templates; do`
  loop (`deploy-harness.sh:383`) and its `copy_dir()` calls. Adding `runtime` to that loop is
  the entire "extend orphan pruning" lift; no new pruning logic is needed.
- **`SYNCED_DIRS_RE`** (`deploy-harness.sh:106`) is used in two places (`grep -qE`, not `find`):
  the dry-run prune-report loop (line 146) and `prune_orphans()`'s defense-in-depth filter
  (line 399). The actual sync set is the hardcoded loop at line 383, plus a summary-counters
  block (lines 411-420) that has no `runtime` line yet. **Three edits**, not one.
- **`BOOTSTRAP_OWNED_FILES`** (protected-file conflict guard, `deploy-harness.sh:29-34`) is a
  hardcoded 4-file list, not a generic per-dir mechanism (confirmed against
  `docs/solutions/harness/resync-protected-files-decisions.md` Decision 3 — deliberately a
  targeted list, not a checksum manifest). `runtime/` needs **no** entries here: both
  `runtime/run_state.py` and `runtime/test_run_state.py` are fully harness-owned (like
  `skills/`/`hooks/` content), never hand-customized per consuming repo.
- **`install-harness.sh`** delegates the actual `.claude/` build to `deploy-harness.sh` (line
  220) but keeps its own separate `PAYLOAD` array (line 33) for legacy-file detection and
  `--keep-sources` staging — needs a parallel `runtime` addition, independent of
  `deploy-harness.sh`'s changes.
- **`harness-manifest.json`**'s `contracts` section (lines 69-76) is the existing precedent for
  "a named surface + its consumers" — `scripts/check_manifest.py` already validates every
  `contracts[*].surface`/`.consumers` path exists on disk (its Check C, lines 98-123). No new
  checker category needed for a 2-file directory (YAGNI — revisit only if `runtime/` grows).
- **`scripts/run-tests.sh`'s wiring gap** (discovered during this brainstorm, unrelated to the
  design fork but directly relevant to the move): its L2 pytest step uses a **hardcoded explicit
  file list** (`PYTESTS=...`, not a glob) that never had `scripts/test_run_state.py` added —
  verified directly (`185 passed` with or without Phase A's 29 tests in the aggregate run).
  Folded into this phase's scope since the file is moving anyway.

## 4. Design decisions

1. **Move, don't duplicate.** `scripts/run_state.py` + `scripts/test_run_state.py` relocate to
   `runtime/run_state.py` + `runtime/test_run_state.py`. Confirmed safe: both files use only
   `__file__`-relative paths internally (`test_run_state.py:8` `sys.path.insert(0,
   os.path.dirname(__file__))`; `:502` `os.path.abspath(__file__).replace(...)`), no hardcoded
   `"scripts/"` string anywhere. Nothing in the repo calls `scripts/run_state.py` yet (Phase C,
   which would, hasn't started) — zero breakage from the rename.
2. **Manifest registration deferred to Phase C — not added in this phase.**
   `scripts/check_manifest.py`'s Check C (lines 98-123) explicitly rejects a `contracts` entry
   with an empty `consumers` list (`elif not consumers: problem(...)`) — a registered contract
   with nobody consuming it is treated as a manifest problem, not a valid "not yet used" state.
   Since nothing in this repo calls `runtime/run_state.py` until Phase C wires an actual caller
   (a skill/hook), there is no real consumer to list yet, and no defensible way to add the
   entry without either weakening that check (out of scope — `check_manifest.py` is governance
   tooling, not something Phase B should touch) or listing a stretch/placeholder consumer.
   Decision (confirmed with the user, 2026-07-24): defer the `harness-manifest.json`
   registration to Phase C, when it can be added correctly with a real `consumers` entry.
3. **New dedicated test file, not a rewrite.** `tests/scripts/runtime-sync.test.sh`, mirroring
   `deploy-prune.test.sh`'s 6-case shape (first-deploy sync, orphan-prune, consumer-addition
   survival, sidecars/backups survive, idempotent re-sync, dry-run) but scoped to `runtime/`.
   Chosen over parametrizing
   the existing file because `deploy-prune.test.sh`'s current cases are skills-specific by
   name/fixture — safer to add a parallel file than modify a working, already-reviewed test.

## 5. Non-goals

- No new pruning *logic* — the existing mechanism is reused, only its dir set grows.
- No protected-file / `BOOTSTRAP_OWNED_FILES` entries for `runtime/` (fully harness-owned).
- No new `harness-manifest.json` checker category (disk-inventory parity) — YAGNI at 2 files.
- No Phase C wiring (nothing consumes `run_state.py` from a skill/hook yet).
- No cross-OS CI validation beyond what `scripts/run-tests.sh` already runs on macOS/Ubuntu.

## 6. Testing

- `tests/scripts/runtime-sync.test.sh` (new) — 6 cases per §4.3.
- `runtime/test_run_state.py`'s existing 29 tests, unchanged content, now reachable via
  `scripts/run-tests.sh`'s `PYTESTS` (fixing the wiring gap as part of the move).
- No new `harness-manifest.json` `contracts` entry this phase (deferred to Phase C, see §4.2) —
  `scripts/check_manifest.py` needs no change and should stay green without modification.
- Full `bash scripts/run-tests.sh` must stay ALL GREEN before this phase ships.
