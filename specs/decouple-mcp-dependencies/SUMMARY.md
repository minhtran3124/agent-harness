# decouple-mcp-dependencies — Summary

Lane: high-risk
Confidence: high
Reason: judgment hard gate remove-functionality (installer stops wiring .mcp.json; test-runner loses context7; Codex context7 policy removed), plus detectable workflow-engine (skills/visual-planner/SKILL.md, agents/*.json) and high-blast (skills/visual-planner/render_plan.py) signals
Flags: existing behavior, public contracts, workflow-engine, high-blast, multi-domain
Affects: install-harness.sh / deploy-harness.sh consumer install contract; agents runtime bindings + Codex agent renderer; visual-planner review overlay; CLAUDE.md / README docs
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/decouple-mcp-dependencies/intent.md @ e32350ea7f87ed6ddea34c331f2d97f17516101c

i want to remove the current mcp "code-review-graph" and "context7" in the current workflow. The user need to install it manually by themself and update instructions to claude.md by themself.
because i dont want current harness workflow stick with any mcp or plugin, it will make the user confuse or even error if they dont install them.
mcp/plugins should be the external, not required.

- approved for intent
- add notes how to configration back for code-review-graph and context7.

### Intake notes

- Confidence was medium on the first draft (six assumed defaults). The user approved intent.md
  with those defaults in it, so one interpretation is now pinned → high; no escalation needed.
- Branch: intake ran on `sdlc` at the user's request; the intent commit was made on
  `refactor/decouple-mcp-dependencies` cut from `sdlc` rather than on `sdlc` itself, because
  `sdlc` is a shared integration branch (PRs target it). PR base: `sdlc`.
- The current session shows the failure mode the change targets: `code-review-graph (ENOENT):
  Executable not found in $PATH: uvx`.
- The approach is already settled by the approved intent; brainstorming should be short (confirm
  no real design fork) before xia2 maps every reference.
- 2026-10-14 (xia2): open PR #279 (base `main`) auto-installs uv and pre-fetches code-review-graph,
  contradicting this change. User chose "keep it open, decide later": this change ignores #279 and
  touches only what is on `sdlc`; the installer conflict surfaces when both reach `main`.

## What changed

<pending — filled at implementation>

### Rationale

<pending>

### Alternatives considered

- none

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Intent pin matches committed intent.md | `git diff --exit-code e32350e -- specs/decouple-mcp-dependencies/intent.md` | 0 | intake-time check; implementation rows added later | |

### Not auto-verified

- none

### Rollback

- `git revert <sha>` per commit on `refactor/decouple-mcp-dependencies`; consumer `.mcp.json` files are never edited by this change, so there is nothing to restore downstream.

### Harness-Delta

- none
