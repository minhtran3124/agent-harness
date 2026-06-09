# claude-skills

Skill framework and governance system for Claude Code — reusable prompt-based workflows from brainstorm to ship.

## Behavioral Guidelines

See @rules/behavior.md — that file is the single source of truth.

---

## Stack

- **Skills** — Markdown prompt documents in `skills/<name>/SKILL.md`, invoked as `/skill-name`
- **Rules** — Architecture/process governance in `rules/`
- **Hooks** — Bash automation in `hooks/`, registered in `settings.json`
- **Knowledge base** — `docs/solutions/<category>/<slug>.md` with YAML front-matter
- **Agents** — Sub-agent role definitions in `agents/`

## Skill Workflow

`feature-intake` runs first and **routes by lane** — it decides how much of the chain below
actually runs (tiny lane skips straight to a direct edit; high-risk runs the full chain).
Skipping a step the lane requires is a hard gate violation:

```
feature-intake (classify → lane + confidence → route)
  → [brainstorming → xia2 →] writing-plans → using-git-worktrees
  → subagent-driven-development (or executing-plans)
  → correctness-review (final adversarial pass — also invokable standalone on any diff)
  → compound → finishing-a-development-branch
```

Lane → ceremony; confidence/ambiguity → whether a human is asked. See `rules/orchestration.md`
and `skills/feature-intake/SKILL.md`. See @skills/README.md for full inventory and handoff map.

## Knowledge Base

Solved problems, patterns, and architectural decisions: `docs/solutions/`
Browse the index: `docs/solutions/INDEX.md`
Critical learnings (read at planning time): `docs/solutions/critical-patterns.md`

## Hooks

Hooks live in `hooks/` (top-level). Register them in `settings.json` under the appropriate trigger key. **Wired** = currently registered in `settings.json` and firing; **dormant** = present on disk but not registered.

| Hook | Trigger | Action | Wired |
|---|---|---|---|
| `check-untracked-py.sh` | PreToolUse (Bash `git *`) | Block commit/push if untracked `.py` files exist | ✅ |
| `commit-quality-gate.sh` | PreToolUse (Bash `git commit`) | Secrets scan + debug artifact check + targeted pytest | ✅ |
| `risk-corroboration.sh` | PreToolUse (Bash `git commit`) | Block if staged diff trips a hard gate but declared `Lane:` is below `high-risk` | ✅ |
| `branch-guard.sh` | PreToolUse (Bash `git commit`) | Warn when committing on `main` | ✅ |
| `ruff-on-edit.sh` | PostToolUse (Edit/Write) | `ruff --fix` + `ruff format` on edited `.py` files | ✅ |
| `blast-radius-check.sh` | PostToolUse (Edit/Write) | Warn when an edit touches a file outside the active plan `<files>` set | ✅ |
| `scope-gate.sh` | UserPromptSubmit | Warn on implementation intent with no plan referenced (lane-aware) | ✅ |
| `state-breadcrumb.sh` | SessionEnd | Append a dated session breadcrumb to `specs/STATE.md` (`## Session End Log`) for cross-session resumption; never blocks | ✅ |
| `auto-test-on-change.sh` | PostToolUse (Edit/Write) | `pytest` on changed files | ⬜ dormant |
| `validate-buzz-commands.sh` | PreToolUse (Bash) | Restrict to post_buzz and read-only git/gh commands | ⬜ dormant |

## Gotchas

- `specs/` is fully gitignored — `PLAN.md`, `PLAN.html`, `design.md`, `research-brief.md`, and sidecars all stay local. Skills update them in-place; nothing is committed (including the `shipped` status transition)
- `settings.local.json` overrides `settings.json` — user-specific permissions and allowlists live there, not in the shared config
- `mcp.json` is at repo root (not in `.claude/`) — holds **only** `mcpServers` (the project's `code-review-graph` server, launched via `uvx`; requires `uv` installed). `context7` is a **user-level** MCP server (HTTP, `CONTEXT7_API_KEY`), not in this file. `env`, `permissions`, `hooks`, `statusLine`, `enabledPlugins` belong in `settings.json`, not here
- `docs/solutions/` entries have a `confirmed_at` field; treat entries older than 30 days as potentially stale
- When ≥5 `app/` files are staged, the commit hook hints to run `/compound` — don't skip it

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
