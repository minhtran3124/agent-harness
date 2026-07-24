# Research: herdr-visible worker sessions instead of hidden subagents

**Date:** 2026-07-24
**Status:** research only — no implementation
**Context:** Idea under discussion: when the workflow needs a subagent, spawn it as a
*visible* Claude Code session managed by herdr instead of a hidden Task-tool subagent,
using the gh-129 durable-run-state contract as the return channel. This doc answers the
three open questions from that discussion. Evidence labels: **[verified-local]** = ran
the command / read the file on this machine; **[verified-web]** = herdr official docs;
**[unverified]** = not independently confirmed.

---

## Q1 — Can herdr see, spawn, and steer worker sessions?

**Answer: herdr is a launcher/multiplexer, not a watcher. It can spawn, observe, await,
and steer any session it launches — but it is blind to sessions started outside its
panes, including background `claude -p`.**

Ground truth (herdr 0.7.3 installed at `~/.local/bin/herdr`, server running,
socket `~/.config/herdr/herdr.sock`) [verified-local]:

- **This orchestrator session itself runs inside herdr** (pane `w1J:p1`, workspace
  `harness-skills`) and is tracked with its Claude `session_id` + transcript path,
  status `working`. Confirmed via `herdr api snapshot`.
- **Identity mechanism:** the installed Claude integration (v7) is a user-level
  `SessionStart` hook (`~/.claude/hooks/herdr-agent-state.sh`, wired in
  `~/.claude/settings.json`) that reports `session_id` + `transcript_path` to the herdr
  socket (`pane.report_agent_session`). It exits early unless `HERDR_ENV=1` and
  `HERDR_PANE_ID` are set — i.e. only sessions launched *inside a herdr pane* register.
  Subagent events (`agent_id` present) are explicitly ignored.
- **Empirical probe:** a `claude -p` run from the Bash tool created a real session
  (session_id `11895a36…`, transcript dir under `~/.claude/projects/`, resumable) but
  `herdr api snapshot` still listed only one agent — the headless run was invisible to
  herdr. So "background `claude -p` for visibility" is a dead end.
