---
slug: plan-at-a-glance
status: shipped
owner: Minh Tran
created: 2026-07-15
---

# At-a-glance PLAN.md summary block Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: use `subagent-driven-development` (or `executing-plans`) to
> implement this plan task-by-task. This edits a core skill engine (`render_plan.py`, high-risk lane)
> and a hook — every `<verify>` is an automated pytest/bash assertion; exit 0 = pass.

**Goal:** Make every tracked `specs/<slug>/PLAN.md` self-summarizing — a human sees scope, order, and
progress with zero tooling — by having `render_plan.py --summarize` inject a deterministic, additive
"At a glance" block (issue #54, scope A+B).

**Architecture:** Reuse the existing parser end-to-end. Add three functions to `render_plan.py`
(`render_summary_block` pure builder, `inject_summary_block` pure string transform,
`summarize_plan_file` I/O wrapper), a new opt-in `--summarize` CLI flag, and an HTML-side strip of the
generated region. Wire `--summarize` through the existing `render-plan-on-write.sh` PostToolUse hook.
The `<task>` blocks stay the single source of truth; the block is derived, idempotent, and never
hand-edited. Full context: `specs/plan-at-a-glance/design.md` + `research-brief.md`.

**Tech Stack:** Python 3 stdlib only; pytest (`skills/visual-planner/test_render_plan.py`); Bash hook
+ its contract test (`tests/hooks/render-plan-on-write.test.sh`); GitHub-native Mermaid on the reader
side.

---

## 1. Motivation

`PLAN.md` is tracked but authored as raw fenced `xml` `<task>` blocks. A human reading it on GitHub or
via `cat` gets no wave map, no file map, no progress — the readable `PLAN.html` is gitignored and
local-only. The parser already extracts every field a summary needs (`parse_task_block`,
`attach_titles`, `_done_task_ids`); the only missing capability is writing a derived summary back into
the Markdown. This adds exactly that, additively and deterministically.

## 2. Non-goals

- Directions C (publish `PLAN.html` as an Artifact URL) and D (`build_roadmap.py` entry point) — deferred.
- No change to the machine contract: agents still parse `<task id/wave/files/action/verify/done>`.
- No new dependency; no new file; stdlib only.
- Bare `render_plan.py <FILE>` keeps its current read→HTML-only behavior (the 43 existing tests stay green).

## 3. Success Criteria

- `render_plan.py <FILE> --summarize` injects an "At a glance" block (count line + wave×task table +
  wave-subgraph Mermaid + progress checklist) immediately before the first `## ` heading, preserving
  the H1 and any `> **For Claude:**` directive blockquote.
- Re-running `--summarize` on an unchanged plan writes nothing (byte-identical → no-op diff).
- Checkbox state derives from `## Status Log` via `_done_task_ids`; the Status Log stays the source of truth.
- The HTML render strips the generated region (no duplicate "At a glance" section in `PLAN.html`).
- The `render-plan-on-write.sh` hook passes `--summarize`; all hook contract cases pass.
- The 43 existing `test_render_plan.py` cases remain green.

## 4. Tasks

### Task 1.1 — `render_summary_block` (pure, deterministic builder)

```xml
<task id="1.1" wave="1">
  <files>skills/visual-planner/render_plan.py, skills/visual-planner/test_render_plan.py</files>
  <action>
TDD. FIRST add failing tests, run them (they fail — function undefined), THEN implement, THEN re-run
to green.

STEP 1 — write these tests in test_render_plan.py (module is loaded as `rp`). Use a small factory:

    def _task(id, wave, files, done, title=None):
        t = {"id": id, "wave": wave, "files": files, "verify": "", "action": "", "done": done}
        if title is not None:
            t["title"] = title
        return t

    class TestSummaryBlock:
        def _tasks(self):
            return [
                _task("1.1", "1", "app/models/x.py, alembic/y.py", "Migration applies clean", "model+migration"),
                _task("1.2", "1", "app/schemas/x.py", "Schemas validate", "schemas"),
                _task("2.1", "2", "app/repos/x.py", "Repo tests pass", "repository"),
            ]

        def test_deterministic(self):
            b1 = rp.render_summary_block(self._tasks(), {"1.1"})
            b2 = rp.render_summary_block(self._tasks(), {"1.1"})
            assert b1 == b2

        def test_has_both_sentinels(self):
            b = rp.render_summary_block(self._tasks(), set())
            assert rp.SUMMARY_BEGIN in b and rp.SUMMARY_END in b
            assert b.startswith(rp.SUMMARY_BEGIN) and b.rstrip().endswith(rp.SUMMARY_END)

        def test_count_line(self):
            b = rp.render_summary_block(self._tasks(), {"1.1"})
            # 3 tasks, 2 waves, 4 distinct files, 1 done
            assert "**3 tasks · 2 waves · 4 files · 1/3 done**" in b

        def test_checkboxes_from_done(self):
            b = rp.render_summary_block(self._tasks(), {"1.1"})
            assert "- [x] 1.1 — model+migration" in b
            assert "- [ ] 2.1 — repository" in b

        def test_mermaid_wave_subgraphs(self):
            b = rp.render_summary_block(self._tasks(), set())
            assert "flowchart LR" in b
            assert "subgraph W0[Wave 1]" in b
            assert "subgraph W1[Wave 2]" in b
            assert "W0 --> W1" in b

        def test_missing_title_falls_back_to_id(self):
            t = [_task("3.1", "1", "a.py", "done text")]  # no title key
            b = rp.render_summary_block(t, set())
            assert "- [ ] 3.1 — 3.1" in b

        def test_all_dash_waves_count_one_wave(self):
            t = [_task("1", "—", "a.py", "d"), _task("2", "—", "b.py", "d")]
            b = rp.render_summary_block(t, set())
            assert "2 tasks · 1 waves · 2 files · 0/2 done" in b

        def test_done_truncated_to_80(self):
            long = "x" * 200
            t = [_task("1.1", "1", "a.py", long)]
            b = rp.render_summary_block(t, set())
            assert ("x" * 80 + "…") in b
            assert ("x" * 81) not in b

        def test_empty_tasks_minimal_block(self):
            b = rp.render_summary_block([], set())
            assert "No tasks defined yet" in b
            assert rp.SUMMARY_BEGIN in b and rp.SUMMARY_END in b

STEP 2 — run: python3 -m pytest skills/visual-planner/test_render_plan.py -k SummaryBlock -q  (expect FAIL).

STEP 3 — implement in render_plan.py, near the other builders (after build_stats is fine). NOTE: the
source must contain NO literal triple-backtick run (it would break the xml fences in plans that embed
it and the mask_fences parser) — build the mermaid fence via FENCE = chr(96)*3.

    SUMMARY_BEGIN = "<!-- AT-A-GLANCE:BEGIN (generated — do not edit; refreshed by render_plan.py --summarize) -->"
    SUMMARY_END = "<!-- AT-A-GLANCE:END -->"
    _SUMMARY_RE = re.compile(re.escape(SUMMARY_BEGIN) + r".*?" + re.escape(SUMMARY_END), re.DOTALL)
    _DONE_TRUNC = 80
    _FENCE = chr(96) * 3  # ``` without embedding a literal triple-backtick run in this source

    def _wave_sort_key(w):
        return (0, int(w)) if w.isdigit() else (1, w)  # numeric waves first, "—" last

    def _mermaid_node_id(task_id):
        return "T" + re.sub(r"[^0-9A-Za-z]", "_", task_id)

    def render_summary_block(tasks, done_ids):
        """Additive 'At a glance' block (both sentinels included). Pure + deterministic:
        no timestamps/randomness -> same input yields byte-identical output."""
        if not tasks:
            return f"{SUMMARY_BEGIN}\n## At a glance\n\n_No tasks defined yet._\n{SUMMARY_END}"
        files = set()
        for t in tasks:
            for f in t["files"].split(","):
                f = f.strip()
                if f:
                    files.add(f)
        waves = sorted({t["wave"] for t in tasks}, key=_wave_sort_key)
        ordered = sorted(tasks, key=lambda t: (_wave_sort_key(t["wave"]), natural_key(t["id"])))

        def title(t):
            return t.get("title") or t["id"]

        def cell(s):
            return str(s).replace("|", "\\|")  # keep a stray pipe from breaking the table

        def done_cell(t):
            d = " ".join(t["done"].split())
            return (d[:_DONE_TRUNC] + "…") if len(d) > _DONE_TRUNC else d

        count_line = (
            f"**{len(tasks)} tasks · {len(waves)} waves · "
            f"{len(files)} files · {len(done_ids)}/{len(tasks)} done**"
        )
        rows = ["| Wave | Task | Title | Files | Done (acceptance) |", "|---|---|---|---|---|"]
        for t in ordered:
            rows.append(
                f"| {cell(t['wave'])} | {cell(t['id'])} | {cell(title(t))} | "
                f"{cell(t['files'])} | {cell(done_cell(t))} |"
            )
        table = "\n".join(rows)

        mer = [f"{_FENCE}mermaid", "flowchart LR"]
        for idx, w in enumerate(waves):
            mer.append(f"  subgraph W{idx}[Wave {w}]")
            for t in [x for x in ordered if x["wave"] == w]:
                label = f"{t['id']} {title(t)}".replace('"', "'")
                mer.append(f'    {_mermaid_node_id(t["id"])}["{label}"]')
            mer.append("  end")
        for idx in range(len(waves) - 1):
            mer.append(f"  W{idx} --> W{idx + 1}")
        mer.append(_FENCE)
        mermaid = "\n".join(mer)

        checks = [
            f"- [{'x' if t['id'] in done_ids else ' '}] {t['id']} — {title(t)}" for t in ordered
        ]
        progress = "### Progress\n" + "\n".join(checks)

        inner = "\n\n".join(["## At a glance", count_line, table, mermaid, progress])
        return f"{SUMMARY_BEGIN}\n{inner}\n{SUMMARY_END}"

STEP 4 — run the same pytest -k SummaryBlock (expect PASS).
  </action>
  <verify>python3 -m pytest skills/visual-planner/test_render_plan.py -k SummaryBlock -q</verify>
  <done>All TestSummaryBlock cases pass; block is deterministic, count/checkbox/mermaid/truncation correct.</done>
</task>
```

### Task 2.1 — `inject_summary_block` (pure insert/replace, anchor before first `## `)

```xml
<task id="2.1" wave="2">
  <files>skills/visual-planner/render_plan.py, skills/visual-planner/test_render_plan.py</files>
  <action>
TDD as before.

STEP 1 — tests (in test_render_plan.py):

    class TestInjectSummaryBlock:
        BLOCK = rp.SUMMARY_BEGIN + "\nBODY\n" + rp.SUMMARY_END

        def test_inserts_before_first_h2_preserving_directive(self):
            text = "# Title\n\n> **For Claude:** directive\n\n## 1. Motivation\nfoo\n"
            out = rp.inject_summary_block(text, self.BLOCK)
            # H1 + directive stay above the block; block sits right before Motivation
            assert out.index("# Title") < out.index("> **For Claude:**") < out.index(rp.SUMMARY_BEGIN)
            assert out.index(rp.SUMMARY_END) < out.index("## 1. Motivation")

        def test_replaces_between_sentinels_idempotent(self):
            text = "# T\n\n" + rp.SUMMARY_BEGIN + "\nOLD\n" + rp.SUMMARY_END + "\n\n## 1. M\nx\n"
            out = rp.inject_summary_block(text, self.BLOCK)
            assert "OLD" not in out
            assert out.count(rp.SUMMARY_BEGIN) == 1  # not duplicated
            assert "BODY" in out and "x" in out and "## 1. M" in out
            # replacing again with the same block is a no-op
            assert rp.inject_summary_block(out, self.BLOCK) == out

        def test_no_h2_appends(self):
            text = "# Title\n\nsome prose only\n"
            out = rp.inject_summary_block(text, self.BLOCK)
            assert out.rstrip().endswith(rp.SUMMARY_END)
            assert "some prose only" in out

        def test_only_sentinel_region_touched(self):
            text = "# T\n\n> keep me\n\n## 1. M\nkeep body\n"
            out = rp.inject_summary_block(text, self.BLOCK)
            assert "> keep me" in out and "keep body" in out

STEP 2 — run: python3 -m pytest skills/visual-planner/test_render_plan.py -k InjectSummaryBlock -q  (FAIL).

STEP 3 — implement (next to render_summary_block):

    def inject_summary_block(plan_text, block):
        """Insert/replace the 'At a glance' block. Idempotent by sentinel.
        Both sentinels present -> replace the region between them (inclusive).
        Else insert `block` immediately before the first '## ' heading (keeping the
        H1 and any directive blockquote above it); no '## ' -> append; empty -> block."""
        if SUMMARY_BEGIN in plan_text and SUMMARY_END in plan_text:
            return _SUMMARY_RE.sub(lambda _m: block, plan_text, count=1)  # lambda: no backref parsing
        m = re.search(r"(?m)^##\s", plan_text)
        if m:
            return plan_text[: m.start()] + block + "\n\n" + plan_text[m.start() :]
        if plan_text.strip():
            return plan_text.rstrip("\n") + "\n\n" + block + "\n"
        return block + "\n"

STEP 4 — run pytest -k InjectSummaryBlock (PASS).

Rationale for whole-text search: frontmatter (--- ... ---) contains no '## ' heading and real plans put
'## 1. Motivation' before any '<task>' block, so the first '^## ' always lands in the body at the right
spot — no need to split frontmatter off.
  </action>
  <verify>python3 -m pytest skills/visual-planner/test_render_plan.py -k InjectSummaryBlock -q</verify>
  <done>Insert-before-first-## and replace-between-sentinels both pass; replace is idempotent; human prose untouched.</done>
</task>
```

### Task 3.1 — `summarize_plan_file` I/O + `--summarize` CLI + HTML strip

```xml
<task id="3.1" wave="3">
  <files>skills/visual-planner/render_plan.py, skills/visual-planner/test_render_plan.py</files>
  <action>
TDD.

STEP 1 — tests (in test_render_plan.py). Use pytest tmp_path.

    _PLAN = (
        "---\nslug: demo\nstatus: active\nowner: X\ncreated: 2026-07-15\n---\n\n"
        "# Demo plan\n\n> **For Claude:** directive\n\n## 1. Motivation\nwhy\n\n"
        "## 4. Tasks\n\n### Task 1.1 — first\n\n```xml\n"
        "<task id=\"1.1\" wave=\"1\">\n<files>a.py</files>\n<action>do</action>\n"
        "<verify>true</verify>\n<done>done</done>\n</task>\n```\n\n"
        "## Status Log\n\n- 2026-07-15 — 1.1 complete ✓\n"
    )

    class TestSummarizePlanFile:
        def test_injects_and_reports_written(self, tmp_path):
            p = tmp_path / "PLAN.md"
            p.write_text(_PLAN, encoding="utf-8")
            wrote = rp.summarize_plan_file(p)
            assert wrote is True
            out = p.read_text(encoding="utf-8")
            assert rp.SUMMARY_BEGIN in out
            assert "- [x] 1.1 — first" in out           # done derived from Status Log
            assert out.index("> **For Claude:**") < out.index(rp.SUMMARY_BEGIN) < out.index("## 1. Motivation")

        def test_second_run_is_noop(self, tmp_path):
            p = tmp_path / "PLAN.md"
            p.write_text(_PLAN, encoding="utf-8")
            rp.summarize_plan_file(p)
            before = p.read_text(encoding="utf-8")
            wrote2 = rp.summarize_plan_file(p)
            assert wrote2 is False
            assert p.read_text(encoding="utf-8") == before

    class TestHtmlStripsSummaryRegion:
        def test_render_ignores_generated_block(self, tmp_path):
            p = tmp_path / "PLAN.md"
            p.write_text(_PLAN, encoding="utf-8")
            rp.summarize_plan_file(p)                    # inject the block first
            html, warnings, meta = rp.render(p, None)
            # the generated markdown must not survive into HTML as its own section
            assert "AT-A-GLANCE" not in html
            assert meta["n_tasks"] == 1                  # task parsing unaffected

