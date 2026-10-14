# decouple-mcp-dependencies — Design

Written 2026-10-14. Pins: repo e32350e (branch `refactor/decouple-mcp-dependencies`, cut from `sdlc` 199914c); Claude Code 2.1.299 (`claude mcp add` interface)

## Goal

The harness requires no MCP server or plugin. The installer stops creating or merging
`.mcp.json`, no skill, agent, rule or `CLAUDE.md` instruction names `code-review-graph` or
`context7`, and the README shows a user how to add both back for local use only.

## Current state

- `.mcp.json` (repo root) declares `code-review-graph` via `uvx code-review-graph serve`;
  `.gitignore:34-35` ignores `.code-review-graph/`.
- `scripts/install-harness.sh`: a `uvx` prerequisite warning (lines 126–131) and closing reminder
  (359–360); an `.mcp.json` wiring block (184–219) that creates the file or jq-merges the
  `code-review-graph` entry, with a `.harness-backup-*/.mcp.json` copy on merge; header comment
  line 8 and validation comment line 108 describe this.
- `scripts/deploy-harness.sh:645` warns when the repo root has no `.mcp.json`.
- `agents/runtime-bindings.json`: Claude `test-runner` tools include
  `mcp__context7__resolve-library-id` and `mcp__context7__query-docs`; capability `mcp` is
  "context7 read-only tools only" (Claude) and "inherit configured context7 server; enable
  context7 only" (Codex). `agents/agent-contracts.json`: `test-runner.mcp = "context7-read-only"`.
- `scripts/render_agent_definitions.py:19` lists `context7-read-only` in `CODEX_MCP_POLICIES`
  and lines 329–330 emit `[mcp_servers.context7] enabled = true`. Tests assert this in
  `scripts/test_render_agent_definitions.py:35-36,177` and `scripts/test_render_codex_adapter.py:126`.
- `skills/visual-planner/SKILL.md` frontmatter `allowed-tools` lists four
  `mcp__code-review-graph__*` tools and the body says "graph-backed plan review";
  `references/review-sidecar.md` and `render_plan.py` (comment at 1298–1299, docstring at 1401,
  user-visible warning at 1390 "not found in the graph") assume a graph source.
  `skills/README.md:312-319` mermaid step 2 says "agent queries code-review-graph".
- `CLAUDE.md`: a Gotchas bullet (line 87) describes `.mcp.json`; a section
  "MCP Tools: code-review-graph" (lines 96–110) instructs agents to use the graph; "Boundary of
  trust" (112–114) names both servers.
- `README.md:87,89,108-118` describe the installer wiring `.mcp.json`, recommend `uv`, and
  document the servers.
- `docs/solutions/harness-bootstrap/meta-repo-signal-remapping.md:29` states `.mcp.json` is the
  only dependency-like file; `docs/solutions/critical-patterns.md:17` (injected into every session
  by `session-knowledge.sh`) lists `.mcp.json` among the harness's high-blast files.
- `tests/scripts/install-harness.test.sh:19,25-33,94-107` assert the old wiring: dry-run
  "would create  .mcp.json", fresh install wires `code-review-graph`, merge yields keys
  `code-review-graph,context7` with a backup, and "already wires code-review-graph".
- `.claude/agents/test-runner.md` (gitignored deployed copy) lists the context7 tools.
- Live symptom in this session: `code-review-graph (ENOENT): Executable not found in $PATH: uvx`.

## Approaches considered

1. **Remove MCP wiring; keep `visual-planner --review` with a source-agnostic sidecar; set
   `test-runner` MCP to `none`.** Chosen — matches the approved intent, keeps a working renderer
   and its tests, and leaves no agent whose tool set depends on per-machine config.
2. **Also remove `visual-planner --review`.** Rejected — only its data source was MCP-bound; the
   sidecar renderer is offline and deterministic already.
3. **`test-runner` MCP `runtime-controlled`** (inherit whatever the user configured). Rejected —
   re-introduces machine-dependent agent capability, the thing the change removes.

