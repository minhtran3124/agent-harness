# herdr-orchestrator — playbook (MVP)

> Status: **experimental MVP**. Guidance docs only — nothing here is wired into skills,
> hooks, or rules. An orchestrator session Reads these on demand (same convention as
> `techstacks/`). Grounding: `docs/research/2026-07-24-herdr-visible-worker-sessions.md`.
> Commands re-verified against herdr 0.7.3 and this tree on **2026-07-26**.

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
herdr worktree create --cwd "$PWD" --branch feat/<slug> --base <base-ref> --no-focus --json
WT=$(herdr worktree list --cwd "$PWD" --json \
     | python3 -c 'import json,sys;print([w["path"] for w in json.load(sys.stdin)["result"]["worktrees"] if w["branch"]=="feat/<slug>"][0])')

# 2. Arm — deploy the harness into the worktree; hard-fail if it didn't land.
#    Run the WORKTREE's own copy of the script: it resolves sources from its own
#    path, so `bash scripts/deploy-harness.sh` here would ship YOUR branch's
#    skills/hooks into the worker. --yes keeps a re-arm from blocking on a prompt.
bash "$WT/scripts/deploy-harness.sh" --target "$WT" --yes
test -f "$WT/.claude/settings.json" || exit 1

# 3. Spawn — interactive worker in a visible pane (see agent-lifecycle.md)
herdr agent start worker-<n> --cwd "$WT" --no-focus -- claude "<task prompt>"

# 4. Await — block until the worker settles (see verification-and-safety.md)
herdr agent wait worker-<n> --status idle --timeout 1800000

# 5. Collect — results come from files in the WORKTREE, never from scraping the pane
#    $WT/specs/<slug>/SUMMARY.md · git -C "$WT" log --oneline
#    $WT/specs/<slug>/RUN.json (opportunistic — see verification-and-safety.md)
```

Every read-back is worktree-relative. `run_state.py` resolves `specs/<slug>/` from the
**current directory**, so query it as `(cd "$WT" && python3 runtime/run_state.py …)` —
running it from your own checkout silently reports your own specs.

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