STEP 2 — run: python3 -m pytest skills/visual-planner/test_render_plan.py -k "SummarizePlanFile or HtmlStrips" -q  (FAIL).

STEP 3a — implement summarize_plan_file (next to the others):

    def summarize_plan_file(plan_path):
        """Read -> build block -> inject -> write only if changed. Returns True if written."""
        text = plan_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        fm, body = parse_frontmatter(text)
        tasks, _ = extract_tasks(body)
        attach_titles(tasks, body)
        done_ids = set()
        for disp, _tok, content in split_sections(body)[1]:
            if disp.lower() == "status log":
                entries = parse_status_entries(content)
                done_ids = _done_task_ids(entries, [t["id"] for t in tasks])
                break
        block = render_summary_block(tasks, done_ids)
        new_text = inject_summary_block(text, block)
        if new_text != text:
            plan_path.write_text(new_text, encoding="utf-8")
            return True
        return False

STEP 3b — HTML strip: in render(), immediately after `fm, body = parse_frontmatter(text)`, add:

        body = _SUMMARY_RE.sub("", body)  # drop the generated 'At a glance' block; HTML has its own view

STEP 3c — CLI flag in main(): add `summarize = False` beside the other flag vars; add a branch
`elif a == "--summarize": summarize = True` BEFORE the `elif a.startswith("--")` catch-all; then right
after `plan_path = resolve_input(positionals[0])` add:

        if summarize:
            summarize_plan_file(plan_path)

