<div align="center">

# Skill Harness

**A ready-to-use toolkit of skills, agents, hooks, and rules for the [Claude Code](https://claude.com/claude-code) CLI**

*Prompt-powered workflows that carry a change from brainstorm to ship.*

</div>

---

Skills are Markdown prompt programs you summon with `/skill-name`. They chain through defined gates so work flows *discovery → design → planning → execution → review → shipping* — no skipping
steps allowed.

## Why this exists

### The problem

Most repositories are built for humans who already know the codebase. A coding agent arrives with
only a chat prompt and a shallow file snapshot — and that gap produces predictable failure modes:

- It **edits code before understanding intent** — solving the wrong problem fluently.
- **Constraints live only in chat history** or someone's head, so they're lost between sessions.
- **Validation expectations are vague**, discovered too late, or asserted without proof.
- **Architecture tradeoffs get re-litigated** every time instead of inherited.
- The **same process is applied to every change** — over-ceremonying a typo, under-scrutinizing an
  auth rewrite — and the human is asked about everything or nothing.

### The harness approach

A repo grows a *harness* so an agent can answer the practical engineering questions **before it
writes code**, without relying on conversation history:

- *What should I read first?*
- *What type of work is this, and how risky?*
- *Which product contract does it touch?*
- *What proof will show the work is done?*
- *What decision or lesson should future agents inherit?*

And it sizes the answer with **one principle, two independent dials:**

> **Ceremony scales with risk. Human interruption scales with ambiguity.**

**Risk** decides how much *proof and process* a change carries (planning, reviews, recorded
evidence and rollback). **Ambiguity / confidence** decides whether a *human* is asked — never to
classify risk, only to confirm intent or authorize a dangerous boundary. So a high-risk-but-clear
change runs autonomously through heavy proof, while a tiny-but-unclear change stops to ask. Risk ≠
interruption.

### How this repo resolves it

The repo is two layers: an **engine** of invocable `/skills` that do the work, and a thin
**harness** that decides — *before* the engine runs — how much process and when to involve a
human. Each engineering question maps to an enforced mechanism, not a convention:

| The question | Resolved by |
|---|---|
| What should I read first? | `session-knowledge` hook loads `docs/solutions/` index + critical patterns at session start; `/xia2` researches what already exists. |
| What type of work, how risky? | `/feature-intake` runs first — a 10-flag checklist + hard gates assign a **lane** (`tiny\|normal\|high-risk`) and a **confidence** to `specs/<slug>/SUMMARY.md`. |
| Which contract does it touch? | Hard gates (auth · migration · public contract · high-blast file) force `high-risk`; `blast-radius` hook flags edits outside the plan. |
| What proof shows it's done? | A re-runnable `### Verify` artifact backs every "done"; `TEST_MATRIX.md` marks a behavior `implemented` only with evidence. |
| What should future agents inherit? | `/compound` crystallizes non-obvious learnings into `docs/solutions/`; `agent-memory/` carries facts forward with confidence decay. |

And the claim is corroborated by code: at commit time, hooks check the staged diff against the
declared lane — the agent can't label a risky change "tiny" and slip it through.

See **[HARNESS.md](HARNESS.md)** for the full model — lanes, hard gates, and how each hook
enforces it.

## Installation

### Add to an existing project

One-liner that clones the harness, builds `.claude/`, and leaves your project root clean:

```bash
curl -fsSL "https://raw.githubusercontent.com/minhtran3124/harness-skills/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes
```

Everything the harness needs lives entirely in a gitignored `.claude/` (skills, agents, hooks, rules, templates, settings) — the only root file is `.mcp.json`, which wires the code-review-graph MCP server (merged into your existing `.mcp.json` if you have one; Claude Code only reads this file at the project root). The installer never stages files at your project root, so it never overwrites or deletes anything there. **To update, just re-run the one-liner** (idempotent; `.claude/` is merge-synced, non-harness entries kept).

Needs `git` + [jq](https://jqlang.github.io/jq/); [uv](https://docs.astral.sh/uv/) is strongly recommended — the code-review-graph MCP server launches through `uvx`, and the installer warns when it's missing.
Flags: `--directory <path>` · `--branch <name>` · `--source <local checkout>` · `--keep-sources` · `--dry-run`.

Then **restart Claude Code** so it loads the skills, agents, and hooks.

### Develop on this repo

Working *on the harness itself* keeps the editable source at the repo root and Claude Code loads from a derived, gitignored `.claude/`. Rebuild it with:

```bash
bash scripts/deploy-harness.sh
```

First run installs; any later run updates (idempotent). Re-run after editing anything under `skills/` `agents/` `hooks/` `rules/` `templates/` `settings.json`. (Installing into another project with `--keep-sources` keeps a copy of these sources in `<target>/.harness-source/`, for inspection or offline re-sync via `bash .harness-source/scripts/deploy-harness.sh --target .`.)

### Testing

`bash scripts/run-tests.sh` runs what CI runs: syntax checks + a doc-truth lint (every path referenced in the core docs exists; the CLAUDE.md hook table matches `settings.json`), hermetic contract tests for the hooks (each runs in a throwaway git repo against its stdin-JSON contract), and installer integration tests. The `harness-ci` workflow runs the same suite on ubuntu + macos.

### MCP servers

This repo wires the [code-review-graph](https://pypi.org/project/code-review-graph/) MCP server in [.mcp.json](.mcp.json) — and `install-harness.sh` wires the same server into a consuming project's root `.mcp.json` automatically (creating it, or merging the entry into an existing one). It launches through [uv](https://docs.astral.sh/uv/)'s `uvx` runner, so there's **no manual `pip install`** — `uvx` fetches and runs it on demand.
You just need `uv` (which provides `uvx`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # installs uv + uvx
uvx code-review-graph serve                        # exactly what .mcp.json invokes
```

The graph data is written to `.code-review-graph/` (gitignored). The `context7` MCP server is configured at the Claude Code **user** level (HTTP, needs `CONTEXT7_API_KEY`) — it is *not* in this repo's `.mcp.json`, so each user wires it in their own global config.

## Repository layout

| Path | What it holds |
|---|---|
| `skills/` | The skill library — one subdir per skill, each with a `SKILL.md`. |
| `agents/` | Sub-agent role definitions dispatched by skills. |
| `rules/` | Architecture & process governance read by skills/agents. |
| `hooks/` | Bash automation wired into Claude Code lifecycle events. |
| `agent-memory/` | Per-agent persistent memory with confidence decay. |
| `specs/` | Per-feature work artifacts — one `<slug>/` dir per change (SUMMARY, design, PLAN, …). |
| `templates/` | Canonical shapes copied into `specs/<slug>/` — `SUMMARY`, `TEST_MATRIX`, `ESCALATIONS`. |
| `docs/` · `scripts/` | Reference docs and standalone helpers. |
| `CLAUDE.md` · `settings.json` · `.mcp.json` | Project instructions; hooks + env + plugins; MCP server config (`mcpServers` only). |

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
/correctness-review              adversarial runtime-bug hunt over the diff
        |
/intent-review                   diff vs the original request, blind to PLAN
        |
/compound                        capture non-obvious learnings
        |
/finishing-a-development-branch  push + open a PR (a human reviews & merges)
```

`/correctness-review` and `/intent-review` also run standalone on any diff. See
[skills/README.md](skills/README.md) for the alternate paths (minimum-viable, bug-fix) and the
full handoff map.

## Further reading

> **[skills/README.md](skills/README.md)** is the single source of truth — full skill
> inventory, triggers, outputs, handoff map, alternate paths, and per-skill design rationales.
>
> **[HARNESS.md](HARNESS.md)** — how the risk/trust harness shapes the workflow: lanes,
> when a human is asked, and how hooks enforce it. Read this to understand *why* the flow behaves
> the way it does.

## Author

**Minh Tran** — [@minhtran3124](https://github.com/minhtran3124) · <tranhuuminh3124@gmail.com>

See [`CONTRIBUTORS.md`](CONTRIBUTORS.md) for the full cast and how to join in.
</content>
