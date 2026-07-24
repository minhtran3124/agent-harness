# Delegation — worker vs Task-tool subagent

## Choose the vehicle

| Signal | Vehicle |
| --- | --- |
| Long-running implementation task (a wave task, a full skill chain) | herdr worker |
| Human may want to watch, steer, or approve permissions mid-flight | herdr worker |
| Task needs its own branch/worktree anyway | herdr worker |
| Quick read-only research, code search, one-shot review | Task-tool subagent |
| Result needed inline in the current turn, seconds not minutes | Task-tool subagent |

Rule of thumb: if you would have opened a terminal and run it yourself, it's a worker.
If it's an internal step of your own reasoning, it's a subagent.

## Return channel: files, not stdout

A worker's pane output is for humans. The orchestrator reads results from the same
contract subagents already use (`rules/orchestration.md` → subagent contract):

- `specs/<slug>/SUMMARY.md` — lane, commits, files touched, deviations, Verify rows
- `specs/<slug>/RUN.json` + `events.jsonl` — when run-state tracking is in use
  (`runtime/run_state.py`); the worker records `claude_session_id` and `herdr_pane_id`
  in event `metadata` at claim time so stalls can be correlated later

## Task-prompt template

The worker is a fresh session — it knows nothing about this conversation. The prompt
must be self-contained:

```text
You are a worker session for task <task-id> of specs/<slug>/PLAN.md (lane: <lane>).

Scope: <one-paragraph task statement>.
Files you may touch: <explicit list from the plan>.
Base branch: <branch>. You are already on your own worktree/branch — do not switch.

Do the work, then:
1. Run the task's verify command: <command> — record the row in specs/<slug>/SUMMARY.md.
2. Fill SUMMARY.md sections (What changed / Rationale / Deviations).
3. Commit on this branch (git add and git commit in SEPARATE Bash calls).
Stop after committing. If the plan itself seems wrong, STOP and say so instead of improvising.
```

Keep one task per worker. If the prompt needs more than ~a screen of context, point the
worker at files to Read instead of inlining them.
