# Intent: Make MCP servers optional, external add-ons

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

The harness workflow is tied to two MCP servers. `code-review-graph` is wired into the root
`.mcp.json`, merged into every consumer's `.mcp.json` by `scripts/install-harness.sh` (with a
`uvx` warning), checked by `scripts/deploy-harness.sh`, named in `visual-planner`'s
`allowed-tools`, and documented in `CLAUDE.md` with an instruction to use it for structural
questions. `context7` is bound to the `test-runner` agent (`agents/runtime-bindings.json`,
`agents/agent-contracts.json`, and the Codex `context7-read-only` MCP policy). A user who has not
installed these servers gets confusing instructions, or failed connections such as
`code-review-graph (ENOENT): Executable not found in $PATH: uvx`.

## Proposed outcome

The harness requires no MCP server or plugin. Installing or updating it never creates or edits
`.mcp.json`. No skill, agent, rule, or `CLAUDE.md` instruction refers to `code-review-graph` or
`context7` by name. Users who want an MCP server install it themselves and add their own
`CLAUDE.md` instructions.

The README documents how to add both servers back for local use only, without touching tracked
files: `claude mcp add --scope local code-review-graph -- uvx code-review-graph serve` (needs
`uv`), `.code-review-graph/` in `.git/info/exclude`, context7 from the user's own user-level or
plugin config, and personal instructions in an untracked `CLAUDE.local.md`.

## Affected users and systems

- Consumer projects that run `install-harness.sh` / `deploy-harness.sh`.
- This repo: `.mcp.json`, `.gitignore`, `CLAUDE.md`, `README.md`, `skills/README.md`,
  `skills/visual-planner/` (SKILL.md, render_plan.py comments), `agents/agent-contracts.json`,
  `agents/runtime-bindings.json`, `scripts/render_agent_definitions.py`, and their tests
  (`tests/scripts/install-harness.test.sh`, `scripts/test_render_*.py`).

## Constraints

- The installer must not delete or rewrite a consumer's existing `.mcp.json`, including a
  `code-review-graph` entry an earlier install added; it simply stops touching the file. (assumed)
- `bash scripts/run-tests.sh` (including the doc-truth lint) must pass.
- `visual-planner --review` stays available as an optional mode: it renders a
  `.plan-review.json` sidecar the agent fills from any evidence source (an MCP graph if the user
  has one, otherwise Grep/Read). Only the hard-wired `code-review-graph` tool names and wording are
  removed. (assumed)
- `test-runner` loses its context7 tools; its MCP policy becomes `none`. The Codex
  `context7-read-only` policy is removed from the renderer. (assumed)
- The `CLAUDE.md` "Boundary of trust" rule is kept, generalized to any MCP output, because users
  may still add servers. (assumed)

## Out of scope

- Removing the user-level `context7` configuration on anyone's machine.
- Rewriting historical records: `specs/*` of shipped work, `docs/research/`, eval raw results.
- Changing a consumer's existing `.mcp.json`.

## Open questions

- Should this repo's own root `.mcp.json` be deleted, or kept for the maintainer's local use
  while the installer stops copying it? Default proposed: delete it and drop the
  `.code-review-graph/` line from `.gitignore`. (assumed)
- none beyond the `.mcp.json` question above; the README note is now required (see Proposed
  outcome).

## What success looks like

- `grep -rn -e code-review-graph -e context7` over `skills/ agents/ rules/ hooks/ scripts/
  templates/ CLAUDE.md` returns nothing except the generalized trust note, if it names examples.
- A fresh `install-harness.sh` into an empty directory creates no `.mcp.json`.
- `bash scripts/run-tests.sh` passes.
- README has an optional-MCP section with the local-only setup for code-review-graph and
  context7.

## Original request

i want to remove the current mcp "code-review-graph" and "context7" in the current workflow. The user need to install it manually by themself and update instructions to claude.md by themself.
because i dont want current harness workflow stick with any mcp or plugin, it will make the user confuse or even error if they dont install them.
mcp/plugins should be the external, not required.

- approved for intent
- add notes how to configration back for code-review-graph and context7.