- **The full orchestration loop exists in the CLI** (all over the socket API, callable
  from any process, including this session's Bash tool):
  - Spawn: `herdr agent start <name> [--cwd PATH] [--workspace ID] [--env K=V] -- <argv…>`
  - Steer: `herdr agent send <target> <text>`, `herdr pane send-keys`, `herdr pane run`
  - Observe: `herdr agent read <target> [--lines N]`, `herdr agent list`, `herdr api snapshot`
  - Await: `herdr agent wait <target> --status idle|working|blocked|unknown [--timeout MS]`,
    `herdr wait agent-status <pane> --status …|done`, `herdr wait output <pane> --match <re>`
  - Human takeover: `herdr agent attach <target> [--takeover]`, or just click/type in the pane
  - Extras: `herdr worktree create --branch NAME --base REF`, `herdr notification show`
- Web docs corroborate: Apache-2.0, single Rust binary, macOS+Linux, actively
  maintained (docs updated 2026-07-23); persistent background server so agents survive
  terminal exit and are restored after server restart via Claude session refs
  [verified-web: herdr.dev/docs, github.com/ogulcancelik/herdr].

**Design consequence:** the push-vs-pull tension from the original discussion
collapses. Workers should be spawned as **interactive** Claude sessions in herdr panes
(`herdr agent start worker-N --cwd <worktree> -- claude "<task>"`). That single shape is
simultaneously visible (pane), steerable (human attach *or* `agent send`), and awaitable
(`agent wait` / `wait agent-status --status done` with timeout). Headless `claude -p` is
only useful where visibility is *not* wanted.

Notes for the spawn recipe [unverified until prototyped]:
- Permission prompts render in the worker's own pane — human-approvable there; for
  autonomy pass an explicit `--permission-mode`.
- `claude --session-id <uuid>` could pre-assign the worker's session id so run-state
  events can be correlated before the worker even starts.
- Each worker pays full session startup (fresh context, SessionStart hooks, MCP init;
  probe showed ~31k tokens cache creation in an *empty* dir — more in-repo).

## Q2 — Stall detection for claimed-but-unfinished tasks

**Answer: the gh-129 engine has deliberately no heartbeat/lease — and with herdr in the
picture it doesn't need one in v1. Liveness can come from the pane layer; the event log
only needs to carry the correlation ids, and its existing `metadata` dict already can.**

Engine ground truth (`runtime/run_state.py`, 494 lines, phases A–C) [verified-local]:

- Per-slug storage `specs/<slug>/`: `events.jsonl` (append-only) + `events.jsonl.lock`
  (fcntl LOCK_EX around read→validate→append→project) + `RUN.json` (rebuildable
  projection, atomic replace). Idempotency via client-supplied `event_id`.
- Event schema: `event_id, seq, ts, slug, run_id, from_state, to_state, event,
  waiting_on, resume_event, sha, metadata{}`. **No actor/session/pid field** — but
  `metadata` is a free dict, so adding `claude_session_id` / `herdr_pane_id` at claim
  time requires **no schema change**.
- FSM: 11 active states, interrupts (`blocked`, `escalated`), terminals (`shipped`,
  `cancelled`, `superseded`); invalid transitions exit 2 without mutation.
- Staleness/heartbeat/lease: **absent by explicit deferral** (phase-c SUMMARY, phase-d
  PLAN): abandoned runs never reach terminal and accumulate in `list --active`
  (display capped at 5 in `hooks/session-knowledge.sh`). Known, documented limitation.

Layered proposal (keeps recovery out of scope per gh-129 non-goals):

1. **Liveness = herdr, durability = run-state.** Worker's claim event records
   `metadata: {claude_session_id, herdr_pane_id}`. A task is *stalled* when its run is
   non-terminal **and** the recorded pane is gone from `herdr api snapshot`, or its
   agent has sat `idle`/`blocked` past a threshold. Orchestrator (or
   `harness-status.sh`) computes this read-only — no engine change.
2. **Await with timeouts, not polling loops:** `herdr agent wait <target> --status idle
   --timeout <ms>`; on timeout, run the stall check; on stall, surface to the human
   (notification) rather than auto-respawn — self-healing stays a separate proposal
   (Proposal 2 non-goal).
3. **Engine-level lease/heartbeat:** only if cross-machine or herdr-less operation ever
   matters. Defer.

Residual gap: herdr restores panes after *its own* restart, but a machine reboot or a
human closing a pane mid-task still yields a claimed, non-terminal run — that is exactly
what check (1) catches at the next orchestrator wakeup / SessionStart surface.

## Q3 — Worktrees and the missing `.claude/`

**Answer: confirmed real and already mitigated by convention — the spawn recipe must run
`deploy-harness.sh` in the worktree before starting the worker.**

Ground truth [verified-local]:

- `.gitignore:26` ignores `.claude/` → every fresh `git worktree add` (and
  `herdr worktree create`) contains **zero** `.claude/`. Tracked source dirs
  (`runtime/`, `hooks/`, `rules/`, `skills/`, `scripts/`…) *are* present.
- Without `.claude/`: Skill-tool resolution breaks (project skills unresolvable —
  memory note, confirmed on PR #63), **no project hooks fire** (registration lives in
  `.claude/settings.json`), rules don't auto-load. Direct invocation by path
  (`runtime/run_state.py`, `scripts/*.sh`) still works.
- `skills/using-git-worktrees/SKILL.md` Step 2 already mandates
  `bash scripts/deploy-harness.sh --target "$(git rev-parse --show-toplevel)"` from
  inside the worktree, before anything else. Deploy copies
  `skills agents hooks rules templates runtime` into `.claude/` and jq-merges
  settings.json — seconds, not heavy.
- Test running in worktrees: bare `python3` may lack pytest; use the shared venv
  `${TMPDIR:-/tmp}/harness-tests-venv/bin/python` (memory note).

**Design consequence:** worker spawn is a three-step recipe, not one command:
`herdr worktree create` (or existing skill) → `deploy-harness.sh --target <worktree>` →
`herdr agent start … --cwd <worktree> -- claude …`. Skipping step 2 silently produces a
worker with no hooks and no skill chain — worse than failing loudly. A worker-spawn
helper script should hard-fail if `<worktree>/.claude/settings.json` is absent.

---

## Synthesis — recommended shape for a prototype

1. Orchestrator (herdr-hosted, like this session) drives one wave task end-to-end:
   `herdr worktree create --branch <task-branch>` → deploy → `herdr agent start` with
   the task prompt → `herdr agent wait --status idle --timeout …` → read
   `specs/<slug>/SUMMARY.md` + `RUN.json` for the structured result → stall-check via
   snapshot on timeout.
2. Worker writes results through the existing file contracts (SUMMARY.md, run-state
   transitions with `metadata` correlation ids). No `run_state.py` schema change.
3. Human can watch/steer any worker pane at any time; permission prompts are visible
   in-pane instead of buried.
4. Out of scope (deliberate): auto-respawn/self-healing (Proposal 2), engine
   heartbeats, observing non-herdr sessions.

Open items before building: exact `herdr agent start -- claude …` argv (flags, env,
`--session-id` pre-assignment); semantics of `wait agent-status --status done` vs
`agent wait --status idle` for Claude panes; token cost per worker vs Task-tool
subagent; wiring this into `subagent-driven-development` would be a workflow-engine
change → high-risk lane + automation-readiness consult when it gets that far.
