---
name: visual-planner
description: Use after a PLAN.md is written, when you want to review it visually before execution (auto-invoked by /writing-plans; also standalone as /visual-planner <slug>). Renders specs/<slug>/PLAN.md to a self-contained HTML page; optional --review mode overlays graph-derived blast-radius and risk.
allowed-tools: Bash, Read, Glob, Write, mcp__code-review-graph__list_graph_stats_tool, mcp__code-review-graph__query_graph_tool, mcp__code-review-graph__get_impact_radius_tool, mcp__code-review-graph__get_affected_flows_tool
---

# Plan → HTML Renderer

## Purpose

Render a single `specs/<slug>/PLAN.md` into a modern, self-contained `specs/<slug>/PLAN.html`
so a reviewer can visually scan waves, tasks, and per-task scope without parsing raw XML or
markdown. Output is **local-only** — `PLAN.html` stays untracked (gitignored as a derived artifact)
next to its source in `specs/` (which is tracked).

## How it works (deterministic script, not LLM transcription)

Rendering is done by `render_plan.py`, **not** by emitting HTML token-by-token. The skill's only
job is to run the script and relay its report:

```bash
python3 .claude/skills/visual-planner/render_plan.py <path-or-slug> [output.html]
```

Run from repo root (the script also locates `specs/` relative to its own path as a fallback).

Two files own the behavior:

| File | Role |
|---|---|
| `render_plan.py` | Parser + builder + self-check. The source of truth for parsing rules. |
| `template.html` | The visual template (CSS/JS/layout) with `{{PLACEHOLDER}}` slots. Edit this to change styling — never regenerate it by hand. |
| `view_plan.py` | Serves/opens the rendered `PLAN.html` and launches Chrome. Auto-renders if missing/stale. See "Viewing the plan" below. |

