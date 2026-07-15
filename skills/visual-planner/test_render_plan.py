"""Tests for the visual-planner renderer's intro-card pipeline.

Focus: the fuzzy-boundary logic that is easy to silently regress —
clause splitting, verb classification, field rendering, multi-line field
capture, and frontmatter hardening. Run:

    python -m pytest .claude/skills/visual-planner/test_render_plan.py -q
"""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "render_plan", Path(__file__).resolve().parent / "render_plan.py"
)
assert _SPEC and _SPEC.loader, "could not load render_plan.py"
rp = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rp)


# --------------------------------------------------------------------------- #
# _split_clauses — must break the dense Architecture wall WITHOUT shattering
# dotted identifiers / decimals.
# --------------------------------------------------------------------------- #
class TestSplitClauses:
    def test_splits_on_semicolon(self):
        assert rp._split_clauses("Keep A; replace B; add C") == [
            "Keep A",
            "replace B",
            "add C",
        ]

    def test_splits_sentences_before_capital(self):
        out = rp._split_clauses("Adapt the core. Keep the module.")
        assert out == ["Adapt the core.", "Keep the module."]

    def test_does_not_split_dotted_identifier_in_backticks(self):
        # `render.yaml` / `sessionmanager.session()` must stay intact: the '.'
        # is followed by a backtick, never whitespace.
        out = rp._split_clauses("add one service to `render.yaml`")
        assert out == ["add one service to `render.yaml`"]

    def test_does_not_split_decimal_version(self):
        # "2.0 (asyncpg)" — '(' is an open char but the '.' has no trailing space
        out = rp._split_clauses("async SQLAlchemy 2.0 (asyncpg) via X")
        assert out == ["async SQLAlchemy 2.0 (asyncpg) via X"]

    def test_does_not_split_lowercase_sentence_continuation(self):
        # "e.g. foo" — lowercase after the period -> not a sentence boundary
        assert rp._split_clauses("uses a cache e.g. redis here") == [
            "uses a cache e.g. redis here"
        ]

    def test_single_clause_returns_one(self):
        assert len(rp._split_clauses("One cohesive goal statement.")) == 1


# --------------------------------------------------------------------------- #
# _classify_clause — priority-ordered verb map.
# --------------------------------------------------------------------------- #
class TestClassifyClause:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("add one type: cron service to render.yaml", "add"),
            ("New MDX pages plug into docs", "add"),
            ("expose a filtered OpenAPI subset", "add"),
            ("Keep process_change and the pure module", "keep"),
            ("Reuse existing requests_count metric", "keep"),
            ("replace the git-diff front end", "change"),
            ("public_schema.py swaps security constants", "change"),
            ("Extend apply.sh with _upsert_monitor", "change"),
            ("delete the unreachable git-diff path", "remove"),
            ("No migration, no new dependency", "exclude"),
            ("All work is Datadog config under infra", "note"),
        ],
    )
    def test_categories(self, text, expected):
        assert rp._classify_clause(text) == expected

    def test_negation_beats_bare_change_verb(self):
        # "no backend code-path changes" contains "changes" but is an exclusion.
        assert rp._classify_clause("no backend code-path changes") == "exclude"

    def test_mutation_beats_incidental_existing(self):
        # "Existing logger swapped" describes a CHANGE, not a KEEP, even though
        # the keep-keyword "existing" appears first.
        assert rp._classify_clause("Existing stdlib logger swapped to JSON") == "change"


# --------------------------------------------------------------------------- #
# _render_field_value — routing per field.
# --------------------------------------------------------------------------- #
class TestRenderFieldValue:
    def test_tech_stack_renders_chips(self):
        html = rp._render_field_value(
            "Tech Stack", "Python 3.12, PyYAML, `anthropic==0.63.0`."
        )
        assert html.count('class="tech-chip"') == 3
        assert "Python 3.12" in html
        assert 'tech-chip">.' not in html  # trailing-period chip stripped

    def test_architecture_renders_change_map(self):
        html = rp._render_field_value("Architecture", "Keep A; add B; No migration")
        assert 'class="change-map"' in html
        assert 'data-act="keep"' in html
        assert 'data-act="add"' in html
        assert 'data-act="exclude"' in html

    def test_architecture_single_clause_is_paragraph(self):
        html = rp._render_field_value("Architecture", "One cohesive sentence only.")
        assert html.startswith("<p>") and "change-map" not in html

    def test_goal_multiclause_is_bullets(self):
        html = rp._render_field_value("Goal", "Do X. Then Y happens.")
        assert 'class="intro-list"' in html and html.count("<li>") == 2

    def test_goal_single_clause_is_paragraph(self):
        html = rp._render_field_value("Goal", "Ship the thing safely.")
        assert html.startswith("<p>")