Also extend USAGE to include `[--summarize]`.

STEP 4 — run pytest -k "SummarizePlanFile or HtmlStrips" (PASS), then the FULL file for regression:
python3 -m pytest skills/visual-planner/test_render_plan.py -q  (all 43 existing + new PASS).
  </action>
  <verify>python3 -m pytest skills/visual-planner/test_render_plan.py -q</verify>
  <done>summarize writes once then no-ops; done derived from Status Log; HTML strips the region; full suite green.</done>
</task>
```

### Task 4.1 — Wire `--summarize` through the hook + extend the contract test

```xml
<task id="4.1" wave="4">
  <files>hooks/render-plan-on-write.sh, tests/hooks/render-plan-on-write.test.sh</files>
  <action>
STEP 1 — in hooks/render-plan-on-write.sh, change the render invocation from:
    OUT=$(python3 "$RENDER" "$FILE" 2>&1)
to:
    OUT=$(python3 "$RENDER" "$FILE" --summarize 2>&1)

Also update the top comment "Won't loop (it writes PLAN.html, not PLAN.md)." to state the real reason,
since it now also writes PLAN.md:
    # Won't loop: render_plan.py writes via subprocess (not the Write/Edit tool), so PostToolUse
    # does not re-fire; and --summarize is a no-op when the block is already current.

