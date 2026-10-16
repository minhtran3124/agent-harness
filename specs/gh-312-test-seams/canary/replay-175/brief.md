# Task brief: 2.1

Plan: `/home/minhtran/Documents/minh.tran/projects/agent-harness/.claude/worktrees/feat+gh-312-test-seams/specs/gh-312-test-seams/canary/replay-175/PLAN.md`

## Global Constraints

- Plan-contract: 2
- Implement in an isolated branch/worktree from `simplify`; preserve unrelated worktrees and user
  changes.
- `runtime/resume_decision.py` remains the single public resume authority and derives every state
  set/legal edge from `runtime/run_state.py`.
- The decision command is semantically read-only: it may inspect git/files and acquire the engine's
  ignored lock file, but must not run plan-authored commands or write/rebuild canonical evidence.
- Contradictory or unresolvable evidence fails closed with a structured `stop`; absence remains
  explicit unknown, never inferred success.
- Human/session judgment remains responsible for confirming waits/blockers and evaluating
  deviations; code supplies evidence and required transitions only.
- Canonical markdown and legacy XML plans remain resumable, with parity fixtures against the live
  renderer's ordered task IDs. Resume completion is associated per task mention and tested
  independently from the renderer's presentation-grade done set.
- No test may parse `SKILL.md` prose to prove lifecycle behavior.
- Every focused Verify below must finish in under 60 seconds; run `bash scripts/run-tests.sh` once
  before shipping and record it in the Status Log/SUMMARY rather than as an SC row.

## Task

### Task 2.1 — Complete the versioned resume cursor authority (wave 2)

- **Files:** runtime/resume_decision.py, runtime/test_resume_decision.py
- **Action:** Replace the current partial verdict with the design's version-1 structured schema.
  Consume Task 1.1's locked snapshot; parse canonical markdown and legacy XML task definitions,
  Verify commands, plan status, and Status Log completion markers associated with individual task
  mentions; return ordered `claimed_complete`, `pending`, `next_task`, and `checks_to_rerun`. A
  mixed entry such as `Task 1.1 complete; Task 1.2 pending` must claim only `1.1`. Accept `--base`;
  otherwise apply the conservative non-self upstream/nearest-ancestor policy. Require claimed SHAs
  to resolve inside
  the chosen `BASE..HEAD`, and stop on ambiguity/conflict. Extract SUMMARY deviations and only a
  same-slug, <=7-day STATE hint. Encode the exact lifecycle matrix, shipped-plan repair exception,
  proposed/paused activation action, missing/invalid-plan stop, untracked-run behavior, and
  interrupt return transition; recover original waiting metadata from the event that entered a
  waiting origin and return its allowed successors. Apply the documented decision precedence so a
  task-cursor conflict cannot override terminal/wait/repair/review-chain routing. Keep every valid
  decision exit 0, CLI misuse exit 2, unexpected failure exit 3. Never execute a Verify command or
  rewrite canonical evidence.
  Add exact expected-result tests for every state/storage/plan combination, task-order parity
  fixtures against the renderer, a mixed complete/pending completion fixture,
  wrong-base/stale-STATE/paused-plan cases, schema stability, and before/after canonical-file byte
  snapshots proving semantic read-only behavior.
- **Verify:** `python3 -m pytest runtime/test_resume_decision.py -q`
- **Done:** the helper answers both lifecycle route and task cursor with stable reason codes; all
  current states have exact expected actions; every reproduced #175 gap and negative evidence case
  is covered behaviorally.
- **Criteria:** SC-2, SC-3, SC-4, SC-5, SC-6, SC-7
- **Interfaces:** Consumes: `runtime/run_state.py`, PLAN/SUMMARY/STATE artifacts, and git refs. Produces: `runtime/resume_decision.py`, `runtime/test_resume_decision.py`.
- **Seams:** `runtime/resume_decision.py --slug <slug>` JSON output — catches: a wrong action, reason_code, next_task or claimed_complete for a given PLAN, SUMMARY and RUN.json; misses: crashes in git or file I/O that the CLI turns into exit 3

## Mapped Success Criteria

| SC-2 | Every engine state and storage combination maps to one exact action/reason code, and adding an unclassified state fails the suite | `python3 -m pytest runtime/test_resume_decision.py -k "state_matrix or storage_matrix" -q` | exit 0 |
| SC-3 | A shipped plan blocks task execution while shipped-plan CI/review repair states remain routable | `python3 -m pytest runtime/test_resume_decision.py -k shipped_plan -q` | exit 0 |
| SC-4 | Interrupt recovery returns an executable transition, including recovered original `waiting_on` and successor data for every waiting origin | `python3 -m pytest runtime/test_resume_decision.py -k "interrupt or waiting_origin" -q` | exit 0 |
| SC-5 | Markdown and legacy plans yield an ordered task cursor; claimed-complete tasks expose checks to re-run and disputed task/commit evidence stops resume | `python3 -m pytest runtime/test_resume_decision.py -k "cursor or git_evidence" -q` | exit 0 |
| SC-6 | Only same-slug, <=7-day STATE context is consumed and SUMMARY deviations are returned without changing lifecycle routing | `python3 -m pytest runtime/test_resume_decision.py -k "state_hint or deviations" -q` | exit 0 |
| SC-7 | All valid decisions emit the stable version-1 JSON shape and leave every canonical evidence file byte-identical | `python3 -m pytest runtime/test_resume_decision.py -k "schema or readonly" -q` | exit 0 |

## Interfaces

Consumes: `runtime/run_state.py`, PLAN/SUMMARY/STATE artifacts, and git refs. Produces: `runtime/resume_decision.py`, `runtime/test_resume_decision.py`.
