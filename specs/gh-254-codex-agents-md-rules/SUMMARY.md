# gh-254-codex-agents-md-rules — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine signal — the change decides how the always-on governance rules reach a Codex session, and rewrites the managed `AGENTS.md` section every Codex consumer receives (public contract).
Flags: workflow-engine, public contracts, existing behavior, cross-platform
Affects: Codex adapter (`adapters/codex/project/harness-instructions.md`, `scripts/render_codex_adapter.py`, `scripts/deploy-codex-adapter.sh`), consumer `AGENTS.md` managed section, `tests/scripts/rule-loading-tiers.test.sh`
Input-type: spec slice
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> current the hook scripts are not available with codex
> and the claude code now support AGENTS.md file
> let review and checking if we can support user with codex if they want to install our harness-skill

> writing plan to the github first with seperate to each section with detail purpose and target
> after that, start for item 1 first

> approve design
> notes: - to avoid any breaking on main, let create branch call "codex" - all PRs related to it, let open to codex branch

> do for next step after this PR, continue based on it

"This PR" is #259 (item 1, #253). The next step in the #257 plan is item 2, GitHub issue #254
("Codex Phase 6.2: deliver always-on rules via a shared, runtime-neutral AGENTS.md"). Its Target
checklist is the scope of this slug. "Continue based on it" is read as: branch from
`feat/gh-253-codex-full-payload` (item 2 depends on item 1) and open the PR against `codex`.

## What changed

<pending>

### Rationale

<pending>

### Alternatives considered

- none

### Deviations

- none

### Task review log

- Task 1.1 (`8048501`): spec pass, quality approved. Minor findings (forwarded to final review):
  M1 install suite and deployed pointer are inconsistent until Task 2.1 lands (by plan);
  M2 the marker check does not cover the preamble; M3 unclosed rule frontmatter inlines an empty
  body silently, and an inline `paths: [..]` yields no globs; M4 the preamble read is not wrapped
  in `AdapterError`; M5 the stale-block test's `pytest.raises` has no `match=`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| plan contract | `python3 scripts/check_plan_contract.py specs/gh-254-codex-agents-md-rules/PLAN.md` | 0 | planning-stage row; implementation rows added per task |  |

### Not auto-verified

- Codex 0.147.0 truncates the root→cwd `AGENTS.md` chain at the byte once 32 KiB is reached — reached provenance (read from `codex-rs/core/src/agents_md.rs` at tag `rust-v0.147.0`); not observed in a live run because no `codex` binary is available on this host.

### Rollback

- Code: `git revert` the branch's commits (or close the PR unmerged; nothing reaches `codex` until merge).
- Consumers: re-run `bash scripts/install-codex-harness.sh --source <pre-#254 checkout>`; the managed block's hash matches the rendered block, so it is replaced by the one-line pointer and `.codex/harness-instructions.md` is re-created. An edited block is kept with an `AGENTS.md.harness-incoming` sidecar.

### Harness-Delta

- none