# --------------------------------------------------------------------------- #
# build_intro_card — multi-line capture (the original truncation bug).
# --------------------------------------------------------------------------- #
class TestBuildIntroCard:
    def test_captures_multiline_field_in_full(self):
        intro = (
            "**Goal:** Run the core on a **weekly cron\njob** preserving `aliases`.\n"
        )
        html = rp.build_intro_card(intro)
        # wrapped value joined -> bold spanning the line break closes correctly
        assert "<strong>weekly cron job</strong>" in html
        assert "preserving" in html

    def test_no_fields_returns_empty(self):
        assert rp.build_intro_card("Just prose, no labelled fields.") == ""


# --------------------------------------------------------------------------- #
# parse_frontmatter — hardened against an unterminated block.
# --------------------------------------------------------------------------- #
class TestParseFrontmatter:
    def test_valid_block(self):
        fm, body = rp.parse_frontmatter(
            "---\nslug: x\nstatus: active\n---\n\n# Title\n"
        )
        assert fm == {"slug": "x", "status": "active"}
        assert body.startswith("# Title")

    def test_unterminated_block_does_not_swallow_body(self):
        # No closing '---'; a heading appears -> treat as NO frontmatter so the
        # body (and any intro fields) survive instead of being parsed as junk.
        text = "---\n\n## slug: x\nstatus: active\n\n# Title\n\n**Goal:** keep me\n"
        fm, body = rp.parse_frontmatter(text)
        assert fm == {}
        assert "**Goal:** keep me" in body

    def test_no_frontmatter(self):
        fm, body = rp.parse_frontmatter("# Title\n\nbody")
        assert fm == {} and body == "# Title\n\nbody"


# --------------------------------------------------------------------------- #
# Section list parser — pre/items/post split with continuation folding.
# --------------------------------------------------------------------------- #
class TestMdListItems:
    def test_pre_items_post(self):
        pre, items, post = rp._md_list_items(
            "Intro line.\n- one\n- two\n\nTrailing prose."
        )
        assert "Intro line." in pre
        assert items == ["one", "two"]
        assert "Trailing prose." in post

    def test_folds_continuation_lines(self):
        _, items, _ = rp._md_list_items("- first item that\n  wraps here\n- second")
        assert items == ["first item that wraps here", "second"]

    def test_no_list_returns_empty_items(self):
        pre, items, _ = rp._md_list_items("Just a paragraph, no bullets.")
        assert items == [] and "paragraph" in pre


# --------------------------------------------------------------------------- #
# Risks -> severity register cards.
# --------------------------------------------------------------------------- #
class TestRenderRisks:
    def test_explicit_severity_tag_extracted_and_stripped(self):
        html = rp.render_risks(
            "- **Risk #1 (Medium)** — Streaming integration. Mitigation: do X."
        )
        assert 'data-sev="medium"' in html
        assert 'risk-sev" data-sev="medium">medium</span>' in html
        assert "(Medium)" not in html  # tag becomes a chip, removed from title
        assert "Risk #1" in html

    def test_real_maps_high_low_maps_low(self):
        assert 'data-sev="high"' in rp.render_risks("- **R (Real)** — body")
        assert 'data-sev="low"' in rp.render_risks("- **R (Low)** — body")

    def test_leading_known_is_medium(self):
        html = rp.render_risks("- **Anti-drift** — KNOWN; lands in same commit.")
        assert 'data-sev="medium"' in html

    def test_untagged_risk_is_neutral(self):
        html = rp.render_risks("- **Staleness** — weekly cadence, tunable.")
        assert 'data-sev="none"' in html
        assert "risk-sev" not in html  # no fabricated severity chip

    def test_mitigation_split(self):
        html = rp.render_risks("- **R** — bad thing happens. Mitigation: guard clause.")
        assert "risk-mit-label" in html and "guard clause" in html

    def test_table_stays_table(self):
        content = "| # | Risk | Mitigation |\n|---|---|---|\n| P1 | x | y |"
        html = rp.render_risks(content)
        assert "<table>" in html and "risk-card" not in html


