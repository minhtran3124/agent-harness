---
slug: durable-run-state
status: shipped
owner: Minh Tran
created: 2026-07-24
---

# Durable Run State — Canonical Plan (GitHub issue #129)

<!-- AT-A-GLANCE:BEGIN (generated — do not edit; refreshed by render_plan.py --summarize) -->
## At a glance

_No tasks defined yet._
<!-- AT-A-GLANCE:END -->

## 1. Motivation

See `research-brief.md` and `design.md` in this folder. This file is the acceptance-contract
rollup: it maps every one of issue #129's acceptance criteria to the phase that satisfies it
and the re-runnable check that proves it, so a reader (or CI) can confirm the whole contract
without reading four separate phase folders.

## 2. Non-goals

See `specs/gh-129-durable-run-state-phase-d/PLAN.md` §2 (this rollup's own authoring phase) —
quoted verbatim from the issue, not restated here to avoid drift.

## 3. Success Criteria (issue #129's acceptance criteria, mapped)

| ID | Behavior (observable) | Check (re-runnable) | Expected |
|------|-------------------------|-----------------------|------------|
| AC-1 | A new run can be initialized from a spec SUMMARY and produces valid `RUN.json` + `events.jsonl` | `python3 -m pytest runtime/test_run_state.py -k test_init_creates_queued_run -q` | exit 0 — Phase A |
| AC-2 | Valid transitions update both artifacts consistently | `python3 -m pytest runtime/test_run_state.py -k test_idempotent_replay_and_conflict -q` | exit 0 — Phase A |
| AC-3 | Invalid, skipped, reversed, and post-terminal transitions fail without mutation | `python3 -m pytest runtime/test_run_state.py -k "test_invalid_transition_rejected or test_terminal_state_blocks_transition" -q` | exit 0 — Phase A |
| AC-4 | Rebuilding from `events.jsonl` reproduces the current projection | `python3 -m pytest runtime/test_run_state.py -k test_rebuild_reproduces_projection -q` | exit 0 — Phase A |
| AC-5 | Duplicate event replay is idempotent; conflicting event reuse is rejected | `python3 -m pytest runtime/test_run_state.py -k test_idempotent_replay_and_conflict -q` | exit 0 — Phase A |
| AC-6 | Concurrent writers produce contiguous event sequences | `python3 -m pytest runtime/test_run_state.py -k test_concurrent_writers_sequence_contiguously -q` | exit 0 — Phase A (5 real OS processes) |
| AC-7 | Corrupt or truncated logs fail visibly and do not silently fabricate state | `python3 -m pytest runtime/test_run_state.py -k test_corrupt_log_fails_visibly -q` | exit 0 — Phase A |
| AC-8 | Active runs are discoverable from SessionStart/status surfaces | `bash tests/hooks/session-knowledge.test.sh` | exit 0 — Phase C |
| AC-9 | Fresh install and resync deploy `.claude/runtime/` and preserve consumer-owned additions | `bash tests/scripts/runtime-sync.test.sh` | exit 0 — Phase B |
| AC-10 | Legacy specs remain usable | `python3 -c "import glob,sys; bad=[1 for f in glob.glob('skills/*/SKILL.md') for l in open(f) if 'runtime/run_state.py' in l and 'true' not in l]; sys.exit(1 if bad else 0)"` | exit 0 — fails if any checkpoint call omits its non-fatal guard; passes vacuously before Phase C merges (no references yet) |
| AC-11 | Full harness tests pass on macOS and Ubuntu | `gh pr checks` | exit 0 — this phase, SC-9 |

## 4. Tasks

None — this is a rollup of already-completed work (Phases A–C), not a plan for new
implementation. See `specs/gh-129-durable-run-state-phase-{a,b,c,d}/PLAN.md` for the tasks
that actually built and verified this contract.

## 5. Risks

None beyond what each phase's own `PLAN.md` §5 already discloses.

## 6. Status Log

- 2026-07-24 — Canonical rollup created at Phase D, consolidating Phases A (PR #164), B
  (PR #166), and C (PR #167).
