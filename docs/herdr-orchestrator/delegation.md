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

- `specs/<slug>/SUMMARY.md` — lane, commits, files touched, deviations, Verify rows.
  **The reliable channel.** Corroborate with `git -C <worktree> log --oneline`.
- `specs/<slug>/RUN.json` + `events.jsonl` (`runtime/run_state.py`) — **opportunistic.**
  The standard chain does emit transitions (`/feature-intake` runs `init` +
  `investigating`/`planning`, `subagent-driven-development` marks `implementing` /
  `verifying`, `finishing-a-development-branch` marks `ready_to_merge`), but every call
  is best-effort `|| true` by design: a worker can finish correctly and leave no
  `RUN.json` at all. Treat its absence as "no signal", never as failure.

### Correlation ids are not automatic

Nothing in the shipped chain records who is running a task — `run_state.py` has no
actor/session field. The event `metadata` dict is free-form and `transition --meta k=v`
exists, so correlation is possible, but **only if the task prompt asks for it**. herdr
exports `HERDR_PANE_ID` into every pane it starts (that is how the Claude integration
hook registers the session), so a worker can self-identify:

```bash
python3 runtime/run_state.py transition --slug <slug> --to implementing \
  --event plan.execution_started \
  --meta "herdr_pane_id=$HERDR_PANE_ID" --meta "claude_session_id=<uuid>" || true
```

If you skip this, keep your own `worker-<n> → slug → pane-id` map instead. Do not claim
in a SUMMARY that ids were recorded when they were not.

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

## Gates the worker will hit — say so up front

An armed worktree runs the full commit gate, and a worker that meets it cold burns a turn
(or improvises around it) in a pane you are not watching. Name these in the prompt:

- **Lane evidence.** `hooks/commit-quality-gate.sh` runs
  `scripts/verify_summary.py --lane` against every staged `specs/*/SUMMARY.md`; a
  `normal`/`high-risk` SUMMARY with no `### Verify` rows is **denied at commit**, not
  warned. Step 1 of the template exists to satisfy this.
- **Verify-row shape.** No `|` inside a command cell (it splits the table), and keep each
  command under the 60s per-command timeout — no whole-suite invocations.
- **Separate `git add` / `git commit` calls.** `hooks/check-untracked-py.sh` scans the
  whole command string before it runs, so `git add x.py && git commit …` in one Bash call
  is denied on its own untracked file.
- **Risk corroboration.** A `Lane:` below `high-risk` is blocked when the staged diff
  trips a block-mode hard gate (`harness-manifest.json`). Give the worker the lane the
  plan assigned; do not let it downgrade to get past the gate.
