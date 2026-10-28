<p align="center">
  <img src="docs/assets/skill-harness-hero.jpg" alt="A miniature papercraft workshop moving coding tasks through discovery, design, planning, execution, review, and shipping gates" width="100%">
</p>

<div align="center">

# Skill Harness

**A ready-to-use toolkit of skills, agents, hooks, and rules for the [Claude Code](https://claude.com/claude-code) CLI**

*Prompt-powered workflows that carry a change from brainstorm to ship.*

📖 **[Read the Guide →](https://skill-harness-guide.vercel.app)**

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
| What should I read first? | start at `docs/solutions/INDEX.md` and `critical-patterns.md`; `/xia2` researches what already exists. |
| What type of work, how risky? | `/feature-intake` runs first — a 10-flag checklist + hard gates assign a **lane** (`tiny\|normal\|high-risk`) and a **confidence**. |
| Which contract does it touch? | Hard gates (auth · migration · public contract · high-blast file) force `high-risk`. |
| What proof shows it's done? | A re-runnable check backs every "done": a test command and its exit code, stated in the PR. |
| What should future agents inherit? | `/compound` crystallizes non-obvious learnings into `docs/solutions/`, the harness's sole committed knowledge path. |

And the claim is corroborated by code: at commit time, hooks check the staged diff against the
declared lane — the agent can't label a risky change "tiny" and slip it through. (Two gates,
`workflow-engine` and `weakening-validation`, are warn-mode: they print a note instead of blocking.)

See **[HARNESS.md](HARNESS.md)** for the full model — lanes, hard gates, and how each hook
enforces it.

## Installation

### Add to an existing project

One-liner that clones the harness, builds `.claude/`, and leaves your project root clean:

```bash
curl -fsSL "https://raw.githubusercontent.com/minhtran3124/agent-harness/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes
```

Everything the harness needs lives in a gitignored `.claude/` (skills, agents, hooks, rules, templates, runtime, a consumer subset of `scripts/`, settings). At the project root it touches only the workflow's structural dirs (`specs/`, `docs/solutions/`), scaffolded **create-if-missing**. The installer never overwrites or deletes anything at your root — it only adds structural files that are absent. **To update, just re-run the one-liner** (idempotent; `.claude/` is merge-synced, non-harness entries and locally-generated files kept; a protected file that differs from incoming is reported via a `<file>.harness-incoming` sidecar rather than overwritten).

Needs `git` + [jq](https://jqlang.github.io/jq/) + `python3`.
Flags: `--directory <path>` · `--branch <name>` · `--source <local checkout>` · `--profile <name>` (deprecated and ignored: hook profiles were removed, every install gets the one fixed hook set) · `--keep-sources` · `--dry-run` · `--overwrite-conflicts` (replace protected files with the incoming copy; `--force`/`--yes` keep local files instead of overwriting them).

Then **restart Claude Code** so it loads the skills, agents, and hooks.

### Develop on this repo

Working *on the harness itself* keeps the editable source at the repo root and Claude Code loads from a derived, gitignored `.claude/`. Rebuild it with:

```bash
bash scripts/deploy-harness.sh
```

First run installs; any later run updates (idempotent). Re-run after editing anything under `skills/` `agents/` `hooks/` `rules/` `templates/` `settings.json`. (Installing into another project with `--keep-sources` keeps a copy of these sources in `<target>/.harness-source/`, for inspection or offline re-sync via `bash .harness-source/scripts/deploy-harness.sh --target .`.)

### Testing

`bash scripts/run-tests.sh` runs what CI runs: syntax checks + a doc-truth lint (every path referenced in the core docs exists; the CLAUDE.md hook table matches `settings.json`), further static checks (skill-bash lint, skill and agent frontmatter and tool conformance scanned from disk, STE linter self-test), hermetic contract tests for the hooks (each runs in a throwaway git repo against its stdin-JSON contract), script and installer integration tests, and the Python unit tests under `scripts/`, `runtime/`, and `skills/` (when `pytest` is available). The `harness-ci` workflow runs the same suite on ubuntu + macos.

### Optional MCP servers (local setup)

The harness needs no MCP server. If you want one, install it yourself — nothing below is committed to the repo.

**code-review-graph** (code graph for callers, dependents, blast radius). Install [uv](https://docs.astral.sh/uv/), then from the project root:

```bash
claude mcp add --scope local code-review-graph -- uvx code-review-graph serve
echo ".code-review-graph/" >> "$(git rev-parse --git-common-dir)/info/exclude"   # keep the graph data out of git (works in worktrees too)
```

Local scope is private to you: it is stored in `~/.claude.json` under this project's path, not in the repo. If `/mcp` does not show the server in a session started inside a git worktree, add it with `--scope user` instead.

**context7** (library docs). Configure it at user scope or as a plugin in your own Claude Code config.

**Personal instructions** (for example, when to use these servers). Put them in an untracked `CLAUDE.local.md` at the project root, excluded the same way (`echo "CLAUDE.local.md" >> "$(git rev-parse --git-common-dir)/info/exclude"`); Claude Code loads it alongside `CLAUDE.md`. It exists only in the checkout or worktree where you created it, so for notes that must follow you into worktrees, import a home-directory file (`@~/.claude/<file>.md`) or use the user-level `~/.claude/CLAUDE.md`. Run `/memory` to confirm what loaded and `/mcp` to see connected servers.

## Further reading

> **[skills/README.md](skills/README.md)** is the single source of truth — full skill
> inventory, triggers, outputs, handoff map, alternate paths, and per-skill design rationales.
>
> **[HARNESS.md](HARNESS.md)** — how the risk/trust harness shapes the workflow: lanes,
> when a human is asked, and how hooks enforce it. Read this to understand *why* the flow behaves
> the way it does.
>
> **[Guide site](https://skill-harness-guide.vercel.app)** — the companion walkthrough at
> `skill-harness-guide.vercel.app`.

## Author

**Minh Tran** — [@minhtran3124](https://github.com/minhtran3124) · <tranhuuminh3124@gmail.com>

See [`CONTRIBUTORS.md`](CONTRIBUTORS.md) for the full cast and how to join in.
</content>
