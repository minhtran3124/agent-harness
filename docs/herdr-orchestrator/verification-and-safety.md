# Verification and safety

## idle ≠ done

`herdr agent wait --status idle` only proves the worker's turn ended — success, failure,
and "stopped to ask a question" all look identical. After every wait, verify from files:

1. `<worktree>/specs/<slug>/SUMMARY.md` — Verify rows filled with real exit codes?
   Deviations recorded? Blockers empty?
2. `git -C <worktree> log --oneline` — did the promised commit actually land?
3. Run-state, if the worker's chain emitted any:

   ```bash
   (cd "$WT" && python3 runtime/run_state.py status --slug <slug>)   # --slug is required
   (cd "$WT" && python3 runtime/run_state.py list --active --json)
   ```

   Both resolve `specs/<slug>/` from the **current directory** — run them from the
   worktree or you are reading your own repo's state. A missing `RUN.json` means the
   best-effort transitions never fired; it is not evidence of failure (`delegation.md`).

Check 2 outranks check 3, and check 1 outranks both when they disagree: a worker that
says "done" with an empty Verify table is not done (`rules/orchestration.md` → evidence
over assertion), whatever `RUN.json` says.

## Reading a worker's run-state

When `RUN.json` is present, `state` tells you where in the chain the worker got to. The
FSM is 16 states — 11 active, 2 interrupts, 3 terminal — and it has **no heartbeat, lease,
or staleness field** (deliberately deferred). That is exactly why liveness comes from the
pane layer and durability from the file:

| `state` | What it means for the orchestrator |
| --- | --- |
| `investigating` / `planning` | intake ran; no code yet |
| `implementing` / `verifying` | the worker is inside `subagent-driven-development` |
| `awaiting_review` / `addressing_review` / `awaiting_ci` / `fixing_ci` | post-diff chain |
| `ready_to_merge` | `finishing-a-development-branch` opened the PR — **your stop line** |
| `blocked` / `escalated` | interrupt; `waiting_on` + `resume_event` say what unblocks it |
| `shipped` / `cancelled` / `superseded` | terminal — a stall check on these is a false positive |

Non-terminal state + dead pane = stalled. Terminal state = done regardless of the pane.

## Gates still apply inside workers

An armed worktree (`parallel-worktrees.md`) carries the full hook set — commit-quality
gate, risk corroboration, branch isolation all fire *inside* the worker's own session.
That is the safety model: enforcement is per-session and mechanical, so the orchestrator
does not need to trust worker self-reports. This is also why the arm step may never be
skipped.

## Never automate

- **No auto-respawn.** A stalled or failed worker is surfaced
  (`herdr notification show … --sound request`), not restarted. Self-healing/retry
  budgets are an explicitly separate proposal (gh-129 Proposal 2 non-goal).
- **No auto-merge, no auto-push of worker branches.** The finishing flow
  (`/finishing-a-development-branch`) creates PRs; humans merge.
- **No steering another human's panes.** `agent send` / `send-keys` only target panes
  this orchestrator spawned.
- **No worktree deletion with uncommitted work** without human confirmation.

## Escalation

Worker escalation paths are unchanged from the standard workflow: a worker that hits a
hard gate or concludes "the plan itself is wrong" STOPs and records it
(`specs/<slug>/ESCALATIONS.md`, deny-on-no-response). The orchestrator relays via
notification and blocks that task — other workers may continue.

## Interrupt honestly

To stop a worker mid-flight: `herdr agent attach --takeover` and Esc/Ctrl-C like a
human would, or close the pane. Then record the abandonment (run-state `cancelled`
transition or a SUMMARY note) — a killed worker with no record is how stale "active"
runs are born.
