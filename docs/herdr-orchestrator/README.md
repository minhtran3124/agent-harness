# herdr-orchestrator — playbook (MVP)

> Status: **experimental MVP**. Guidance docs only — nothing here is wired into skills,
> hooks, or rules. An orchestrator session Reads these on demand (same convention as
> `techstacks/`). Grounding: `docs/research/2026-07-24-herdr-visible-worker-sessions.md`.

Run workflow tasks as **visible, steerable worker sessions in herdr panes** instead of
hidden Task-tool subagents. One worker = one interactive Claude Code session in its own
herdr pane, on its own worktree/branch. The human can watch or take over any pane at any
time; the orchestrator awaits and collects results through files, not tool returns.

## When to use

Use a herdr worker when the task is long-running, the human may want to watch or steer
mid-flight, or the task needs its own permission surface (prompts render in the worker's
pane). Keep using Task-tool subagents for quick read-only research and anything that
should stay invisible. Details: `delegation.md`.

## The core loop

```bash
# 1. Isolate — worktree + branch (see parallel-worktrees.md)
herdr worktree create --branch feat/<slug> --base <base-ref>

# 2. Arm — deploy the harness into the worktree; hard-fail if it didn't land
bash scripts/deploy-harness.sh --target <worktree-path>
test -f <worktree-path>/.claude/settings.json || exit 1

# 3. Spawn — interactive worker in a visible pane (see agent-lifecycle.md)
herdr agent start worker-<n> --cwd <worktree-path> -- claude "<task prompt>"

# 4. Await — block until the worker settles (see verification-and-safety.md)
herdr agent wait worker-<n> --status idle --timeout 1800000

# 5. Collect — results come from files, never from scraping the pane
#    specs/<slug>/SUMMARY.md (+ RUN.json / events.jsonl when run-state is in use)
```

On timeout: stall-check via `herdr api snapshot` (pane gone or idle while the run is
non-terminal = stalled) → notify the human. Never auto-respawn.

## Topic docs

| Doc | Covers |
| --- | --- |
| `agent-lifecycle.md` | spawn → await → collect → stall-check → close |
| `delegation.md` | worker vs Task-subagent choice; task-prompt template; file return channel |
| `parallel-worktrees.md` | worktree + deploy recipe; parallelism limits; cleanup |
| `model-routing-and-context.md` | model/permission-mode per worker; startup token cost |
| `verification-and-safety.md` | evidence rules; idle ≠ done; escalation; what never to automate |
