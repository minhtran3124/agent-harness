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
| unit | `python -m pytest scripts/test_run_state.py -q` | 0 | full suite, 23 passed |  |
| repo | `bash scripts/run-tests.sh` | 0 | repo-wide regression gate, ALL GREEN (185 python + shell suites) |  |

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
