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

The harness no longer requires or wires any MCP server. `install-harness.sh` stops creating,
merging or backing up `.mcp.json` and stops checking for `uvx`; `deploy-harness.sh` drops its
`.mcp.json` warning; the repo's own `.mcp.json` and `.code-review-graph/` ignore lines are gone.
`test-runner` loses its context7 tools (MCP policy `none`) and the Codex renderer drops the
`context7-read-only` policy. `visual-planner --review` stays, with evidence gathered by Grep/Read
or any graph tool the user installs. `CLAUDE.md` loses its code-review-graph instructions and keeps
a server-neutral "Boundary of trust". README gains "Optional MCP servers (local setup)" showing how
to add code-review-graph (local scope, worktree-safe exclude), context7, and personal instructions
(`CLAUDE.local.md`, or a home-directory import for worktrees).

### Rationale

Users without the servers got failed connections (`uvx` ENOENT) and instructions pointing at
tools they never installed; Claude Code already provides private per-project MCP config (local
scope) and private instructions (`CLAUDE.local.md`), so the harness only needs to document them.
The installer leaves existing consumer `.mcp.json` files untouched, so nothing downstream breaks.

### Alternatives considered

- Remove `visual-planner --review` entirely — rejected: only its data source was MCP-bound; the renderer is offline already (design D2).
- `test-runner` MCP `runtime-controlled` (inherit the user's servers) — rejected: keeps agent capability machine-dependent (D3).
- An installer opt-in flag for MCP wiring — rejected: keeps MCP knowledge inside the harness, the thing the request removes.

### Deviations

- Rule 2 — `scripts/test_render_agent_definitions.py`: the Claude `test-runner` tools assertion was a substring check that still passed with the context7 tools present; anchored to the whole `tools:` line, which fails against the old bindings. Commit `1ce515c`.

### Minor findings (task review, non-blocking)

- 1.1 — `tests/scripts/install-harness.test.sh`: the real-run fresh-install case checks `$OUT` for `.mcp.json` but not for `uvx` (the dry-run case covers `uvx`). checked_against SC-1.
- 1.1 — `scripts/install-harness.sh`: the reworded header comment line is longer than its neighbours (cosmetic).
- 1.4 — `README.md`: `echo ".code-review-graph/" >> .git/info/exclude` fails inside a linked worktree, where `.git` is a file; use `"$(git rev-parse --git-common-dir)/info/exclude"` or say "main checkout". checked_against SC-5.

### Context-Propagation Audit

Diff `2d211e6..1c44b7c` plus the audit repair below. Consumer search surface:
`grep -rIn -i -e graph-derived -e graph-backed -e "graph overlay" -e "boundary of trust" -e "MCP Tools" -e "knowledge graph"` and
`grep -rIln -e visual-planner -e review-sidecar` over `skills agents rules templates hooks scripts CLAUDE.md README.md HARNESS.md adapters`;
`grep -rIn graph-derived tests evals/skills skills`. The code-review-graph MCP server was not connected (and is what this change removes), so consumers come from Grep only.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `skills/visual-planner/SKILL.md` allowed-tools + overlay wording | main session running `visual-planner` | main | skill body loaded on invocation | inspected: SKILL.md frontmatter `Bash, Read, Glob, Write`; deployed copy refreshed by Task 2.1 redeploy |
| `skills/visual-planner/references/review-sidecar.md` | `visual-planner` overlay step | main | explicit reference listed in SKILL.md `## References` | inspected SKILL.md references section |
| visual-planner overlay concept ("review-derived") | `skills/writing-plans/SKILL.md:40` | main (planning) | skill body loaded on invocation | **FAIL → repaired**: said "graph-derived overlay"; now "review-derived overlay" |
| visual-planner overlay concept | `skills/visual-planner/template.html:286` | none (CSS comment in rendered HTML) | n/a | repaired for consistency; `test_render_plan.py` 82 passed |
| `agents/runtime-bindings.json` / `agent-contracts.json` test-runner `mcp` | rendered `test-runner` agent (Claude frontmatter, Codex TOML) | test-runner subagent | renderer at deploy/install | SC-3 pytest 26 passed; SC-9 `grep -c mcp__ .claude/agents/test-runner.md` → 0 |
| test-runner tool set | `skills/subagent-driven-development/SKILL.md:61` (`test-runner retry`) | controller | skill body | inspected: references the role, not its MCP tools — unaffected |
| `CLAUDE.md` MCP Tools section removed; Boundary of trust generalized | main session | main | always-loaded project CLAUDE.md | inspected CLAUDE.md:95; not deployed to consumers (installer ships `.claude/` only) |
| `rules/behavior.md` §1 (cited by Boundary of trust) | reviewer agents | reviewer, scorer | `.claude/rules/` always-on | unchanged by this diff |

Result: **PASS** after one repair (writing-plans wording + template comment).

### Correctness Review

Range `2d211e6..0ddca5d` (package `.harness-state/sdd/package-branch.md`), six FIND angles, four deduplicated locations, one independent scorer each (threshold 75).

- **Fixed** — `README.md:116` (score 75): the README exclude command `>> .git/info/exclude` failed in a linked worktree, where `.git` is a file. Now uses `"$(git rev-parse --git-common-dir)/info/exclude"` for both `.code-review-graph/` and `CLAUDE.local.md`. Commit `24aadd9`; re-scored in fix round 1.

Re-review of the advisory fixes (`37f2c17..968b9a2`, six angles): one deduplicated location,
`scripts/render_agent_definitions.py:157-160` (score 50) — the new guard accepted an empty list,
non-string entries and a comma-joined entry (`"Read, mcp__x"`), which render as a bare `tools:`, a
`TypeError`, or an MCP grant. Fixed anyway because it sat in the advisory fix itself: the guard now
requires a non-empty list of plain tool names; 5 parametrized cases added.

### Advisory Findings

The user asked on 2026-10-14 to fix the first three advisories ("fix the 3 advisory findings too"); all three are fixed in `968b9a2`.

- **Fixed** — `skills/visual-planner/SKILL.md:4` (score 50) — `allowed-tools` omitted `Grep`, which the body names. Now `Bash, Read, Grep, Glob, Write`.
- **Fixed** — `tests/scripts/install-harness.test.sh:10` (score 0, pre-existing) — `target()` appended to `_CLEANUP_DIRS` inside `$(...)`, a subshell, so every target dir leaked. `target()` now sets `TARGET` in the calling shell. Measured with a private `TMPDIR`: 16 dirs left after a run before the fix, 2 after. The remaining 2 are empty dirs created by the scripts under test, not by the helper; their source is not pinned (searched `mktemp` in `tests/lib.sh`, `scripts/install-harness.sh`, `scripts/deploy-harness.sh`).
- **Fixed** — `scripts/render_agent_definitions.py` (score 0, unmodified-line) — `validate()` now rejects any role whose contract is `mcp: none` unless its Claude binding has an explicit `tools` list with no `mcp__` entry (a missing list inherits every tool). Tests: `test_mcp_tool_on_mcp_none_role_is_rejected[reviewer|task-reviewer|test-runner]` and `test_missing_tools_list_on_mcp_none_role_is_rejected`, which failed before the fix and pass after.
- Existing checkouts that already hold a `.code-review-graph/` directory lose the tracked ignore rule (design D4); they must run the README exclude command once. Reported with the scored README finding; no separate score.

### Intent Findings

Intent review over `2d211e6..24aadd9`, blind to PLAN.md: every intent clause met, no behaviorally different drift.

- **gap (proof only, accepted)** — design SC-6 / intent constraint "`bash scripts/run-tests.sh` … must pass" has no Verify row. Whole-suite rows are disallowed (`rules/plan-format.md` Guardrail 4); the suite runs at `finishing-a-development-branch`. The intent reviewer ran it independently: exit 0, 906 passed.
- **gap (proof only, accepted)** — PLAN SC-9 names the deployed `.claude/agents/test-runner.md`; the Verify row checks its source `agents/runtime-bindings.json` because `.claude/` is gitignored and absent in CI. The deployed check passed locally (listed under Not auto-verified).
- **drift (equivalent, advisory)** — README adds a `--scope user` fallback for worktree sessions and worktree guidance for personal notes (`@~/.claude/<file>.md`, `~/.claude/CLAUDE.md`); none touches tracked files. Sourced from official docs (research brief); see Intake notes.
- **drift (equivalent, advisory)** — `skills/visual-planner/SKILL.md:4` omits `Grep` from `allowed-tools` while the body names Grep/Read (same as the correctness advisory).
- **excess (report-only)** — `docs/solutions/critical-patterns.md` and `meta-repo-signal-remapping.md` current-state lines updated (planned in design, not named in intent).
- **excess (report-only)** — `skills/writing-plans/SKILL.md:40` "graph-derived" → "review-derived" (context-propagation audit repair).
- **excess (report-only)** — renderer test hardening: whole-line `tools:` assertion and a new former-policy-rejected test.
- **excess (report-only)** — installer tests assert no invalid-JSON warning and no `uvx` mention (stricter negative assertions).

Intent review of the advisory fixes (`37f2c17..e591f73`, oracle: "fix the 3 advisory findings too"): all three fixed, no gap or drift.

- **excess (report-only, accepted)** — the `mcp: none` guard also requires a non-empty list of plain tool names (`[A-Za-z][A-Za-z0-9_-]*`), not only "no `mcp__` entry and no missing list". The empty-list and comma-joined cases close bypasses of the requested check; the plain-name rule is a new restriction on how tool names may be written for `mcp: none` roles. All current bindings satisfy it.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Intent pin matches committed intent.md | `git diff --exit-code e32350e -- specs/decouple-mcp-dependencies/intent.md` | 0 | intake-time check | |
| Installer: fresh install writes no .mcp.json; dry/real output names neither .mcp.json nor uvx | `bash tests/scripts/install-harness.test.sh` | 0 | 12 passed | SC-1 |
| Installer: existing .mcp.json (other servers, code-review-graph entry, invalid JSON) byte-identical, no backup | `bash tests/scripts/install-harness.test.sh` | 0 | cmp-based cases in the same suite | SC-2 |
| Renderer: test-runner has no MCP server or mcp__ tool; former policy rejected | `python3 -m pytest scripts/test_render_agent_definitions.py scripts/test_render_codex_adapter.py -q` | 0 | 26 passed | SC-3 |
| No live harness file names either server | `grep -rIn -e code-review-graph -e context7 skills agents rules hooks scripts templates CLAUDE.md` | 1 | no matches | SC-4 |
| README has the local-setup section, command and CLAUDE.local.md guidance | `grep -q "Optional MCP servers (local setup)" README.md && grep -q "claude mcp add --scope local code-review-graph" README.md && grep -q "CLAUDE.local.md" README.md` | 0 | | SC-5 |
| visual-planner renderer unchanged by rewording | `python3 -m pytest skills/visual-planner/test_render_plan.py -q` | 0 | 82 passed | SC-6 |
| Doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | | SC-7 |
| Repo ships no root .mcp.json | `test ! -e .mcp.json` | 0 | | SC-8 |
| test-runner binding (source of the deployed agent) lists no mcp__ tool | `grep -c mcp__ agents/runtime-bindings.json` | 1 | prints 0; the deployed `.claude/agents/test-runner.md` check is local-only (see Not auto-verified) | SC-9 |
| No hook reads .mcp.json or an MCP tool name | `grep -rIn -e "\.mcp\.json" -e mcp__ hooks` | 1 | no matches | SC-10 |
| Renderer rejects mcp__ tools or a missing tools list on an mcp-none role (advisory fix) | `python3 -m pytest scripts/test_render_agent_definitions.py -q -k mcp_none` | 0 | 9 passed (incl. empty, non-string and comma-joined lists) | |
| visual-planner pre-approves Grep (advisory fix) | `grep -q "^allowed-tools: .*Grep" skills/visual-planner/SKILL.md` | 0 | | |

### Not auto-verified

- This repo's deployed `.claude/agents/test-runner.md` has no `mcp__` tool — reached truth locally (`grep -c mcp__ .claude/agents/test-runner.md` printed 0 after redeploy, Task 2.1); not a Verify row because `.claude/` is gitignored and absent in CI.
- README local-setup commands (`claude mcp add --scope local …`, `uvx code-review-graph serve`) work end to end — reached traceability only: checked against `claude mcp add --help` (Claude Code 2.1.299) and official docs; not run because `uv` is not installed here.
- `CLAUDE.local.md` loads in the user's Claude Code — reached provenance (official memory docs, 2026-10-14); not exercised locally.
- Full suite `bash scripts/run-tests.sh` — runs at `finishing-a-development-branch`, not a Verify row (whole-suite rows are disallowed).

### Rollback

- `git revert <sha>` per commit on `refactor/decouple-mcp-dependencies`; consumer `.mcp.json` files are never edited by this change, so there is nothing to restore downstream.

### Harness-Delta

- backlog — the worktree-isolation guard refuses Bash calls whose text names git in a form it cannot verify (a heredoc mentioning `.git/info/exclude`, a script chained with git commands, a python heredoc naming git); implementers and the controller had to split commands or use the Edit tool (Task 1.4, Task 1.1, controller).