## Architecture

MCP configuration is owned by the user, at local or user scope. The harness ships none and asks
for none.

| Area | Change |
|---|---|
| Installer | Delete the `uvx` check + reminder and the `.mcp.json` block (with its `BACKUP_DIR`); update header/validation comments. The installer never reads or writes `.mcp.json`. |
| Deploy | Remove the missing-`.mcp.json` warning. |
| Repo config | Delete `.mcp.json`; remove the `.code-review-graph/` lines from `.gitignore`. |
| Agents | `test-runner`: drop the two context7 tools; Claude `mcp` capability "no MCP tools allowed", Codex "disabled"; contract `mcp: none`. Renderer: remove `context7-read-only` policy and its emission branch. |
| visual-planner | Drop the four MCP tools from `allowed-tools`. Reword every graph-as-required-source string: SKILL.md description "optional graph-derived risk", body "graph-backed plan review", "gather graph evidence", "New/missing graph nodes"; `references/review-sidecar.md:4-5` "The graph informs the sidecar … unknown graph coverage remains unknown"; `render_plan.py:1298-1299` comment, `:1390` warning "not found in the graph", `:1401` docstring (no logic change); `skills/README.md:317` mermaid step 2. A graph tool may be named only as one optional evidence source among Grep/Read, generically and never by server name (SC-4). |
| Docs | `CLAUDE.md`: delete the MCP Tools section and the `.mcp.json` Gotcha; keep Boundary of trust generalized to any MCP server the user adds, naming no server. `README.md`: replace "MCP servers" with "Optional MCP servers (local setup)"; line 87 says the installer touches only the structural dirs at the root (one thing, not two); line 89 drops the `uv` recommendation. KB: `meta-repo-signal-remapping.md:29` and `critical-patterns.md:17` updated to current state (no `.mcp.json`). |
| Deployed copy | After the source changes, re-run `bash scripts/deploy-harness.sh` so this repo's `.claude/` (including `agents/test-runner.md`) drops the MCP tools. |

README local-setup section content:

- code-review-graph: install `uv`, then from the project root
  `claude mcp add --scope local code-review-graph -- uvx code-review-graph serve`
  (local scope stores it in the user's `~/.claude.json` under this project, not in the repo);
  add `.code-review-graph/` to `.git/info/exclude`.
- context7: configure it at user scope or install it as a plugin in the user's own Claude Code
  config; the harness agents do not use it.
- Personal instructions: an untracked `CLAUDE.local.md` at the project root (excluded via
  `.git/info/exclude`); confirm it loads with `/memory`. If it does not load, put the notes in the
  user-level `~/.claude/CLAUDE.md` (always loaded, never in the repo), scoped with a heading that
  names the project.

## Error behavior

- A consumer with an existing `.mcp.json` (including a `code-review-graph` entry from an earlier
  install, other servers, or invalid JSON): left byte-identical; no backup written; no message.
- A machine without `uv`: the installer no longer warns; nothing in the harness launches `uvx`.
- Re-sync on an older consumer: deployed skills lose the MCP tool names; the old `.mcp.json`
  entry still works on its own if `uv` is present.
- Codex adapter: the `test-runner` profile renders `mcp_servers = {}`; a contract that still says
  `context7-read-only` fails render with "unmapped mcp policy".

## Tests

- `tests/scripts/install-harness.test.sh` (truth tier — the installer is re-run): the old
  wiring assertions (lines 19, 25–33, 94–107) are inverted, not deleted:
  fresh install creates no `.mcp.json`; existing `.mcp.json` with a `code-review-graph` entry,
  with only other servers, and with invalid JSON each stay byte-identical (`cmp`); no
  `.harness-backup-*/.mcp.json`; neither dry-run nor real-run output contains a `.mcp.json` line.
- `scripts/test_render_agent_definitions.py`, `scripts/test_render_codex_adapter.py` (truth):
  `test_runner["mcp_servers"] == {}`; the former policy is rejected as unmapped (the test builds
  the policy string from parts so the literal name does not appear); Claude `test-runner` tools
  contain no `mcp__` entry.
- Reference sweep (traceability):
  `grep -rn -e code-review-graph -e context7 skills agents rules hooks scripts templates CLAUDE.md`.
- `bash scripts/run-tests.sh` including the doc-truth lint (truth).

## Success criteria

- SC-1: fresh install into an empty directory leaves no `.mcp.json` — installer test case.
- SC-2: an existing consumer `.mcp.json` is byte-identical after install, in all three fixtures — installer test cases.
- SC-3: rendered Codex and Claude `test-runner` definitions carry no MCP server or `mcp__` tool — renderer tests.
- SC-4: the reference sweep above prints no lines (exit 1) — the grep. The generalized Boundary-of-trust note names no server (D5).
- SC-5: README contains an "Optional MCP servers" section with the `claude mcp add --scope local code-review-graph` command and context7 guidance — `grep -n` on README.
- SC-6: `bash scripts/run-tests.sh` exits 0.

## Non-goals

- Editing or deleting anyone's `.mcp.json`, user-level context7 config, or plugins.
- Rewriting historical records: shipped `specs/*`, `docs/research/`,
  `docs/harness-gap-closure-plan.md`, eval raw results.
- Adding an installer flag or prompt to opt back into MCP wiring.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | No hook or gate reads `.mcp.json` or the context7/graph tool names, so removing them breaks no gate | provenance: Local, 2026-10-14, `grep -rn -i mcp hooks scripts/*.sh scripts/*.py rules templates` (hits only installer, deploy, lint-doc-truth comment, renderer) | SC-6 | A gate fails in CI; patch that gate in this change |
| A2 | `visual-planner --review` rendering does not depend on the graph beyond prose — the sidecar is agent-written JSON | provenance: Local, 2026-10-14, `render_plan.py:1298-1405` | SC-6 (renderer unit tests) | Rendering changes; keep the wording change only and stop to re-scope |
| A3 | `claude mcp add` accepts `--scope local` and defaults to local | provenance: Local, 2026-10-14, `claude mcp add --help` | SC-5 (doc content) | README command is wrong; correct it from `--help` |
| A4 | `CLAUDE.local.md` is loaded by the user's Claude Code version | none yet — Inference: Claude Code memory docs as recalled, 2026-10-14, not re-read | accepted risk: README tells the user to confirm with `/memory` | User's notes are not loaded; README fallback is the user-level `~/.claude/CLAUDE.md` |
| A5 | Codex renderer accepts `none` for `test-runner` (already used by reviewer roles) | provenance: Local, 2026-10-14, `render_agent_definitions.py:324-325` | SC-3 | Renderer rejects; add `none` handling for that role |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| Consumers who already have `code-review-graph` in `.mcp.json` get it removed | Deliberately untouched — the installer never deletes consumer files |
| The README local setup is verified end-to-end on the user's machine | `uv` is not installed here; the commands are checked against `--help`, not run |
| Agents still produce graph-quality blast-radius evidence without the server | Without a graph, review evidence comes from Grep/Read; quality is the agent's, not a tool's |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | The installer never reads or writes `.mcp.json` | Old consumer entries persist; no backup or merge logic remains | settled |
| D2 | Keep `visual-planner --review`; its sidecar is source-agnostic | Prose and `allowed-tools` change; renderer logic does not | settled |
| D3 | `test-runner` MCP policy is `none`; `context7-read-only` is removed from the renderer | Codex `test-runner` gets `mcp_servers = {}`; Claude tools lose context7 | settled |
| D4 | Delete this repo's `.mcp.json` and its `.gitignore` lines | Maintainer re-adds the server at local scope per README | settled |
| D5 | Keep "Boundary of trust" in `CLAUDE.md`, generalized to any MCP server and naming none | Untrusted-input rule survives for user-added servers; SC-4 expects zero matches | settled |