# --------------------------------------------------------------------------- #
# Success -> checklist; Non-goals -> scope-out; Motivation -> callout.
# --------------------------------------------------------------------------- #
class TestOtherSectionRenderers:
    def test_success_checklist_and_arrow(self):
        html = rp.render_success("- no changes → 0 drafts\n- modified → one draft")
        assert html.count('class="check-item"') == 2
        assert html.count('class="then-arrow"') == 2

    def test_success_table_stays_table(self):
        html = rp.render_success("| a | b |\n|---|---|\n| 1 | 2 |")
        assert "<table>" in html and "check-item" not in html

    def test_nongoals_scope_out(self):
        html = rp.render_nongoals("- No auto-publish\n- No new dependency")
        assert html.count("scope-mark") == 2 and "⊘" in html

    def test_motivation_callout(self):
        html = rp.render_motivation("The committed core only runs from a git diff.")
        assert html.startswith('<div class="callout">') and "git diff" in html


# --------------------------------------------------------------------------- #
# Status log — relaxed grammar, classification, sub-bullets, collapse, progress.
# --------------------------------------------------------------------------- #
class TestStatusLog:
    def test_em_dash_and_colon_separators(self):
        e = rp.parse_status_entries(
            "- 2026-05-20 — built it\n- 2026-05-21: drafted plan"
        )
        assert [x["date"] for x in e] == ["2026-05-20", "2026-05-21"]
        assert e[0]["note"] == "built it" and e[1]["note"] == "drafted plan"

    def test_folds_continuation_and_subbullets(self):
        e = rp.parse_status_entries(
            "- 2026-05-20 — P1 complete. All tasks\n"
            "  done and verified\n"
            "  - P1.1 ✓ STATE.md\n"
            "  - P1.2 ✓ ROADMAP.md"
        )
        assert len(e) == 1
        assert "done and verified" in e[0]["note"]
        assert e[0]["subs"] == ["P1.1 ✓ STATE.md", "P1.2 ✓ ROADMAP.md"]

    @pytest.mark.parametrize(
        "note,kind",
        [
            ("Original CORE built; 54 tests passed", "build"),
            ("Client answered ENG-409: weekly cron", "decision"),
            ("Design + research-brief finalized", "plan"),
            ("Open ops items: ownership unresolved", "open"),
            ("Renamed the helper for clarity", "note"),
        ],
    )
    def test_kind_classification(self, note, kind):
        assert rp.parse_status_entries(f"- 2026-05-20 — {note}")[0]["kind"] == kind

    def test_plan_outranks_open_when_both_present(self):
        e = rp.parse_status_entries(
            "- 2026-05-21 — design finalized; open ops items remain"
        )
        assert e[0]["kind"] == "plan"

    def test_done_task_ids_from_checkmarks(self):
        e = rp.parse_status_entries(
            "- 2026-05-20 — P1 complete\n  - P1.1 ✓ x\n  - P1.2 ✓ y"
        )
        assert rp._done_task_ids(e, ["P1.1", "P1.2", "P2.1"]) == {"P1.1", "P1.2"}

    def test_done_task_ids_intersects_real_tasks(self):
        e = rp.parse_status_entries("- 2026-05-20 — finished 9.9 complete")
        assert rp._done_task_ids(e, ["1.1"]) == set()  # 9.9 isn't a real task

    def test_long_log_collapses_older(self):
        log = "\n".join(f"- 2026-05-{d:02d} — update {d}" for d in range(1, 12))  # 11
        html, entries = rp.render_timeline(log)
        assert len(entries) == 11
        assert '<details class="timeline-fold">' in html
        assert "Show 6 earlier updates" in html  # 11 - 5 kept

    def test_short_log_no_collapse(self):
        html, _ = rp.render_timeline("- 2026-05-20 — a\n- 2026-05-21 — b")
        assert "timeline-fold" not in html and html.count("timeline-entry") == 2

    def test_kind_data_attr_rendered(self):
        html, _ = rp.render_timeline("- 2026-05-20 — built and verified")
        assert 'data-kind="build"' in html and 't-kind" data-kind="build"' in html


