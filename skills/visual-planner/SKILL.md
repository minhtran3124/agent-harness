---
name: visual-planner
description: Render a `PLAN.md` to a self-contained local HTML review page. Use after planning or standalone to inspect plan waves, tasks, scope, and optional review-derived risk.
allowed-tools: Bash, Read, Grep, Glob, Write
---

# Plan → HTML Renderer

The executable interface is authoritative. Never hand-transcribe HTML. Resolve
`<visual-planner-dir>` to the directory that contains this loaded `SKILL.md`:

```bash
python3 <visual-planner-dir>/render_plan.py <path-or-slug> [output.html]
```

The renderer resolves a PLAN path or unambiguous slug, writes a sibling untracked `PLAN.html`,
and performs self-checks. Relay its stdout. On failure, report its `SELF-CHECK FAILED:` output
and do not claim success. `template.html` controls layout and `render_plan.py` owns parsing.

`--summarize` first injects or refreshes the tracked At-a-glance block in `PLAN.md`. The block
sits between the generated `AT-A-GLANCE:BEGIN`/`END` sentinel lines. Its `### Progress` checklist
comes from `## Status Log`. `--summarize` writes `PLAN.md` only on change, then renders as usual.
Three callers run it:

- `writing-plans` runs it after it saves a plan.
- `rules/wave-parallelism.md` runs it at each wave boundary.
- `finishing-a-development-branch` runs it before the shipped commit.

Use `view_plan.py <slug> --file|--no-open|--port N|--render` only on a request for visual viewing.
Its serving mode blocks. Do not auto-open from writing-plans or a headless environment.

## Optional review overlay

For evidence-backed plan review, do these steps in order:

1. Emit the plan files.
2. Gather evidence per file with Grep/Read. Optionally, also use any installed code-graph tool.
3. Render a sidecar.

Steps 1 and 3 use these commands:

```bash
python3 <visual-planner-dir>/render_plan.py <slug> --emit-files
python3 <visual-planner-dir>/render_plan.py <slug> --review specs/<slug>/.plan-review.json
```

The sidecar records provenance plus per-file path, status (`new|existing|missing`), dependents,
tests, risk (`high|medium|low`), note, and optional flows. New/missing files remain explicit.
Do not invent risk or coverage. Review output defaults to untracked `PLAN.review.html`.

The renderer supports both XML and canonical markdown task forms. Keep parsing and rendering
behavior in the tested code. Re-run the renderer's unit tests in the harness repo after changes.

## References

- `references/review-sidecar.md` — sidecar schema and evidence rules
