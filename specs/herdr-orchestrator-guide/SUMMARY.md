# herdr-orchestrator-guide — Summary

Lane: tiny
Confidence: high
Reason: Docs-only addition under `docs/herdr-orchestrator/` — no edits to `skills/*/SKILL.md`,
`hooks/*`, `settings.json`, or any core skill engine, so no hard gate fires. Single-purpose
guidance docs derived from an existing research doc; no behavior change to the harness.
Flags: none
Affects: docs/herdr-orchestrator/ (new guidance doc set), specs/herdr-orchestrator-guide/
Input-type: feature idea (screenshot + verbal)

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

"hãy check screenshot này, idea có thể viết thêm markdown riêng để hướng dẫn, điều hướng
workflow. đây chỉ là 1 tính năng nhỏ dc sinh ra lúc nhất thời, ko cần phải quá hoàn hảo ở
mức mvp"

Screenshot shows a `herdr-orchestrator/` doc set from another project (agent-lifecycle.md,
delegation.md, model-routing-and-context.md, parallel-worktrees.md,
verification-and-safety.md + a HERDR_ORCHESTRATOR.md entry doc) as the structural model.
Context: same-session research in `docs/research/2026-07-24-herdr-visible-worker-sessions.md`
(visible worker sessions via herdr instead of hidden Task-tool subagents).

## What changed

Created `docs/herdr-orchestrator/` — an MVP playbook an orchestrator session Reads on
demand before spawning herdr-visible worker sessions: README.md (entry, core loop) +
agent-lifecycle.md, delegation.md, parallel-worktrees.md, model-routing-and-context.md,
verification-and-safety.md.

**2026-07-26 accuracy pass** (rebased onto `cc-herdr`, 132 commits of drift since the
branch was cut). Every command re-run against herdr 0.7.3 and this tree; four claims were
wrong and are corrected:

1. `run_state.py status <slug>` → **`status --slug <slug>`**. The documented form exits 2
   with a usage error.
2. The arm step must invoke the **worktree's own** `deploy-harness.sh`
   (`bash "$WT/scripts/deploy-harness.sh"`). The script resolves sources from its own path
   (`ROOT="$(dirname "$0")/.."`), so the previous `bash scripts/deploy-harness.sh --target
   "$WT"` armed the worker with the *orchestrator's* branch of skills/hooks/rules. Added
   `--yes` — a re-arm with a differing protected file otherwise blocks on `/dev/tty`.
3. "The worker records `claude_session_id`/`herdr_pane_id` in event metadata at claim
   time" was stated as fact; **no shipped skill does this.** Reframed as an opt-in the
   task prompt must request, with the real `transition --meta k=v` invocation.
4. `run_state.py` resolves `specs/<slug>/` from **cwd** — read-backs must be
   `(cd "$WT" && …)` or they report the orchestrator's own specs.

Also brought current: run-state is now wired into the standard chain (feature-intake /
subagent-driven-development / finishing) but every call is best-effort `|| true`, so
`RUN.json` is opportunistic, not a contract — added a state→meaning table and made
SUMMARY.md + `git log` the ranked oracles; `herdr worktree` placement
(`~/.herdr/worktrees/…`, not `.worktrees/`) and JSON path resolution, since the core loop
used `<worktree-path>` without saying where it comes from; `--cwd`/`--no-focus` on the
herdr calls; the `agent wait` vs `wait agent-status` status-set difference; the four
commit gates a worker will hit (lane evidence, Verify-row shape, split add/commit, risk
corroboration); `--session-id` un-hedged to "flag verified, argv combination still
untested". The research doc keeps its 2026-07-24 snapshot with a dated addendum.

### Rationale

Read-on-demand docs (same convention as `techstacks/`) instead of a new skill or rule:
a skill/rule edit is a workflow-engine hard gate (high-risk lane), which contradicts the
explicit MVP intent. Docs carry the same guidance with zero enforcement surface; promoting
to a skill stays available as a follow-up.

### Alternatives considered

- New `skills/herdr-orchestrator/SKILL.md` — rejected for MVP: trips the workflow-engine
  hard gate, forces high-risk ceremony onto a spur-of-the-moment feature.
- Single flat markdown — rejected: the screenshot's per-topic split keeps each Read small
  and lets the orchestrator load only the stage it needs.

### Deviations

- Intake classification done inline (this file) rather than via the full /feature-intake
  skill run — MVP scope, docs-only, zero risk flags; recorded here per "record always-on".
- Rule 2 (2026-07-26): rebased the branch onto `cc-herdr` before verifying. Checking the
  docs against the stale base would have re-verified them against code the PR does not
  merge into.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Doc-truth lint (every referenced path exists) | `bash scripts/lint-doc-truth.sh` | 0 | all referenced paths exist; hook table matches settings.json |
| Old `status <slug>` form is genuinely broken | `python3 runtime/run_state.py status durable-run-state` | 2 | usage error — `--slug` is required; corrected in verification-and-safety.md |
| Corrected `status --slug` form parses | `python3 runtime/run_state.py status --slug durable-run-state` | 3 | reaches storage, exits 3 only because no run exists yet — no usage error |
| Arm recipe runs non-interactively | `bash scripts/deploy-harness.sh --target /tmp/harness-arm-dryrun --yes --dry-run` | 0 | first-time install path, no protected-file prompt |
| Worktree path resolution works | `herdr worktree list --cwd . --json` | 0 | `.result.worktrees[]` carries branch + path; herdr 0.7.3 |
| Lane-evidence gate denies an empty Verify table | `python3 scripts/verify_summary.py --lane specs/herdr-orchestrator-guide/SUMMARY.md --plan-dir specs/herdr-orchestrator-guide` | 0 | tiny lane passes; a synthetic `normal` SUMMARY with the same empty table exited 1 — the claim in delegation.md |

### Rollback

- `git revert <sha>` (branch `docs/herdr-orchestrator-guide`, PR #169). The accuracy pass
  is a single follow-up commit on top of the original doc commit; reverting it restores
  the 2026-07-24 text without removing the doc set.

### Harness-Delta

- none

Route: direct docs write (tiny lane) — branch + commit deferred until the user wants to land it
