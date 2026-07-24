# gh-129-durable-run-state-phase-a — Summary

Lane: normal
Confidence: high
Reason: 0 of 10 risk flags fired and no hard gate is tripped — scope is confined to new files under scripts/ + tests/ (a new stdlib-only CLI), with no touch to skills/, hooks/, rules/, or settings.json (those are explicitly out of scope, deferred to Phase B/C). Lane is `normal` rather than `tiny` because the change spans multiple files and introduces a new public callable (the run_state.py CLI surface), per the tiny-lane file-count/no-new-public-callable qualifier in feature-intake Step 3.
Flags: none
Affects: none (net-new module, no existing contract modified)
Input-type: new initiative

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<paste the original request, verbatim>
"bắt đầu Phase A trước" (start Phase A first)

Context established earlier in the same conversation, from the user's review request against
GitHub issue https://github.com/minhtran3124/agent-harness/issues/129 ("Durable Run State
Contract"): the user asked to review the issue against the current codebase, evaluate
feasibility, then asked for the practical benefits, then asked to begin Phase A.

Phase A scope (from issue #129, "Phase A — Contract and engine"):
- Add machine-readable event and projection schemas.
- Implement the stdlib-only transition engine and CLI.
- Add atomic writes, lock handling, event sequencing, idempotency, and projection rebuild.
- Add unit tests for valid/invalid transitions, corruption, replay, concurrency, SHA
  validation, waiting metadata, and terminal states.

Explicitly out of scope for this phase (deferred to later phases per the issue): Phase B
(`runtime/` → `.claude/runtime/` portable deployment, installer/resync manifest changes),
Phase C (wiring into feature-intake / finishing-a-development-branch / SessionStart /
harness-status), Phase D (design.md/PLAN.md documentation rollout, cross-OS CI validation).

## What changed

Added `scripts/run_state.py` — a stdlib-only durable run-state engine and CLI implementing
Phase A of GitHub issue #129: an append-only `specs/<slug>/events.jsonl` event log, an atomic
`specs/<slug>/RUN.json` projection, `fcntl.flock`-serialized reads/writes, idempotent event
replay with conflict detection, the 16-state FSM from the issue (queued → … → shipped, plus
blocked/escalated/cancelled/superseded), and 5 CLI subcommands (`init`, `transition`, `status`,
`list`, `rebuild`). Added `scripts/test_run_state.py` with 23 tests covering every stated
acceptance criterion, including a real multi-process concurrency test. No existing file was
modified except one added test-coverage follow-up; no skill/hook/rule/settings.json touched.

### Rationale

Phase A is the dependency root for B/C/D per the issue itself ("Proposal 2 ... should build
on this contract") — the engine's on-disk contract (event schema, projection schema, CLI
exit codes) must be stable before anything deploys it or wires workflow checkpoints into it.
Scoping this spec to Phase A only keeps the diff reviewable and isolates the highest-risk
correctness work (locking, atomicity, idempotent replay, rebuild-from-log) from the lower-risk
deployment/wiring work in later phases.

### Alternatives considered

- Do all four phases in one spec — rejected: Phase A alone is substantial (concurrency +
  atomicity + FSM correctness); bundling B–D would make the diff too large to review well and
  couples unrelated risk profiles (engine correctness vs. deploy plumbing vs. prompt wiring).

### Deviations

- Rule 1 — Fixed a lock-fd leak in `locked_run.__enter__`: `fcntl.flock` raising after `open()` succeeded left `__exit__` unreachable, leaking the fd. Wrapped in try/except, close-and-reraise. `scripts/run_state.py`. Commit `17176b2`.
- Rule 2 — Added `cmd_status` test coverage (happy-path `--json` + missing-run exit-3 path), which had zero tests; flagged by code-quality review as a real gap. `scripts/test_run_state.py`. Commit `7445f16`.
- Rule 2 — Added a one-line stderr warning when `cmd_list` skips a slug with a corrupted `RUN.json`, instead of silently omitting it (previously gave a false-clean read on `list --active`). Flagged by code-quality review on task 1.4 as a near-zero-risk fix. `scripts/run_state.py`. Commit `3317490`.
- Rule 1 — Fixed 6 adversarial correctness-review findings (all mechanical, no architectural judgment): `parse_meta` moved inside `main()`'s try/except so a malformed `--meta` exits 2 instead of an uncaught traceback; `read_events` now validates required event keys and raises `StorageError` (exit 3) on schema-incomplete-but-JSON-valid lines instead of a downstream `KeyError`/`TypeError`; `cmd_list`'s plaintext loop uses `.get()` instead of bare indexing so one malformed `RUN.json` no longer drops the whole listing; `cmd_transition`'s idempotency match now requires the matched `event_id` to be the LAST event (else raises `ConflictError` instead of falsely reporting success on a stale replay); `cmd_init` without `--run-id` is now idempotent (checks `os.path.exists` before generating a fresh uuid). `scripts/run_state.py`, `scripts/test_run_state.py` (23 → 29 tests). Commit `fix(run-state): correctness-review findings — exit-code contract, idempotency edge cases`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| unit | `python -m pytest scripts/test_run_state.py -k test_init_creates_queued_run -q` | 0 | fresh init → queued state | SC-1 |
| unit | `python -m pytest scripts/test_run_state.py -k test_invalid_transition_rejected -q` | 0 | invalid transition raises, exit 2 | SC-2 |
| unit | `python -m pytest scripts/test_run_state.py -k test_terminal_state_blocks_transition -q` | 0 | terminal states reject any transition | SC-3 |
| unit | `python -m pytest scripts/test_run_state.py -k test_idempotent_replay_and_conflict -q` | 0 | replay = no-op; conflicting reuse = exit 2 | SC-4 |
| unit | `python -m pytest scripts/test_run_state.py -k test_corrupt_log_fails_visibly -q` | 0 | corrupt/truncated log → exit 3, no fabrication | SC-5 |
| unit | `python -m pytest scripts/test_run_state.py -k test_rebuild_reproduces_projection -q` | 0 | rebuild reproduces RUN.json from events.jsonl | SC-6 |
| unit | `python -m pytest scripts/test_run_state.py -k test_concurrent_writers_sequence_contiguously -q` | 0 | 5 real OS processes, lock serializes, contiguous seq | SC-7 |
| unit | `python -m pytest scripts/test_run_state.py -k test_shipped_requires_valid_sha -q` | 0 | shipped without valid --sha rejected | SC-8 |
| unit | `python -m pytest scripts/test_run_state.py -k test_waiting_and_resume_metadata_required -q` | 0 | awaiting_*/blocked/escalated require metadata | SC-9 |
| unit | `python -m pytest scripts/test_run_state.py -q` | 0 | full suite, 29 passed |  |

`bash scripts/run-tests.sh` was also run from the repo root and confirmed ALL GREEN
(185 python + shell suites) as a repo-wide regression check, after the correctness-review
fixes below — not listed as its own Verify row per
`docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md` (whole-suite command
risks the 60s per-row re-run cap).

### Advisory Findings

<!-- From /correctness-review: findings that scored below the 75 fix-loop threshold. Not
     fixed, not discarded — reported for a human to weigh. -->

- **(score 50) `atomic_write_json` doesn't clean up its temp file or remap the exception if
  `os.fsync`/`os.replace` raises** (`scripts/run_state.py`, `atomic_write_json`). A disk-full or
  permission-denied failure mid-write leaves an orphan `<path>.tmp.<pid>` file and escapes as a
  raw `OSError` (exit 1) instead of the documented `StorageError` (exit 3). Scored 50 (real but
  low reachability — a small local JSON write to a repo directory rarely hits ENOSPC/EACCES in
  normal usage). Not fixed in this phase; worth a `try/except OSError: unlink tmp; raise
  StorageError` wrap if this surfaces in practice.
- **(score 50) `--slug` accepts path separators / `..`, allowing storage to land outside
  `specs/`** (`scripts/run_state.py`, `spec_dir`). `init --slug '../escaped'` writes
  `events.jsonl`/`RUN.json` outside the `specs/` root with exit 0. Scored 50 — currently the CLI
  has no external/untrusted caller (Phase B/C wiring is out of scope for this phase), so `--slug`
  is always supplied by a trusted operator on their own machine. Should be revisited (reject
  slugs matching `[^A-Za-z0-9._-]` or containing `..`) before Phase B/C exposes this to any
  less-trusted input path.

### Intent Findings

<!-- From /intent-review: findings against the verbatim original request, blind to PLAN.md. -->

- **(gap, minor, report-only — advisory)** Issue #129's proposed CLI shows
  `run_state.py list --active [--json|--prompt]`; only `--json` is implemented, `--prompt` is
  absent. This was a deliberate, documented decision, not an oversight — see PLAN.md §2
  Non-goals: "`--prompt` is speculative output shaping with no consumer yet in Phase A — add it
  when Phase C actually needs it." No action taken.
- **(drift, behaviorally different — ESCALATED, resolved, see ESCALATIONS.md E001)** Issue #129
  Phase A asks to "Add machine-readable event and projection schemas." What shipped is a
  docstring describing the event/RUN.json shape plus a runtime `REQUIRED_EVENT_KEYS` presence
  check in `read_events()`, not a separate formal schema-validation artifact (e.g. JSON Schema).
  Escalated as genuinely ambiguous rather than guessed at. **Decision (2026-07-24, Minh Tran):
  accepted as sufficient for Phase A** — the issue's contrast is JSON (machine-readable) vs.
  `specs/STATE.md` prose (human-only), not "informal" vs. "formal schema-validation artifact."
  No further work.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
