# decouple-mcp-dependencies — Research Brief

Written 2026-10-14. Pins: repo 23b5876; Claude Code 2.1.299; docs code.claude.com/docs/en/mcp and /memory read 2026-10-14

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing — pure removal plus doc rewording; the only new content is a README section that points at Claude Code's built-in local MCP scope and `CLAUDE.local.md` |
| **Why this is the lightest credible path** | Every coupling point is a deletable block or a string; Claude Code already provides private per-project MCP config (local scope) and private instructions (`CLAUDE.local.md`), so nothing needs building |
| **Confidence** | 85% |
| **Next step** | The user decides what happens to open PR #279 (it does the opposite of this change); then `writing-plans` |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Meta-repo: prompt-based skill framework + bash hooks/installers + Python scripts |
| Primary language + runtime | Bash, Python 3 (stdlib), Markdown/JSON |
| Frameworks / platforms | Claude Code 2.1.299 (primary runtime); Codex advisory alpha adapter |
| Relevant packages | `jq` (installer), `uv`/`uvx` (only consumer is the code-review-graph launch being removed) |
| Detectable versions | no package manifest; `.mcp.json` is the only dependency-like file |
| Important constraints | Installer never deletes/overwrites consumer files (`install-harness.sh:7-10`); `bash scripts/run-tests.sh` + doc-truth lint before changing `scripts/`; `scripts/ci-strict-gate.sh` warn tier for `scripts/` diffs; PR base `sdlc` |

---

## Feature Understanding and Assumptions