# --------------------------------------------------------------------------- #
# Output path by mode — a --review render must NOT clobber the plain PLAN.html,
# since an auto plain-render fires after every plan approval.
# --------------------------------------------------------------------------- #
class TestOutputPathByMode:
    _PLAN = (
        "---\nslug: demo-out\nstatus: proposed\nowner: t\ncreated: 2026-05-22\n---\n\n"
        "# Demo\n\n## 1. Motivation\nx\n\n## 4. Tasks\n\n"
        '<task id="1.1" wave="1">\n<files>a.py</files>\n<action>do</action>\n'
        "<verify>true</verify>\n<done>ok</done>\n</task>\n"
    )

    def test_plain_render_writes_plan_html(self, tmp_path):
        plan = tmp_path / "PLAN.md"
        plan.write_text(self._PLAN, encoding="utf-8")
        rp.main(["render_plan.py", str(plan)])
        assert (tmp_path / "PLAN.html").exists()
        assert not (tmp_path / "PLAN.review.html").exists()

    def test_review_render_writes_separate_file(self, tmp_path):
        plan = tmp_path / "PLAN.md"
        plan.write_text(self._PLAN, encoding="utf-8")
        sidecar = tmp_path / ".plan-review.json"
        sidecar.write_text(
            '{"base":"t","files":[{"path":"a.py","status":"new","risk":"low"}]}',
            encoding="utf-8",
        )
        rp.main(["render_plan.py", str(plan), "--review", str(sidecar)])
        assert (tmp_path / "PLAN.review.html").exists()
        assert not (tmp_path / "PLAN.html").exists()


# --------------------------------------------------------------------------- #
# render_summary_block — pure, deterministic "At a glance" block builder.
# --------------------------------------------------------------------------- #
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
        # multiple done ids + multiple files so set-iteration order could differ between runs
        assert rp.render_summary_block(self._tasks(), {"1.1", "2.1"}) == rp.render_summary_block(
            self._tasks(), {"1.1", "2.1"}
        )

    def test_count_ignores_unknown_done_ids(self):
        # a stale Status-Log id not among the tasks must not inflate the done count
        b = rp.render_summary_block(self._tasks(), {"1.1", "9.9"})
        assert "**3 tasks · 2 waves · 4 files · 1/3 done**" in b

    def test_has_both_sentinels(self):
        b = rp.render_summary_block(self._tasks(), set())
        assert rp.SUMMARY_BEGIN in b and rp.SUMMARY_END in b
        assert b.startswith(rp.SUMMARY_BEGIN) and b.rstrip().endswith(rp.SUMMARY_END)

    def test_count_line(self):
        b = rp.render_summary_block(self._tasks(), {"1.1"})
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
        b = rp.render_summary_block([_task("3.1", "1", "a.py", "done text")], set())
        assert "- [ ] 3.1 — 3.1" in b

    def test_all_dash_waves_count_one_wave(self):
        t = [_task("1", "—", "a.py", "d"), _task("2", "—", "b.py", "d")]
        assert "2 tasks · 1 waves · 2 files · 0/2 done" in rp.render_summary_block(t, set())

    def test_done_truncated_to_80(self):
        b = rp.render_summary_block([_task("1.1", "1", "a.py", "x" * 200)], set())
        assert ("x" * 80 + "…") in b
        assert ("x" * 81) not in b

    def test_empty_tasks_minimal_block(self):
        b = rp.render_summary_block([], set())
        assert "No tasks defined yet" in b
        assert rp.SUMMARY_BEGIN in b and rp.SUMMARY_END in b