STEP 2 — extend tests/hooks/render-plan-on-write.test.sh with a case that feeds a real PLAN.md fixture
(front-matter + one wave=1 xml task + a '## Status Log') to the hook via stdin JSON
({"tool_input":{"file_path":"<fixture>"}}), then asserts:
  (a) the fixture PLAN.md now CONTAINS 'AT-A-GLANCE:BEGIN' (block injected);
  (b) capturing the file bytes, running the hook a SECOND time leaves the file byte-identical (no-op).
Follow the existing test's harness/fixture idiom (inline heredoc fixture, temp dir, exit-0 assertion).

STEP 3 — run the contract test.
  </action>
  <verify>bash tests/hooks/render-plan-on-write.test.sh</verify>
  <done>Hook passes --summarize; new contract case shows block injected on save and idempotent on re-run; all cases exit 0.</done>
</task>
```

### Task 4.2 — Document the additive block (format rule + writing-plans)

```xml
<task id="4.2" wave="4">
  <files>rules/plan-format.md, skills/writing-plans/SKILL.md</files>
  <action>
Document the derived block as ADDITIVE, DERIVED, and NEVER the source of truth (agents still author and
parse only the `<task>` blocks).

STEP 1 — in rules/plan-format.md, add a short subsection (near "Rendering requirement") titled
"Auto-generated 'At a glance' block" stating: render_plan.py --summarize injects an idempotent,
sentinel-delimited (AT-A-GLANCE:BEGIN/END) summary immediately before the first '## ' heading; it is
derived from the `<task>` blocks + `## Status Log`; do not hand-edit inside the sentinels; the hook
regenerates it on every PLAN.md save.

