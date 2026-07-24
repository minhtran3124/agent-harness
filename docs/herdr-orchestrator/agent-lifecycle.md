# Agent lifecycle

Spawn → await → collect → stall-check → close. All commands talk to the herdr socket and
work from any process, including the orchestrator's Bash tool.

## Spawn

```bash
herdr agent start worker-<n> --cwd <worktree-path> [--workspace ID] [--env K=V] -- claude "<task prompt>"
```

- **Never spawn with `-p` / print mode.** A print-mode `claude` process runs to
  completion and exits; herdr closes the pane the moment the process ends, so `agent
  wait` / `agent read` afterward return `agent_not_found` — confirmed by testing. Pass
  the task prompt as a plain positional argument to interactive `claude` so the session
  stays open and idles in-pane after the turn.
- `agent start` returns once herdr detects the agent is ready for input.
- Name workers after their task (`worker-gh129-d1`), not sequentially — names are how
  you target `send` / `wait` / `read` later.
- Precondition: the worktree is armed (`parallel-worktrees.md`). A worker spawned in an
  unarmed worktree runs with no hooks and no skill chain — silently ungoverned.

## Await

```bash
herdr agent wait worker-<n> --status idle --timeout <ms>     # settled (turn finished)
herdr wait agent-status <pane-id> --status blocked --timeout <ms>  # waiting on permission/input
```

- `idle` means the session finished a turn — **not** that the task succeeded. Truth
  lives in the files (`verification-and-safety.md`). Confirmed by testing: a `wait
  --status idle` call returned while a `read` moments later showed the worker still
  mid tool-call — treat `idle` as "check now", not "finished".
- Always pass `--timeout`. A wait without a timeout turns a stalled worker into a
  stalled orchestrator.
- If a wait times out, `read` before re-waiting blindly — the worker may be legitimately
  still working (e.g. investigating a gate failure), not stalled. Only escalate as a
  stall per `verification-and-safety.md` once the pane is gone or genuinely idle/blocked
  past the threshold.

## Steer (use it — don't just watch)

Steering isn't a nice-to-have for emergencies only: watch what the worker is actually
doing between waits, and intervene the moment it drifts from its task scope (e.g. it
starts "fixing" a hook, running a full test suite, or editing files outside its Files
list) instead of reporting the blocker. `agent send` is cheap; a scope-creep commit is
not.

```bash
herdr agent read worker-<n> --lines 40        # peek at the pane
herdr agent send worker-<n> "<text>"          # inject a message (literal text)
herdr agent attach worker-<n> --takeover      # human takes the keyboard
```

The human can also just focus the pane and type — that is the point of the feature.

## Stall-check

A worker is **stalled** when its task/run is non-terminal AND either its pane no longer
appears in `herdr api snapshot`, or its agent has sat `idle`/`blocked` past your wait
timeout. On stall: `herdr notification show "worker-<n> stalled" --sound request` and
stop — the human decides. Never auto-respawn (see `verification-and-safety.md`).

## Collect and close

1. Read `specs/<slug>/SUMMARY.md` (and `RUN.json` if run-state is in use) from the
   worktree — that is the return value.
2. Close the pane (`herdr pane close <pane-id>`) or leave it open for the human to
   inspect; remove the worktree only after the branch is pushed/merged
   (`parallel-worktrees.md`).
