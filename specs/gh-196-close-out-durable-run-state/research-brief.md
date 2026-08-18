# gh-196-close-out-durable-run-state — Research Brief

Depth: **Deep** (intake lane `high-risk`). No later upgrade.

## Source Pack

- none (local-only; no external surface — no new dependency, no external integration, no
  version-specific API. Changes are local Python + one GitHub Actions workflow already in-repo.)

## Terrain map (ground-truthed on `simplify`, 2026-08-08)

### Branch topology
- `simplify` is the active integration branch (current checkout; 270 commits ahead of stale `main`,
  the GitHub default branch).
- `feat/gh-174-run-state-chain-validation` branched from an **older** `simplify` (merge-base
  `924af14`) and carries 14 commits of chain-validation work not yet on `simplify`.
- For `runtime/run_state.py`, `simplify` == merge-base (`git diff 924af14 simplify -- runtime/run_state.py`
  is empty), so the feat/gh-174 runtime hunks apply cleanly onto current `simplify`.

### Part 1 — chain validation (mostly done on feat/gh-174)
- **Current `simplify`**: `read_events(slug)` (run_state.py ~L107–131) only checks file-exists,
  JSON parse, required keys, non-empty. **No `validate_chain`.** `cmd_status` reads only `RUN.json`
  (never the log); `cmd_list` reads only per-slug `RUN.json`. Storage errors → `StorageError` →
  `main` exit **3**; input/transition → exit **2**; `rebuild --check` drift → exit 3.
- **feat/gh-174 adds** pure `validate_chain(events, slug, path)` raising `StorageError` on the first
  of **8 invariants**: (1) `seq` strict-int contiguous from 1; (2) `from_state == prev.to_state`;
  (3) constant `slug`+`run_id`, chain `slug` == requested; (4) genesis `from_state None`/`to_state
  "queued"`; (5) each hop legal via `validate_transition`; (6) unique `event_id`; (7) `event` is
  str; (8) `shipped` requires `sha` matching `SHA_RE`. Wired as `read_events(slug, validate=True)`;
  `cmd_status` gains a shared-lock read + raises on invalid chain / projection drift. Escape hatches:
  `rebuild --allow-invalid-chain`; `cmd_transition` routes `--to ∈ {cancelled,superseded}` through
  `_close_run_over_invalid_chain` (idempotent, sentinel in metadata) so a bricked run stays closeable.
- **Tests added**: `runtime/test_chain_guards_are_load_bearing.py` (mutation gate — each guard proven
  load-bearing), ~+990 lines in `runtime/test_run_state.py`, `tests/scripts/run-state-chain-validation.test.sh`.
- **Cherry-pick feasibility**: runtime engine + the two new test/script files apply cleanly.
  **Will conflict / hand-reapply**: `skills/subagent-driven-development/SKILL.md` (simplify rewrote
  it; feat edits target deleted prose), `runtime/test_run_state.py` (simplify renamed 4 `test_*`→
  `legacy_*`), `scripts/run-tests.sh` (simplify rewrote PYTESTS; re-add the one line registering
  `test_chain_guards_are_load_bearing.py`).
- **Grandfathering**: both tracked logs (`new-session-plan-resume`, `gate-verifiability-principle`)
  have seq 1–6 contiguous, genesis `null→queued`, chained `from_state`, single identity, unique
  `event_id`, legal hops. **Both PASS** the new validator — landing it grandfathers them, breaks
  neither. (Acceptance criterion 1 satisfied by pass, not by repair.)

### Part 2 — terminalization gap (evidence-backed)
- `.github/workflows/post-merge-maintenance.yml` trigger: `pull_request_target: types:[closed]`,
  **base-branch filter line 28: `branches: [main, loop]`**. Job writes `shipped` via
  `run_state.py transition --to shipped --sha $MERGE_SHA` (L73–74), stages `RUN.json`+`events.jsonl`
  into the bookkeeping PR (L116–118). Missing SUMMARY/RUN.json → non-fatal skip (L69–72).
- **`pull_request_target` reads its definition + branch filter from the repo DEFAULT branch (`main`)**
  — documented in the file (L14–18) and by GitHub. A filter edit only on an integration branch has
  no effect. `main`'s copy currently has `[main, loop]` and the run-state step.
- **Failure mode confirmed**: the workflow has **not fired since 2026-07-27**. Integration moved to
  `simplify` (absent from `[main, loop]`), so every `simplify`-targeted merge triggered **no run**.
- Branch policy is duplicated nowhere authoritative; only line 28 is functional. Prior specs
  (`post-merge-bookkeeping`, `post-merge-wiring-fix`, `fix-bookkeeping-trigger-loop`,
  `fix-post-merge-runstate-staging`) evolved the list and added the staging step but **none added
  `simplify` and none made the policy base-branch-agnostic.**
- Regression test `tests/scripts/post-merge-runstate-staging.test.sh` asserts the staging contract
  only (write set = RUN.json+events.jsonl, step ordering, publish-on-success). **Gap: nothing
  asserts the trigger/base-branch policy** (the issue calls a text-only branch-list assertion
  insufficient).

### Stale-run landed SHAs (confirmed via `gh pr view`, for reconciliation)
- `new-session-plan-resume`: RUN.json `sha=null`, state `ready_to_merge`. Landed via **PR #173**,
  base `loop`, merge SHA **`206605218508d5b3ee1d1769e785c4057dc6345a`**. Stale because it merged
  *before* the run-state staging step existed (historical, not a filter miss).
- `gate-verifiability-principle`: RUN.json `sha=ecdcb49…` (run head), state `ready_to_merge`.
  Landed via **PR #189**, base `simplify`, merge SHA **`c9b3b7ef3f36f846a5df3e0194b819b85656ebd4`**.
  Stale because base `simplify` was excluded from the filter — the demonstrated gap.

## Risks
- Changing a `pull_request_target` workflow is high-blast; the fix only takes effect once merged to
  `main`. The regression test + docs must state this explicitly so it does not silently rot again.
- Reconciliation must use the **merge SHA** (not the run head commit) and must not fabricate events —
  append exactly one `shipped` event per run via the real CLI so the chain stays valid.