STEP 2 — in skills/writing-plans/SKILL.md, in the "Visual Render Handoff" section, add one line noting
that besides PLAN.html, the same hook now injects the additive 'At a glance' block into the tracked
PLAN.md (deterministic, script-owned) so the plan is human-readable on GitHub without tooling.

Keep both edits factual and minimal — no format change to the `<task>` schema.
  </action>
  <verify>grep -q "AT-A-GLANCE" rules/plan-format.md && grep -qi "at a glance" skills/writing-plans/SKILL.md</verify>
  <done>Both docs describe the additive derived block; no change to the task schema.</done>
</task>
```

### Task 5.1 — Integration & regression gate

```xml
<task id="5.1" wave="5">
  <files>skills/visual-planner/test_render_plan.py</files>
  <action>
Final gate — no new production code. Confirm the whole surface is green together and nothing regressed.

STEP 1 — run the full renderer suite: python3 -m pytest skills/visual-planner/test_render_plan.py -q
  Expect: all 43 pre-existing cases + every new TestSummaryBlock / TestInjectSummaryBlock /
  TestSummarizePlanFile / TestHtmlStripsSummaryRegion case PASS.
STEP 2 — run the hook contract test: bash tests/hooks/render-plan-on-write.test.sh (all exit 0).
STEP 3 — if either fails, fix in the owning task (do not patch here); this task only certifies green.

