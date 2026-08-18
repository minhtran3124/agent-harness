---
name: visual-planner
description: Render a `PLAN.md` to a self-contained local HTML review page. Use after planning or standalone to inspect plan waves, tasks, scope, and optional graph-derived risk.
allowed-tools: Bash, Read, Glob, Write, mcp__code-review-graph__list_graph_stats_tool, mcp__code-review-graph__query_graph_tool, mcp__code-review-graph__get_impact_radius_tool, mcp__code-review-graph__get_affected_flows_tool
---

# Plan → HTML Renderer

The executable interface is authoritative; never hand-transcribe HTML. Resolve
`<visual-planner-dir>` to the directory containing this loaded `SKILL.md`:

```bash
python3 <visual-planner-dir>/render_plan.py <path-or-slug> [output.html]
```

The renderer resolves a PLAN path or unambiguous slug, writes a sibling untracked `PLAN.html`,
and performs self-checks. Relay its stdout; on failure report its `SELF-CHECK FAILED:` output
without claiming success. `template.html` controls layout and `render_plan.py` owns parsing.

Use `view_plan.py <slug> --file|--no-open|--port N|--render` only when visual viewing is requested;
its serving mode blocks. Do not auto-open from writing-plans or a headless environment.

## Optional review overlay

For graph-backed plan review, first emit plan files, gather graph evidence, then render a sidecar:

```bash
python3 <visual-planner-dir>/render_plan.py <slug> --emit-files
python3 <visual-planner-dir>/render_plan.py <slug> --review specs/<slug>/.plan-review.json
```

The sidecar records provenance plus per-file path, status (`new|existing|missing`), dependents,
tests, risk (`high|medium|low`), note, and optional flows. New/missing graph nodes remain explicit;
do not invent risk or coverage. Review output defaults to untracked `PLAN.review.html`.

Both XML and canonical markdown task forms are supported. Keep parsing and rendering behavior in
the tested code; use `test_render_plan.py` after changes.

## References

- `README.md` — user-facing renderer and sidecar details
- `references/review-sidecar.md` — sidecar schema and evidence rules