class TestInjectSummaryBlock:
    BLOCK = rp.SUMMARY_BEGIN + "\nBODY\n" + rp.SUMMARY_END

    def test_inserts_before_first_h2_preserving_directive(self):
        text = "# Title\n\n> **For Claude:** directive\n\n## 1. Motivation\nfoo\n"
        out = rp.inject_summary_block(text, self.BLOCK)
        assert out.index("# Title") < out.index("> **For Claude:**") < out.index(rp.SUMMARY_BEGIN)
        assert out.index(rp.SUMMARY_END) < out.index("## 1. Motivation")

    def test_replaces_between_sentinels_idempotent(self):
        text = "# T\n\n" + rp.SUMMARY_BEGIN + "\nOLD\n" + rp.SUMMARY_END + "\n\n## 1. M\nx\n"
        out = rp.inject_summary_block(text, self.BLOCK)
        assert "OLD" not in out
        assert out.count(rp.SUMMARY_BEGIN) == 1
        assert "BODY" in out and "x" in out and "## 1. M" in out
        assert rp.inject_summary_block(out, self.BLOCK) == out  # re-inject is a no-op

    def test_no_h2_appends(self):
        text = "# Title\n\nsome prose only\n"
        out = rp.inject_summary_block(text, self.BLOCK)
        assert out.rstrip().endswith(rp.SUMMARY_END)
        assert "some prose only" in out

    def test_only_sentinel_region_touched(self):
        text = "# T\n\n> keep me\n\n## 1. M\nkeep body\n"
        out = rp.inject_summary_block(text, self.BLOCK)
        assert "> keep me" in out and "keep body" in out

    def test_half_present_sentinel_does_not_swallow_content(self):
        # only BEGIN survives (END was hand-deleted from the "do not edit" region)
        text = "# T\n\n" + rp.SUMMARY_BEGIN + "\nORPHAN\n\n## 1. M\nkeep body\n"
        out = rp.inject_summary_block(text, self.BLOCK)
        assert out.count(rp.SUMMARY_BEGIN) == 1  # orphan stripped, one fresh BEGIN
        assert out.count(rp.SUMMARY_END) == 1
        assert "keep body" in out and "BODY" in out
        # a second inject is now a clean region-replace, content still preserved
        out2 = rp.inject_summary_block(out, self.BLOCK)
        assert "keep body" in out2 and out2.count(rp.SUMMARY_BEGIN) == 1


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
        assert rp.summarize_plan_file(p) is True
        out = p.read_text(encoding="utf-8")
        assert rp.SUMMARY_BEGIN in out
        assert "- [x] 1.1 — first" in out
        assert out.index("> **For Claude:**") < out.index(rp.SUMMARY_BEGIN) < out.index("## 1. Motivation")

    def test_second_run_is_noop(self, tmp_path):
        p = tmp_path / "PLAN.md"
        p.write_text(_PLAN, encoding="utf-8")
        rp.summarize_plan_file(p)
        before = p.read_text(encoding="utf-8")
        assert rp.summarize_plan_file(p) is False
        assert p.read_text(encoding="utf-8") == before

    def test_no_status_log_all_unchecked(self, tmp_path):
        # a plan without a '## Status Log' section -> empty done set, 0/N done
        p = tmp_path / "PLAN.md"
        p.write_text(_PLAN.replace("## Status Log\n\n- 2026-07-15 — 1.1 complete ✓\n", ""), encoding="utf-8")
        assert rp.summarize_plan_file(p) is True
        out = p.read_text(encoding="utf-8")
        assert "1 tasks · 1 waves · 1 files · 0/1 done" in out
        assert "- [ ] 1.1 — first" in out


class TestHtmlStripsSummaryRegion:
    def test_render_ignores_generated_block(self, tmp_path):
        p = tmp_path / "PLAN.md"
        p.write_text(_PLAN, encoding="utf-8")
        rp.summarize_plan_file(p)
        html, warnings, meta = rp.render(p, None)
        assert "AT-A-GLANCE" not in html
        assert meta["n_tasks"] == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