(If any assertion count needs a home, add a single belt-and-suspenders test asserting a full
round-trip: build a plan string, inject via summarize_plan_file on a tmp file, render() it, and assert
'AT-A-GLANCE' absent from HTML while the task/wave counts are intact.)
  </action>
  <verify>python3 -m pytest skills/visual-planner/test_render_plan.py -q && bash tests/hooks/render-plan-on-write.test.sh</verify>
  <done>Full renderer suite + hook contract test both green; feature integrated end to end.</done>
</task>
```

## 5. Risks

| Risk | Mitigation |
|---|---|
| `render_plan.py` now mutates its input file | Opt-in `--summarize` only; explicit sentinels; write-only-if-changed; bare invocation + 43 tests unchanged (Task 3.1 regression). |
| Corrupting human prose / directive blockquote | Injection anchored before first `## ` (Task 2.1); only the sentinel region is ever replaced. |
| Diff churn on re-save | Full determinism (no timestamps/randomness) + byte-equality no-op (Task 1.1 `test_deterministic`, Task 3.1 `test_second_run_is_noop`). |
| Literal triple-backtick in source breaks fenced plans / `mask_fences` | Mermaid fence built via `FENCE = chr(96)*3` — no triple-backtick run in the source. |
| HTML duplicate "At a glance" section | `_SUMMARY_RE` strip in `render()` before parsing (Task 3.1 `TestHtmlStripsSummaryRegion`). |
| Hook loop | Subprocess write ≠ Write/Edit tool → no PostToolUse re-fire; no-op-on-unchanged is belt-and-suspenders (hook comment updated in Task 4.1). |

## 6. Wave / parallelism map

| Wave | Tasks | Parallelism | Files (disjoint within wave) |
|------|-------|-------------|------------------------------|
| 1 | 1.1 | single | render_plan.py, test_render_plan.py |
| 2 | 2.1 | single | render_plan.py, test_render_plan.py |
| 3 | 3.1 | single | render_plan.py, test_render_plan.py |
| 4 | 4.1, 4.2 | 2 parallel | 4.1: hooks/render-plan-on-write.sh, tests/hooks/render-plan-on-write.test.sh · 4.2: rules/plan-format.md, skills/writing-plans/SKILL.md |
| 5 | 5.1 | single | test_render_plan.py (verify-only) |

Waves 1–3 are sequential because every task edits `render_plan.py` + `test_render_plan.py` (no
same-wave file-disjointness possible). Wave 4's two tasks touch disjoint files and run in parallel.

## 7. Status Log

- 2026-07-15 — Plan drafted from design.md + research-brief.md (scope A+B, high-risk lane). status: proposed.
- 2026-07-15 — Execution started on worktree `feat/plan-at-a-glance`; status: active.
  - Wave 1 (render_summary_block) complete: `60df278`, `2144659` (quality: intersect done count).
  - Wave 2 (inject_summary_block) complete: `72a22ea`, `ce276cf` (quality: DRY wave-sort, orphan-sentinel guard). ✓
  - Wave 3 (summarize_plan_file + --summarize + HTML strip) complete: `0b959f6`, `e14aa30`. ✓
  - Wave 4 (hook wiring ‖ docs) complete: `5449410`, `9ad3be8`. ✓
  - Wave 5 gate: full render suite 76 passed; hook contract 5 passed. ✓
  - Known limitation: this meta-plan parses to 0 tasks (its task actions embed literal `<task>` fixture
    strings), so `--summarize` on THIS PLAN.md would emit a degenerate "No tasks defined yet" block.
    Normal plans summarize correctly (verified by the hook contract test's clean fixture). Left un-self-injected.
