# gh-268-codex-agent-profile-paths — Summary

Lane: high-risk
Confidence: medium
Reason: workflow-engine delivery — the change rewrites what isolated Codex subagent contexts (`.codex/agents/*.toml` `developer_instructions`) are told and adds a consumer-owned file at install; one material choice (how a Codex-only consumer gets `agents/PROJECT.md`) needs the user.
Flags: workflow-engine, public contracts, existing behavior, cross-platform
Affects: `scripts/render_codex_adapter.py` (agent profile render), Codex installer, `docs/codex-alpha-install.md`
Input-type: spec slice
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: yes (agents/PROJECT.md delivery has three materially different options; asked at brainstorming)

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> current the hook scripts are not available with codex
> and the claude code now support AGENTS.md file
> let review and checking if we can support user with codex if they want to install our harness-skill

> approve design
> notes: - to avoid any breaking on main, let create branch call "codex" - all PRs related to it, let open to codex branch

> ok, let check sub-agent profile issue. and go to next phase 6 itme

> 268 first

This slug is GitHub issue #268 ("Codex Phase 6: agent profiles cite bare rules/ paths that a
Codex install does not have"), filed from the #254 context-propagation audit. Its Target checklist
is the scope. The branch stacks on `feat/gh-255-codex-hook-trust` (PR #271); the PR targets
`codex`.

## What changed

<pending>

### Rationale

<pending>

### Alternatives considered

- none

### Deviations

- none

### Task review log

- Task 1.1 (`b81095a`): spec pass, quality approved. Minor M1 (non-JSON `developer_instructions`
  raised a bare `JSONDecodeError`) and M2 (the one-line guard was untested) fixed in `1608b6a`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane gh-268-codex-agent-profile-paths` | 0 | intake |  |

### Not auto-verified

- none yet — filled at the end of the run.

### Rollback

- Code: `git revert` the branch's commits, or close the PR unmerged; nothing reaches `codex` until merge.
- Consumers: re-run `bash scripts/install-codex-harness.sh --source <pre-#268 checkout>`; the agent profiles are manifest-owned and are re-rendered (an edited profile is kept with a `.harness-incoming` sidecar).

### Harness-Delta

- none
