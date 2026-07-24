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

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |

### Rollback

- `rm -rf docs/herdr-orchestrator/ specs/herdr-orchestrator-guide/` (files are untracked
  until committed; once committed, `git revert <sha>`)

### Harness-Delta

- none

Route: direct docs write (tiny lane) — branch + commit deferred until the user wants to land it
