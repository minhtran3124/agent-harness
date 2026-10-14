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
- README guidance adds two items beyond design.md's text, both from research-brief.md Docs
  findings: the `--scope user` fallback when a worktree session does not load a local-scope server,
  and the `@~/.claude/<file>.md` import because `CLAUDE.local.md` is per-worktree.

## What changed

<pending — filled at implementation>

### Rationale

<pending>

### Alternatives considered

- none

### Deviations

- Rule 2 — `scripts/test_render_agent_definitions.py`: the Claude `test-runner` tools assertion was a substring check that still passed with the context7 tools present; anchored to the whole `tools:` line, which fails against the old bindings. Commit `1ce515c`.

### Minor findings (task review, non-blocking)

- 1.1 — `tests/scripts/install-harness.test.sh`: the real-run fresh-install case checks `$OUT` for `.mcp.json` but not for `uvx` (the dry-run case covers `uvx`). checked_against SC-1.
- 1.1 — `scripts/install-harness.sh`: the reworded header comment line is longer than its neighbours (cosmetic).
- 1.4 — `README.md`: `echo ".code-review-graph/" >> .git/info/exclude` fails inside a linked worktree, where `.git` is a file; use `"$(git rev-parse --git-common-dir)/info/exclude"` or say "main checkout". checked_against SC-5.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Intent pin matches committed intent.md | `git diff --exit-code e32350e -- specs/decouple-mcp-dependencies/intent.md` | 0 | intake-time check; implementation rows added later | |

### Not auto-verified

- none

### Rollback

- `git revert <sha>` per commit on `refactor/decouple-mcp-dependencies`; consumer `.mcp.json` files are never edited by this change, so there is nothing to restore downstream.

### Harness-Delta

- backlog — the worktree-isolation guard refuses Bash calls whose text names git in a form it cannot verify (a heredoc mentioning `.git/info/exclude`, a script chained with git commands, a python heredoc naming git); implementers and the controller had to split commands or use the Edit tool (Task 1.4, Task 1.1, controller).
