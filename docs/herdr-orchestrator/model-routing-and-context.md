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
| Standard implementation task from a PLAN.md | sonnet |
| Hard design/debugging, high-risk lane, plan-is-ambiguous recovery | opus |

Omitting `--model` inherits the **user's configured default**, which is not necessarily
the middle tier — do not describe any row above as "the default". When unsure, omit the
flag; the aliases resolve to the current generation of each tier.

## Permission mode

Visible panes make permission prompts a *feature* — the human approves in the pane.

- Default mode: good for high-risk or unfamiliar tasks; the human is the gate.
- `--permission-mode acceptEdits`: for trusted, plan-scoped implementation tasks where
  prompt-stalls would defeat the point of parallelism.
- Never grant a worker broader permissions than the orchestrator itself has.

## Context hygiene

- The worker starts blank: the task prompt must carry or point to everything
  (`delegation.md` template). Don't paste long file contents — name the paths.
- Pre-assigning identity: `claude --session-id <uuid>` is a real flag (verified in
  `claude --help`) and lets you know the worker's session id before it starts, so
  run-state metadata can carry it (`delegation.md` → correlation ids). Passing it
  *through* `herdr agent start … -- claude --session-id <uuid> "<prompt>"` is still
  untested end-to-end — verify on first use rather than assuming.
- One task per worker, then close. Reusing a long-lived worker pane for task after task
  accumulates stale context and defeats fresh-context isolation.
