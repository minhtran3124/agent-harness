# Durable Run State — Research Brief (canonical, GitHub issue #129)

Consolidates what already exists across Phases A (engine), B (portable deployment), and C
(core workflow checkpoints) of the Durable Run State Contract. Written at Phase D (Evidence
and rollout) so a future reader never has to re-derive this from three separate phase folders.

## What already exists

- **Engine** (`runtime/run_state.py`, Phase A → relocated by Phase B): stdlib-only Python CLI.
  Subcommands: `init`, `transition`, `status`, `list`, `rebuild`. Exit codes: 0
  (success/idempotent), 2 (invalid input/transition), 3 (storage error). A 16-state FSM —
  `queued → investigating → planning → implementing → verifying → ready_to_merge → shipped`
  (happy path), plus `fixing_ci` and `addressing_review` for the CI-failure/review-address loops —
  together the 11 `ACTIVE_STATES` (`queued`/`investigating`/`awaiting_confirmation`/`planning`/
  `implementing`/`verifying`/`awaiting_ci`/`fixing_ci`/`awaiting_review`/`addressing_review`/
  `ready_to_merge`) — plus `TERMINAL_STATES` (`shipped`/`cancelled`/`superseded`), `INTERRUPT_STATES`
  (`blocked`/`escalated`), and the `WAITING_STATES` subset of active states (`awaiting_confirmation`/
  `awaiting_ci`/`awaiting_review`). Storage: `specs/<slug>/events.jsonl` (append-only) +
  `specs/<slug>/RUN.json` (current projection, atomically rewritten). `fcntl.flock` locking
  for concurrent-writer safety; idempotent event replay via `--event-id`.
- **Portable deployment** (Phase B, PR #166): the engine lives at `runtime/` (not `scripts/`),
  registered in `scripts/deploy-harness.sh`'s `SYNCED_DIRS_RE` and
  `scripts/install-harness.sh`'s `PAYLOAD` array — every consuming repo gets it on
  install/resync, landing at `.claude/runtime/run_state.py`.
- **Workflow checkpoints** (Phase C, PR #167, open against the epic branch): 8 checkpoints
  across 6 files call the engine — `skills/feature-intake/SKILL.md` (init + investigating +
  lane-scoped planning), `skills/subagent-driven-development/SKILL.md` (implementing +
  verifying), `skills/finishing-a-development-branch/SKILL.md` (ready_to_merge),
  `hooks/session-knowledge.sh` (SessionStart active-run summary),
  `scripts/harness-status.sh` (on-demand Active Runs section, meta-repo-only),
  `.github/workflows/post-merge-maintenance.yml` (shipped-on-merge, meta-repo-only). Every
  checkpoint call is unconditionally non-fatal (`|| true`). Only normal/high-risk lanes get the
  full chain; `tiny`-lane runs intentionally stop at `investigating`.
- **Pre-existing, adjacent mechanism**: `specs/STATE.md` + `hooks/state-breadcrumb.sh`
  (SessionEnd) — tracks one session's current focus, not a per-spec durable FSM. Phase D
  (Task 1.1) documents the boundary between the two; they do not read or write each other's
  files.

## Known limitations

- A `tiny`-lane or abandoned run never reaches a terminal state, so `list --active`'s consumers
  (`session-knowledge.sh`, `harness-status.sh`) will accumulate stale entries over time
  (bounded to 5 displayed, unbounded underlying). This is by design — a `tiny` run intentionally
  stops at `investigating` — not a terminalization defect.

## Close-out (gh-196, GitHub issue #196) — current contract

The following were resolved after Phase D; the pre-#177 limitations above are fixed, not deferred:

- **Semantic event-chain validation (#174).** `read_events` now runs `validate_chain` by default,
  so every read surface that trusts history — `status`, `list`, `rebuild`, `rebuild --check`, and
  the resume decision — fails visibly with the storage-error contract (exit 3) on a JSON-valid but
  semantically impossible log (bad `seq`, broken `from_state` chaining, mixed run identity, an
  illegal transition, or a `shipped` event without a valid `sha`) instead of projecting a fabricated
  history — and does so without mutating either artifact. Escape hatches:
  `rebuild --allow-invalid-chain`, and closing a bricked run to `cancelled`/`superseded`.
- **Reliable terminalization.** The staging no-op (#177) is fixed — the bookkeeping PR stages both
  `RUN.json` and `events.jsonl`. The trigger is now **base-branch-agnostic**: `post-merge-maintenance.yml`
  carries no static `branches:` base-branch allowlist, so a merged PR carrying a tracked run
  (`specs/<slug>/SUMMARY.md` + `RUN.json`) transitions to `shipped` exactly once with the confirmed
  merge SHA regardless of which integration branch it targeted. The checkpoint can no longer silently
  disappear when the integration branch is renamed. Caveat: `pull_request_target` loads its definition
  from the repo default branch (`main`), so the trigger change is inert until synced there.
- **Stale runs reconciled.** The two runs left at `ready_to_merge` (`new-session-plan-resume`,
  `gate-verifiability-principle`) were terminalized to `shipped` from confirmed GitHub merge SHAs
  (PRs #173 and #189) via the real CLI — one appended event each, chains still validate.

## What Phase D adds

- This brief, `design.md`, and a canonical `PLAN.md` under `specs/durable-run-state/` — a
  single consolidated account of the whole feature, cross-referencing each phase's own
  `specs/gh-129-durable-run-state-phase-{a,b,c}/` folder rather than duplicating their content.
- A documented ownership boundary with `specs/STATE.md` (Task 1.1).
- A regression sweep confirming Phase A/B's evidence still holds cumulatively (Task 3.1).
- Confirmation that the whole contract passes the existing macOS+Ubuntu CI matrix (SC-9).

## Sources

- `specs/gh-129-durable-run-state-phase-a/SUMMARY.md`, `PLAN.md` — engine (all Verify rows,
  Advisory/Intent Findings).
- `specs/gh-129-durable-run-state-phase-b/SUMMARY.md`, `PLAN.md`, `design.md` — portable
  deployment.
- `specs/gh-129-durable-run-state-phase-c/SUMMARY.md`, `PLAN.md`, `design.md` (on branch
  `feat/gh-129-durable-run-state-phase-c`, PR #167 — not present in this checkout since it is
  unmerged; cited from the PR/branch, not re-read line-by-line here since the branch this task
  runs from does not have it checked out).
- `runtime/run_state.py` (current, this checkout).
