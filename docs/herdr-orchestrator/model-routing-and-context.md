# Model routing and context

## Cost model

Every worker is a full Claude Code session: SessionStart hooks, MCP init, CLAUDE.md +
rules + knowledge-base load. Measured floor: ~31k tokens of cache creation in an
*empty* directory — in-repo workers cost more. A worker is worth it for minutes-long
tasks; for a 30-second lookup it is pure overhead (use a Task-tool subagent).

## Routing

Pick the model per task with `claude --model <id>` in the spawn argv:

| Task shape | Model |
| --- | --- |
| Mechanical/scripted: run a checklist, apply a prepared patch, bulk renames | haiku |
| Standard implementation task from a PLAN.md | sonnet (default — omit the flag) |
| Hard design/debugging, high-risk lane, plan-is-ambiguous recovery | opus (or the session default) |

When unsure, omit `--model` and let the worker use the user's default.

## Permission mode

Visible panes make permission prompts a *feature* — the human approves in the pane.

- Default mode: good for high-risk or unfamiliar tasks; the human is the gate.
- `--permission-mode acceptEdits`: for trusted, plan-scoped implementation tasks where
  prompt-stalls would defeat the point of parallelism.
- Never grant a worker broader permissions than the orchestrator itself has.

## Context hygiene

- The worker starts blank: the task prompt must carry or point to everything
  (`delegation.md` template). Don't paste long file contents — name the paths.
- Pre-assigning identity: `claude --session-id <uuid>` lets you record the worker's
  session id in run-state metadata before it even starts (useful for stall
  correlation). Unverified flag combination — test before relying on it.
- One task per worker, then close. Reusing a long-lived worker pane for task after task
  accumulates stale context and defeats fresh-context isolation.