This split is intentional. Asking the model to transcribe a ~340-line template verbatim each run
is both expensive (output tokens) and the *least* deterministic part of the pipeline. A script makes
the fill free and byte-for-byte reproducible. (See `CLAUDE.local.md` §8 — "if code can answer, code
answers".)

## Invocation

```
/visual-planner <path-or-slug>          # render PLAN.md → PLAN.html
/visual-planner <slug> --view           # render (if stale) then open in the browser
/visual-planner <file.html> --view      # open an already-rendered HTML file as-is
```

**Routing:** if the arguments contain `--view`, run `view_plan.py` (see "Viewing the plan" below),
passing the positional arg and any `--file` / `--port` / `--no-open` / `--render` through verbatim —
`view_plan.py` accepts a slug, a `PLAN.md` path, **or** an `.html` file (viewed as-is, no render).
Without `--view`, run `render_plan.py` as described next.

Argument resolution (implemented in the script):

1. Normalize `\r\n` → `\n` on read.
2. Arg ends in `PLAN.md` and exists → use directly.
3. Otherwise treat as a slug → glob `specs/**/<slug>/PLAN.md`.
   - 0 matches → error `No PLAN.md found for slug "<slug>".`
   - >1 matches → error listing them; pass an explicit path.
4. Output path: `<plan-dir>/PLAN.html` (sibling), overwritten silently (untracked). With
   `--review`, the default becomes `<plan-dir>/PLAN.review.html` so a later plain render does
   not clobber the review build; an explicit `[output.html]` positional overrides either default.

The skill should run the command and surface the script's stdout. On a non-zero exit, surface the
`SELF-CHECK FAILED:` lines verbatim — do not claim success.

## Viewing the plan (serve + open Chrome)

`view_plan.py` *displays* a rendered plan (`render_plan.py` builds it; `view_plan.py` shows it). It
auto-renders `PLAN.html` first when it is missing or older than `PLAN.md`, so it always shows the
current plan.

```bash
# Default: serve on localhost + open Chrome (blocks until Ctrl+C)
python3 .claude/skills/visual-planner/view_plan.py <slug>

# Open the raw file via file:// (no server, returns immediately)
python3 .claude/skills/visual-planner/view_plan.py <slug> --file

# Pin a port / skip the browser (headless or agent context)
python3 .claude/skills/visual-planner/view_plan.py <slug> --port 8801 --no-open
```

| Flag | Effect |
|---|---|
| _(none)_ | Serve plan dir at `http://127.0.0.1:<auto-port>/PLAN.html`, open Chrome, block until Ctrl+C |
| `--file` | Open `PLAN.html` via `file://` (no server) — fastest, but "copy `<verify>`" uses the `execCommand` fallback |
| `--port N` | Bind the server to port N instead of an auto-picked free port |
| `--no-open` | Render + serve (or print the file URL) without launching a browser |
| `--render` | Force a re-render even if `PLAN.html` looks fresh |

**Why serve instead of just `file://`?** localhost is a browser *secure context*, so the per-task
"copy `<verify>`" buttons use `navigator.clipboard`; over `file://` Chrome blocks that API and the
page falls back to the deprecated `execCommand` path. Use `--file` when clipboard doesn't matter.

**Agent note:** server mode blocks (`serve_forever`) — run it via the background runner (the URL line
is flushed immediately, so it's captured). Auto-opening Chrome is intentionally **not** wired into the
writing-plans handoff: viewing is environment-dependent (headless CI / remote boxes have no display),
so it stays an explicit step the user (or a human-driven `! python3 …`) triggers.

## What it renders

- **Header**: title (from `# `), status badge (frontmatter `status`), owner/created/slug meta,
  source-file links (`PLAN.md`, `design.md`, `research-brief.md` when present).
- **Stats card**: tasks, waves, unique files touched, `K/N` parallel waves; optional progress strip
  when the Status Log has parsed task entries.
- **Intro card**: the `**Goal:** / **Architecture:** / **Tech Stack:**` lines above the first `##`,
  each rendered for scannability instead of as a wall of prose (fields may wrap across source lines —
  the full paragraph is captured, not just line 1):
  - **Tech Stack** → comma-split into chips.
  - **Architecture** → a **"scope of change" map**: clauses (split on `;` and sentence boundaries)
    are verb-classified into `add / change / keep / remove / exclude` (deterministic keyword map,
    unmatched → neutral `note`) and rendered as colour-coded rows with a count dashboard on top. A
    single-clause Architecture stays a paragraph. Classification is in `_ACTION_RULES` (render_plan.py).
  - **Goal / other** → bullet list when multi-clause, else a paragraph.
- **Wave-flow SVG**: one column per wave, task nodes linking to their cards, arrows between waves.
- **Sections**: every `## ` section except `Tasks`, in source order. Recognized sections get
  structured rendering (each **degrades to plain markdown** for tables or non-list bodies, and
  preserves prose before/after the list):
  - `Risks` → severity-coded register cards. Severity is taken **only** from explicit author
    signals — a `(Critical|High|Real|Medium|Moderate|Low)` tag or a leading `KNOWN` — mapped to
    RAG colors; untagged risks stay neutral (no fabricated severity). A `Mitigation:` clause is
    split out and labeled. A markdown-table risks section stays a table.
  - `Success Criteria` → acceptance checklist (Definition-of-Done `☐` rows); a `→` is styled as
    the condition→outcome boundary.
  - `Non-goals` → out-of-scope list (`⊘`, slate styling matching the change-map `exclude`).
  - `Motivation` → accent callout block.
  - `Status Log` → kind-colored timeline. Any `- YYYY-MM-DD <—|:|-> note` entry is parsed
    (continuation lines folded, nested sub-bullets kept); each entry is classified
    build/decision/plan/open/note for a colored dot + chip. Logs longer than 8 entries collapse
    the older ones behind a native `<details>` toggle (keeps the most recent 5 visible). The
    stats progress strip is derived from task ids the log marks complete (`✓` / "complete" in a
    build entry, intersected with real task ids). Empty logs fall back to prose.
- **Tasks**: collapsible cards grouped by wave; first card of the lowest wave starts expanded;
  `<files>` → chips, `<verify>` → copyable code block, sub-tasks (`N.M.x`) nest under their parent.

## Plan Review mode (`--review`)

Overlays a **graph-derived "Plan Review"** section (impact dashboard, per-file blast-radius
table, high-risk cards) between the plan body and the Tasks block — the same idea as
visual-explainer's `/plan-review`, but backed by this repo's `code-review-graph` instead of grep.

The renderer is offline and **cannot call MCP itself**, so review is a 3-step dance the agent runs:

1. **Emit the file list** the plan touches:
   ```bash
   python3 .claude/skills/visual-planner/render_plan.py <slug> --emit-files
   ```
2. **Gather graph data** for each source file via `code-review-graph` MCP and classify it:
   - `query_graph` `importers_of` → split importers into **code dependents** (blast radius) vs
     **test files** (coverage signal; file-level `tests_for` returns 0, so use test-file importers).
   - `get_impact_radius` (with `apps/api/...` paths) → overall risk + N-hop file count.
   - `get_affected_flows` (optional) → user-facing flows the change touches.
   - A file absent from the graph → `status: "new"` (created by the plan) or `"missing"` (bad path).
   Assign `risk` with judgment: high = many code dependents, central config, or a file flagged in
   `CLAUDE.local.md` (e.g. `streaming_service.py`, `repositories/ai/`, `session_manager.py`).
3. **Write the sidecar JSON** and render:
   ```bash
   # specs/<slug>/.plan-review.json  (untracked, like PLAN.html)
   python3 .claude/skills/visual-planner/render_plan.py <slug> --review specs/<slug>/.plan-review.json
   ```

### Sidecar schema

```json
{
  "base": "free-text provenance, e.g. graph @ DATE (impact: high, N files)",
  "files": [
    {
      "path": "app/services/ai/streaming_service.py",
      "status": "new | existing | missing",
      "dependents": 1,
      "dependent_names": ["app/services/ai/chat_service.py"],
      "tests": ["tests/services/ai/test_overloaded_error_handling.py"],
      "risk": "high | medium | low",
      "note": "why it matters — surfaced as a card for high-risk files"
    }
  ],
  "flows": ["optional", "affected", "flow names"]
}
```

Dashboard stats are derived from `files`: total, new, existing, total dependents, untested count.
High-risk files also render as cards with their note + dependent chips. A `--review` render
writes `PLAN.review.html` (not `PLAN.html`) by default, so it never clobbers a plain render.
Omit `--review` for a plain plan render.

## Parsing notes (authoritative details live in `render_plan.py`)

- **Tasks may be raw `<task>` blocks OR fenced in ` ```xml `.** Real PLAN.md files in this repo use
  both conventions. The script masks fenced code first and extracts raw tasks; example/illustration
  `<task>` snippets inside an `<action>` (or any fence) are ignored. If a plan fences its *real*
  tasks and has no raw ones, the script falls back to scanning fenced tasks.
- **Entity-preserving escaping**: source like `&lt;slug&gt;` or `jq . &gt; /dev/null` round-trips to
  the intended glyph instead of double-escaping.
- **Pipe tables**: `\|` is honored; a malformed table falls back to `<pre>` rather than misrendering.
- **Frontmatter**: only `slug`, `status`, `owner`, `created` are consumed; others ignored.

## Self-check (run by the script before claiming success)

1. Output is non-empty.
2. No `{{PLACEHOLDER}}` survived substitution.
3. The frontmatter `slug` appears somewhere in the output.
4. `<section data-wave="…">` wrapper count equals the number of distinct waves (or exactly 1 for the
   empty-state when no tasks were parsed).

On success it prints `Wrote <path> (<N> bytes).` plus a `tasks=/waves=` line and an `open <path>`
hint. Auto-open is intentionally deferred — `Bash(open *)` is not required by this skill.

## Deviations from the original (LLM-transcription) spec

- **Self-check #2 fixed.** The old spec required the `slug` inside `<title>`, but the template
  hardcodes `<title>{{TITLE}} · plan</title>` (TITLE = H1 text, never the slug) — unsatisfiable. The
  script instead asserts the slug appears anywhere in the output and that no placeholder remains.
- **Raw-or-fenced task handling** (above) — the original spec assumed only fenced ` ```xml ` tasks;
  real plans use raw blocks and reserve fences for examples.
- **Status Log prose fallback** — when no entries match the timeline grammar, the rich free-form log
  is rendered as prose instead of being dropped.

Verified against `eng-315-api-key-generation` (7 tasks/5 waves), `workflow-upgrade` (15/2),
`kb-auto-regenerate-on-merge` (6/1), `eng-380-datadog-sdk` (12/5), `eng-334-xml-prompt-migration`
(10/3).