- **Requested feature:** remove code-review-graph and context7 from the harness workflow; users install them and write their own `CLAUDE.md` instructions; README explains how to add both back locally.
- **What success appears to mean:** design SC-1…SC-6 (no `.mcp.json` from install; existing one byte-identical; no MCP on `test-runner`; zero-match reference sweep; README section; suite green).
- **Assumptions from the request:** the approved design's D1–D5.
- **Assumptions still needing confirmation:** what to do with PR #279 (see Risks).

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/install-harness.sh:126-131,184-219,359-360` hold all uvx/`.mcp.json` logic; `BACKUP_DIR` is used only inside that block (grep, 2026-10-14) |
| `Local` | Hooks and gates never read `.mcp.json` or MCP tool names: `grep -rn -i mcp hooks scripts/*.sh scripts/*.py rules templates` hits only installer, deploy:645, a lint-doc-truth comment, and the agent renderer |
| `Local` | `scripts/run_test_runner_eval.py:78-80` already runs `test-runner` evals with `--strict-mcp-config` and `TOOLS="Bash,Read,Glob,Grep"` — the eval baseline is MCP-free, so removing context7 from the role cannot regress the measured eval setup |
| `Local` | `render_plan.py --review` renders agent-written JSON; no network/MCP call (`render_plan.py:1298-1405`) |
| `Local` | Open PR #279 `feat(install): auto-install uv and pre-fetch code-review-graph, with --no-uv opt-out`, base `main`, branch `feat/install-uv-autoinstall` (worktree `.worktrees/feat/install-uv-autoinstall`), 14 files / +859 lines incl. 142 lines in `tests/scripts/install-harness.test.sh` (`gh pr list`, `git diff --stat`, 2026-10-14) |
| `Local` | KB precedent `docs/solutions/harness/techstacks-project-owned-stack-profiles.md`: "agnostic core", installer inherits no stack baggage — same principle applied to tools |
| `Local` | `docs/solutions/critical-patterns.md:17` and `harness-bootstrap/meta-repo-signal-remapping.md:29` name `.mcp.json` as current state |
| `Docs` | MCP scopes: Local (default) → `~/.claude.json` under the project path, private; Project → `.mcp.json`, shared; User → `~/.claude.json`, all projects. Precedence Local > Project > User > plugin > claude.ai connectors; whole entry from the winning source (code.claude.com/docs/en/mcp, 2026-10-14) |
| `Docs` | `./CLAUDE.local.md` is a supported "Local instructions" file, loaded at launch alongside `CLAUDE.md` and appended after it (code.claude.com/docs/en/memory, 2026-10-14) |
| `Docs` | Caveat: "a gitignored `CLAUDE.local.md` only exists in the worktree where you created it. To share personal instructions across worktrees, import a file from your home directory instead" (`@~/.claude/<file>.md`; external imports need a one-time approval). User-level `~/.claude/CLAUDE.md` loads without that dialog (same page) |
| `Docs` | Caveat: a `CLAUDE.local.md` counts as a CLAUDE file, so in a repo relying on `AGENTS.md` it stops Claude reading `AGENTS.md` unless "Project instructions" is `claude-md-and-agents-md` (same page). This repo has a `CLAUDE.md`, so no effect here; consumers may differ |
| `Inference` | The docs do not say whether a local-scope MCP server (keyed by project path) applies when Claude Code is launched from inside a linked worktree at a different path; `~/.claude.json` here has keys only for the two main checkout paths |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** as enumerated in design.md "Current state" (reviewer-verified line pointers), plus `tests/scripts/deploy-profile.test.sh:108` (asserts no `.mcp.json` from deploy — still valid, no change).
- **Existing abstractions or extension points:** agent capability vocabulary already has the target values — Claude `"no MCP tools allowed"` and Codex `"disabled"` (`agents/runtime-bindings.json`, reviewer roles); renderer policy `none` emits `mcp_servers = {}` (`render_agent_definitions.py:324-325`).
- **Conventions worth preserving:** installer never touches a consumer file it did not create; tests invert behavior rather than delete coverage; doc-truth lint treats docs as checked artifacts.
- **What can likely be reused:** existing installer test harness (`assert_rc_contains`, temp targets) for the byte-identical `cmp` cases; reviewer-role renderer assertions as the model for `test-runner`.
- **What appears missing locally:** nothing needed; no Codex-side generated file is tracked for `test-runner` (renderer emits at install time).

---

## Upstream Findings

- **Repositories inspected:** none — no upstream repository search was run for this removal (see Evidence Boundary).
- **Pattern or capability already present upstream:** Claude Code itself separates shared (project/`.mcp.json`) from private (local, user) MCP config; the design moves the harness from shipping the shared form to documenting the private form.
- **Files, modules, or areas worth modeling:** none.
- **How closely the upstream pattern matches this repo:** direct match — the docs' local scope is exactly "only you, this project".
- **Any upstream gaps or uncertainties:** worktree behavior of local scope (Inference row).

---

## Docs Findings

- **Official sources checked:** code.claude.com/docs/en/mcp, code.claude.com/docs/en/memory.
- **Version-matched vs latest-stable status:** pages read 2026-10-14 (latest); installed CLI 2.1.299; `claude mcp add --help` observed locally agrees (`-s, --scope … (default: "local")`).
- **Built-in capabilities that already support the feature:** local MCP scope; `CLAUDE.local.md`; `@~/...` imports; user-level `~/.claude/CLAUDE.md`.
- **Current recommended APIs or workflows:** `claude mcp add [--scope local|user|project] <name> -- <command> [args...]`; `/mcp` and `/memory` to confirm what loaded.
- **Important caveats, deprecations, or migration notes:** `CLAUDE.local.md` is per-worktree — this harness runs implementation in worktrees (`.claude/worktrees/` or `.worktrees/`), so the README should recommend the `@~/.claude/<file>.md` import (or user-level `~/.claude/CLAUDE.md`) for notes that must follow into worktrees. No deprecation of `CLAUDE.local.md` found.

---

## Recommendation

- **Primary recommendation:** reuse existing — implement design D1–D5 as removals and rewording; README points at the built-in local scope and private-instruction files.
- **Why this is the lightest credible path:** all coupling is local and enumerated; the platform already provides the private-config mechanisms the README needs.
- **Why the next-best alternative lost:** an installer opt-in flag (`--with-mcp`) keeps MCP knowledge inside the harness — the thing the request removes (design Non-goals).
- **What would change this recommendation:** a decision to keep PR #279 and merge it — then this change must also remove its uv auto-install/pre-fetch code, a larger diff.

### Design refinements (no decision change)

- README personal-instructions guidance should lead with the worktree caveat: `CLAUDE.local.md` works in the checkout where it was created; for worktrees use an `@~/.claude/<file>.md` import or `~/.claude/CLAUDE.md`. This tightens design A4 (now provenance: Docs) without changing D1–D5.
- README MCP guidance should add: if a session is launched from inside a worktree and `/mcp` does not show the local-scope server, add it with `--scope user` instead.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - PR #279 conflicts directly: it edits the same installer region and `install-harness.test.sh` (+142 lines) to *auto-install* uv for code-review-graph. Whichever lands second on `main` reintroduces or breaks the other. This branch targets `sdlc`, #279 targets `main`, so the clash surfaces at the sdlc→main merge.
  - `scripts/` diff triggers `ci-strict-gate.sh` warn tier; `skills/visual-planner/render_plan.py` is high-blast (block tier) — the change needs a high-risk SUMMARY with re-runnable `### Verify` rows.
  - Removing `context7-read-only` from `CODEX_MCP_POLICIES` makes any external contract still using it fail render ("unmapped mcp policy") — intended (design Error behavior).
- **Evidence gaps:** local-scope MCP behavior in linked worktrees is undocumented; no upstream repositories searched.
- **Version uncertainties:** docs are latest, CLI is 2.1.299; the `CLAUDE.local.md` behavior was not exercised locally.
- **Follow-up questions for the user:** Should PR #279 be closed (recommended — it contradicts the approved intent), or kept and its uv logic removed by this change?

---

## Source Pack

- **Local files read:** `scripts/install-harness.sh`, `scripts/deploy-harness.sh`, `scripts/render_agent_definitions.py`, `scripts/run_test_runner_eval.py`, `agents/runtime-bindings.json`, `agents/agent-contracts.json`, `agents/test-runner.md`, `skills/visual-planner/SKILL.md`, `skills/visual-planner/references/review-sidecar.md`, `skills/visual-planner/render_plan.py`, `skills/README.md`, `skills/using-git-worktrees/SKILL.md`, `CLAUDE.md`, `README.md`, `.mcp.json`, `.gitignore`, `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness-bootstrap/meta-repo-signal-remapping.md`, `specs/mcp-install-wiring/SUMMARY.md`, `tests/scripts/install-harness.test.sh`
- **Upstream repositories or pages checked:** none searched (gap recorded in Evidence Boundary)
- **Official docs domains or pages checked:** https://code.claude.com/docs/en/mcp, https://code.claude.com/docs/en/memory

---

## Evidence Boundary

> Confirmed from artifacts: every coupling point and line range; no hook/gate reads MCP config; test-runner eval already MCP-free; PR #279 open against main with overlapping files; local MCP scope semantics and `CLAUDE.local.md` support with its worktree caveat (official docs); CLI flag `--scope` default local (`--help`).
> Inferred from patterns: local-scope MCP may not apply in a session launched inside a worktree path.
> Not checked: upstream repositories (removal of an internal coupling has little upstream analogue; recorded as a gap, not "none found"); `CLAUDE.local.md` loading exercised on this machine; README commands executed (no `uv` installed).
