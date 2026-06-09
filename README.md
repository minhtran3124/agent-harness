<div align="center">

# Skill Harness

**A ready-to-use toolkit of skills, agents, hooks, and rules for the [Claude Code](https://claude.com/claude-code) CLI**

*Prompt-powered workflows that carry a change from brainstorm to ship.*

</div>

---

Skills are Markdown prompt programs you summon with `/skill-name`. They chain through defined gates so work flows *discovery → design → planning → execution → review → shipping* — no skipping
steps allowed.

## Installation

### Add to an existing project

One-liner that clones the harness, builds `.claude/`, and leaves your project root clean:

```bash
curl -fsSL "https://raw.githubusercontent.com/minhtran3124/harness-skills/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes
```

Everything the harness needs lives entirely in a gitignored `.claude/` (skills, agents, hooks, rules, templates, settings) — nothing is dropped at your project root. **To update, just re-run the one-liner** (idempotent; existing files are backed up first).

Needs `git` + [jq](https://jqlang.github.io/jq/).
Flags: `--directory <path>` · `--branch <name>` · `--source <local checkout>` · `--keep-sources` · `--dry-run`.

Then **restart Claude Code** so it loads the skills, agents, and hooks.

### Develop on this repo

Working *on the harness itself* keeps the editable source at the repo root and Claude Code loads from a derived, gitignored `.claude/`. Rebuild it with:

```bash
bash scripts/deploy-harness.sh
```

First run installs; any later run updates (idempotent). Re-run after editing anything under `skills/` `agents/` `hooks/` `rules/` `templates/` `settings.json`. (Installing into another project with `--keep-sources` reproduces this same root-source + `.claude/` layout there.)

### MCP servers

This repo wires the [code-review-graph](https://pypi.org/project/code-review-graph/) MCP server in [mcp.json](mcp.json). It launches through [uv](https://docs.astral.sh/uv/)'s `uvx` runner, so there's **no manual `pip install`** — `uvx` fetches and runs it on demand.
You just need `uv` (which provides `uvx`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # installs uv + uvx
uvx code-review-graph serve                        # exactly what mcp.json invokes
```

The graph data is written to `.code-review-graph/` (gitignored). The `context7` MCP server is configured at the Claude Code **user** level (HTTP, needs `CONTEXT7_API_KEY`) — it is *not* in this repo's `mcp.json`, so each user wires it in their own global config.

## Repository layout

| Path | What it holds |
|---|---|
| `skills/` | The skill library — subdirs with `SKILL.md` + standalone `.md` graph skills. |
| `agents/` | Sub-agent role definitions dispatched by skills. |
| `rules/` | Architecture & process governance read by skills/agents. |
| `hooks/` | Bash automation wired into Claude Code lifecycle events. |
| `agent-memory/` | Per-agent persistent memory with confidence decay. |
| `specs/` | Per-feature work artifacts — one `<slug>/` dir per change (SUMMARY, design, PLAN, …). |
| `templates/` | Canonical shapes copied into `specs/<slug>/` — `SUMMARY`, `TEST_MATRIX`, `ESCALATIONS`. |
| `docs/` · `scripts/` | Reference docs and standalone helpers. |
| `CLAUDE.md` · `settings.json` · `mcp.json` | Project instructions; hooks + env + plugins; MCP server config (`mcpServers` only). |

## The skill workflow

Each step hands off to the next; `/feature-intake` runs first and decides how many steps apply.

```
/feature-intake                  classify risk lane + confidence, route (run first)
        |
/brainstorming                   explore intent & design  (high-risk lane)
        |
/xia2                            research what already exists
        |
/writing-plans                   turn design into tasks
        |
/visual-planner   (auto)         render plan to HTML for review
        |
/using-git-worktrees             isolated branch + worktree
        |
/subagent-driven-development     build it  (or /executing-plans)
        |
/compound                        capture non-obvious learnings
        |
/finishing-a-development-branch  PR, review, merge
```

## Further reading

> **[skills/README.md](skills/README.md)** is the single source of truth — full skill
> inventory, triggers, outputs, handoff map, alternate paths, and per-skill design rationales.
>
> **[HARNESS.md](HARNESS.md)** — how the risk/trust harness shapes the workflow: lanes,
> when a human is asked, and how hooks enforce it. Read this to understand *why* the flow behaves
> the way it does.

## Credits & inspiration

This harness remixes ideas from people who generously shared their agentic-coding playbooks — standing on the shoulders of:

| Source | By | Idea borrowed |
|---|---|---|
| [superpowers](https://github.com/obra/superpowers) | Jesse Vincent ([@obra](https://github.com/obra)) | The skill engine — composable `/skills`, brainstorm-before-code, TDD, a fresh subagent per task, plus hooks & continuous learning. |
| [Get Shit Done (GSD)](https://github.com/gsd-build/get-shit-done) | TÂCHES ([@gsd-build](https://github.com/gsd-build)) | Spec-driven development + treating the context window as a managed resource — atomic plans run in fresh subagent contexts, stitched with git commits. |
| [Compound engineering](https://every.to/guides/compound-engineering) | Kieran Klaassen & [Every](https://every.to) | The *plan → work → review → compound* learning loop — every bug, decision, and insight captured for future agents (our `/compound` + `docs/solutions/`). |
| [harness-experimental](https://github.com/hoangnb24/harness-experimental) | Bang Hoang ([@hoangnb24](https://github.com/hoangnb24)) | The risk/trust harness — lanes, hard gates, and *"ceremony scales with risk; interruption scales with ambiguity."* |

## Author

**Minh Tran** — [@minhtran3124](https://github.com/minhtran3124) · <tranhuuminh3124@gmail.com>

See [`CONTRIBUTORS.md`](CONTRIBUTORS.md) for the full cast and how to join in.
</content>
