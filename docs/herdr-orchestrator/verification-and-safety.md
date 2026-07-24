# Verification and safety

## idle ≠ done

`herdr agent wait --status idle` only proves the worker's turn ended — success, failure,
and "stopped to ask a question" all look identical. After every wait, verify from files:

1. `specs/<slug>/SUMMARY.md` in the worktree — Verify rows filled with real exit codes?
   Deviations recorded? Blockers empty?
2. `git -C <worktree> log --oneline` — did the promised commit actually land?
3. If run-state is in use: `python3 runtime/run_state.py status <slug>` — is the state
   the one the worker claims?

A worker that says "done" with an empty Verify table is not done
(`rules/orchestration.md` → evidence over assertion).

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
