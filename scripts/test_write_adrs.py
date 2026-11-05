"""Tests for plugins/harness/scripts/write_adrs.py."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "plugins/harness/scripts/write_adrs.py"
TEMPLATE = Path(__file__).resolve().parent.parent / "docs/adr/TEMPLATE.md"


def dec(**kw):
    d = {
        "ticket": 1, "stage": "design", "title": "Use a queue", "context": "c",
        "options": ["a", "b"], "decision": "a", "why": "w", "consequences": "q",
        "how_to_reverse": "git revert", "confidence": "medium", "needs_review": True, "adr": True,
        "decided_by": "claude",
    }
    d.update(kw)
    if "context" not in kw:
        d["context"] = f"context of {d['title']}"   # distinct per title, so only the title can merge
    return d


def setup(tmp_path, decisions, existing=("0001-workflow-capabilities.md",)):
    adr = tmp_path / "adr"
    adr.mkdir()
    (adr / "README.md").write_text("r")
    (adr / "TEMPLATE.md").write_text(TEMPLATE.read_text())
    for name in existing:
        (adr / name).write_text("x")
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps({"run": "r", "decisions": decisions}))
    return adr, inp


def run(adr, inp, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(inp), "--adr-dir", str(adr), *extra],
        capture_output=True, text=True,
    )


def test_numbers_continue_after_0001(tmp_path):
    adr, inp = setup(tmp_path, [dec(title="One"), dec(title="Two")])
    r = run(adr, inp)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert [o["number"] for o in out] == ["0002", "0003"]
    assert (adr / "0002-one.md").is_file() and (adr / "0003-two.md").is_file()
    text = (adr / "0002-one.md").read_text()
    assert "status: proposed" in text and "# 0002. One" in text and "- a\n- b" in text


def test_files_are_ordered_by_ticket_then_stage(tmp_path):
    ds = [dec(title="a", ticket=2), dec(title="b", ticket=1, stage="plan"),
          dec(title="c", ticket=9), dec(title="d", ticket=1, stage="design"),
          dec(title="e", ticket=1, adr=False)]   # table only: no file
    adr, inp = setup(tmp_path, ds)
    out = json.loads(run(adr, inp).stdout)
    assert [o["title"] for o in out] == ["d", "b", "a", "c"]
    assert "status: proposed" in (adr / "0002-d.md").read_text()


def test_slug_rules_and_collision(tmp_path):
    long = "Ünïcode Title! " + "x" * 100
    adr, inp = setup(tmp_path, [dec(title=long), dec(title="Same"), dec(title="Same", ticket=2)])
    out = json.loads(run(adr, inp).stdout)
    names = [Path(o["path"]).name for o in out]
    assert len(set(names)) == 3
    for n in names:
        slug = n[5:-3]
        assert len(slug) <= 60 and slug == slug.lower() and slug.isascii()
    # collision with an existing slug at the same number cannot happen; same-title runs differ by number
    assert names[1].endswith("same.md") and names[2].endswith("same.md")


def test_ignores_readme_template_and_nonadr_files(tmp_path):
    adr, inp = setup(tmp_path, [dec()], existing=("0001-a.md", "0007-b.md", "notes.md", "12-x.md"))
    out = json.loads(run(adr, inp).stdout)
    assert out[0]["number"] == "0008"


def test_empty_dir_starts_at_0001(tmp_path):
    adr, inp = setup(tmp_path, [dec()], existing=())
    assert json.loads(run(adr, inp).stdout)[0]["number"] == "0001"


def test_refuse_overwrite(tmp_path, monkeypatch, capsys):
    sys.path.insert(0, str(SCRIPT.parent))
    import write_adrs

    adr, inp = setup(tmp_path, [dec(title="One")])
    (adr / "0002-one.md").write_text("keep")
    # simulate a race: the plan was made before another writer created the file
    item = {"number": "0002", "path": str(adr / "0002-one.md"), "ticket": 1, "stage": "design",
            "title": "One", "needs_review": False, "adr": True, "_text": "new"}
    monkeypatch.setattr(write_adrs, "plan", lambda *a: [item])
    monkeypatch.setattr(sys, "argv", ["w", "--input", str(inp), "--adr-dir", str(adr)])
    assert write_adrs.main() == 2
    assert "refusing to overwrite" in capsys.readouterr().err
    assert (adr / "0002-one.md").read_text() == "keep"


def test_numbering_skips_existing_slug(tmp_path):
    adr, inp = setup(tmp_path, [dec(title="One")])
    (adr / "0002-one.md").write_text("keep")
    assert run(adr, inp).returncode == 0
    assert (adr / "0002-one.md").read_text() == "keep"
    assert (adr / "0003-one.md").is_file()


def test_bad_input_exit_2(tmp_path):
    adr, inp = setup(tmp_path, [dec()], existing=())
    for bad in ({"decisions": []}, {"decisions": [dec(confidence="x")]},
                {"decisions": [dec(needs_review="yes")]}, {"decisions": [dec(adr="yes")]},
                {"decisions": [{k: v for k, v in dec().items() if k != "adr"}]},
                {"decisions": [{k: v for k, v in dec().items() if k != "why"}]}):
        inp.write_text(json.dumps(bad))
        r = run(adr, inp)
        assert r.returncode == 2 and "write_adrs:" in r.stderr
    inp.write_text("not json")
    assert run(adr, inp).returncode == 2


def test_dry_run_writes_nothing(tmp_path):
    adr, inp = setup(tmp_path, [dec(title="One")])
    before = sorted(p.name for p in adr.iterdir())
    r = run(adr, inp, "--dry-run")
    assert r.returncode == 0 and json.loads(r.stdout)[0]["number"] == "0002"
    assert sorted(p.name for p in adr.iterdir()) == before


def test_render_section(tmp_path):
    adr, inp = setup(tmp_path, [dec(title="Plain"), dec(title="Risky", ticket=5)])
    written = tmp_path / "w.json"
    written.write_text(run(adr, inp, "--dry-run").stdout)
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--render-section", str(written), "--artifact", "https://x/y"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    s = r.stdout
    assert s.startswith("## Decisions") and "Artifact: https://x/y" in s
    assert "- [ADR 0003](docs/adr/0003-risky.md) (#5, design): Risky" in s
    assert "- [ADR 0002](docs/adr/0002-plain.md) (#1, design): Plain" in s
    assert s.index("Plain") < s.index("Risky")


def test_fill_count_replaces_placeholder(tmp_path):
    written = tmp_path / "w.json"
    written.write_text('[{"number": "0002"}, {"number": "0003"}]')
    body = tmp_path / "b.md"
    body.write_text("- [x] ADR files: {{ADR_COUNT}}\n")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--fill-count", str(body), "--written", str(written)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert body.read_text() == "- [x] ADR files: 2\n"
    bad = subprocess.run(
        [sys.executable, str(SCRIPT), "--fill-count", str(body), "--written", str(tmp_path / "none.json")],
        capture_output=True, text=True,
    )
    assert bad.returncode == 2


def test_default_template_matches_the_repo_template():
    """The built-in fallback is the same text as docs/adr/TEMPLATE.md."""
    import write_adrs
    repo_template = (Path(__file__).resolve().parent.parent / "docs/adr/TEMPLATE.md").read_text()
    assert write_adrs.DEFAULT_TEMPLATE == repo_template


def test_consumer_without_a_template_still_writes(tmp_path, monkeypatch):
    """No docs/adr/TEMPLATE.md anywhere on the lookup path: the built-in default is used."""
    import write_adrs
    monkeypatch.setattr(write_adrs, "__file__", str(tmp_path / "elsewhere" / "write_adrs.py"))
    template = write_adrs.load_template(tmp_path / "adr-dir-without-template")
    assert template == write_adrs.DEFAULT_TEMPLATE


# --- filter, merge and table (#398) ---------------------------------------------------------

def wa():
    sys.path.insert(0, str(SCRIPT.parent))
    import write_adrs
    return write_adrs


def test_needs_adr_filter():
    w = wa()
    assert w.needs_adr(dec(confidence="low", needs_review=False))   # adr alone decides, not confidence
    assert not w.needs_adr(dec(adr=False, needs_review=True))
    assert not w.needs_adr(dec(adr=False, owner_confirmed=True))
    assert "table only (low confidence, check)" in w.decisions_table([dec(confidence="low", adr=False, needs_review=False)])
    # adr wins over owner_confirmed: file, table row and PR section must agree
    assert w.needs_adr(dec(confidence="low", owner_confirmed=True))
    assert "ADR file" in w.decisions_table([dec(owner_confirmed=True)])
    assert not w.needs_adr(dec(options=["a"]))
    assert not w.needs_adr(dec(options=["a", " N/A "]))
    assert not w.needs_adr(dec(title="Boundary: x"))
    assert not w.needs_adr(dec(title="UAT not run for #7"))
    assert not w.needs_adr(dec(boundary=True))


def test_owner_confirmed_validation(tmp_path):
    adr, inp = setup(tmp_path, [dec(owner_confirmed="yes")], existing=())
    r = run(adr, inp)
    assert r.returncode == 2 and "owner_confirmed" in r.stderr
    inp.write_text(json.dumps({"decisions": [dec(owner_confirmed=True)]}))
    assert run(adr, inp, "--dry-run").returncode == 0
    inp.write_text(json.dumps({"decisions": [dec()]}))   # missing means false
    assert len(json.loads(run(adr, inp, "--dry-run").stdout)) == 1


def test_merge_by_title_slug():
    w = wa()
    out = w.dedupe([dec(title="Insert the step!", context="a"), dec(title="insert  the step", context="b")])
    assert len(out) == 1


def test_merge_by_identical_context():
    w = wa()
    out = w.dedupe([dec(title="One", context="Same  context"), dec(title="Two", context="same context")])
    assert len(out) == 1


def test_empty_context_never_matches():
    w = wa()
    assert len(w.dedupe([dec(title="One", context=" "), dec(title="Two", context=" ")])) == 2
    assert len(w.dedupe([dec(title="One", context="n/a"), dec(title="Two", context="n/a")])) == 2


def test_different_ticket_not_merged():
    w = wa()
    assert len(w.dedupe([dec(title="Same", ticket=1), dec(title="Same", ticket=2)])) == 2


def test_merge_keeps_highest_confidence_and_ties_to_first():
    w = wa()
    out = w.dedupe([dec(title="Same", confidence="low", decision="first"),
                    dec(title="Same", confidence="high", decision="second"),
                    dec(title="Same", confidence="high", decision="third")])
    assert len(out) == 1 and out[0]["decision"] == "second" and out[0]["confidence"] == "high"
    tie = w.dedupe([dec(title="Same", decision="first"), dec(title="Same", decision="second")])
    assert tie[0]["decision"] == "first"


def test_merge_carries_needs_review():
    w = wa()
    out = w.dedupe([dec(title="Same", confidence="high", needs_review=False, adr=False),
                    dec(title="Same", confidence="low", needs_review=True)])
    assert out[0]["confidence"] == "high" and out[0]["needs_review"] is True


def test_merge_owner_confirmed_only_when_all_confirmed():
    w = wa()
    mixed = w.dedupe([dec(title="Same", confidence="high", owner_confirmed=True, needs_review=False, adr=False),
                      dec(title="Same", confidence="low", needs_review=False, adr=False)])
    assert mixed[0]["confidence"] == "high" and not mixed[0].get("owner_confirmed")
    assert not w.needs_adr(mixed[0])
    both = w.dedupe([dec(title="Same", owner_confirmed=True), dec(title="Same", owner_confirmed=True)])
    assert both[0]["owner_confirmed"] is True


def test_table_owner_confirmed_row_and_escaping():
    w = wa()
    t = w.decisions_table([dec(title="A|B", owner_confirmed=True, needs_review=False, adr=False, decision="line\nbreak"),
                           dec(title="C", confidence="high", needs_review=False, adr=False), dec(title="D")])
    assert t.splitlines()[0].startswith("| Ticket | Title")
    assert "| #1 | A\\|B | line break | w | owner-confirmed |" in t
    assert "| table only |" in t and "| ADR file |" in t


def test_zero_adr_run_writes_nothing_and_prints_empty_list(tmp_path):
    adr, inp = setup(tmp_path, [dec(confidence="high", needs_review=False, adr=False), dec(title="Two", confidence="low", needs_review=False, adr=False)])
    before = sorted(p.name for p in adr.iterdir())
    table = tmp_path / "t.md"
    r = run(adr, inp, "--table-out", str(table))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == []
    assert sorted(p.name for p in adr.iterdir()) == before
    assert table.read_text().count("\n| #1 |") == 2


def test_six_decisions_give_one_adr_file_and_five_table_rows(tmp_path):
    """2 near-duplicates merge to 1, so 6 decisions are 5 table rows; only the needs_review one gets a
    file, not the low-confidence guess."""
    ds = [
        dec(title="Insert the step", confidence="high", needs_review=False, adr=False, context="c1"),
        dec(title="Insert the step", stage="plan", confidence="high", needs_review=False, adr=False, context="c2"),   # near-duplicate
        dec(title="Owner said so", confidence="low", needs_review=False, adr=False, owner_confirmed=True),
        dec(title="Touches contract", confidence="high", needs_review=True),
        dec(title="Guessed", confidence="low", needs_review=False, adr=False),
        dec(title="Plain", confidence="high", needs_review=False, adr=False),
    ]
    adr, inp = setup(tmp_path, ds)
    table = tmp_path / "t.md"
    r = run(adr, inp, "--table-out", str(table))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert [o["title"] for o in out] == ["Touches contract"]
    assert sorted(p.name for p in adr.iterdir() if p.name[:4].isdigit()) == [
        "0001-workflow-capabilities.md", "0002-touches-contract.md"]
    rows = [l for l in table.read_text().splitlines() if l.startswith("| #")]
    assert len(rows) == 5
    assert sum("owner-confirmed" in l for l in rows) == 1


def test_table_out_not_written_on_dry_run(tmp_path):
    adr, inp = setup(tmp_path, [dec(confidence="low", title="Guessed")])
    table = tmp_path / "t.md"
    r = run(adr, inp, "--dry-run", "--table-out", str(table))
    assert r.returncode == 0, r.stderr
    assert not table.exists()


def test_skill_doc_matches_dedupe_and_owner_confirmed_rules():
    skill = (SCRIPT.parent.parent / "skills/decision-record/SKILL.md").read_text()
    flat = " ".join(skill.split())
    assert "highest `confidence`" in flat
    assert "lowest `confidence`" not in flat
    assert "`adr` wins over `owner_confirmed`" in flat
    assert "at least two viable options" in flat and "Boundary" in flat and "UAT not run" in flat


# --- the adr gate, born accepted, folder dedupe (#565) ----------------------------------------

def md_files(adr):
    return sorted(p.name for p in adr.glob("[0-9][0-9][0-9][0-9]-*.md"))


def test_merge_ors_adr():
    w = wa()
    out = w.dedupe([dec(title="Same", confidence="high", adr=False), dec(title="Same", confidence="low")])
    assert out[0]["confidence"] == "high" and out[0]["adr"] is True


def test_second_run_against_same_folder_writes_one_file(tmp_path):
    adr, inp = setup(tmp_path, [dec()], existing=())
    assert run(adr, inp).returncode == 0
    table = tmp_path / "t.md"
    r = run(adr, inp, "--table-out", str(table))
    assert r.returncode == 0 and json.loads(r.stdout) == []
    assert md_files(adr) == ["0001-use-a-queue.md"]
    assert "already recorded (ADR 0001)" in table.read_text()


def test_folder_dedupe_matches_by_context_and_list_context(tmp_path):
    adr, inp = setup(tmp_path, [dec(title="First", context=["x", "y"])], existing=())
    run(adr, inp)
    inp.write_text(json.dumps({"decisions": [dec(title="Other title", context=["x", "y"])]}))
    assert json.loads(run(adr, inp).stdout) == []
    assert len(md_files(adr)) == 1


def test_same_title_other_ticket_gets_a_file(tmp_path):
    adr, inp = setup(tmp_path, [dec(ticket=1)], existing=())
    run(adr, inp)
    inp.write_text(json.dumps({"decisions": [dec(ticket=2)]}))
    assert len(json.loads(run(adr, inp).stdout)) == 1
    assert len(md_files(adr)) == 2


def test_run_level_tickets_are_not_deduped_against_the_folder(tmp_path):
    adr, inp = setup(tmp_path, [dec(ticket="run")], existing=())
    run(adr, inp)
    assert len(json.loads(run(adr, inp).stdout)) == 1
    assert len(md_files(adr)) == 2


def test_malformed_existing_adr_is_ignored(tmp_path):
    adr, inp = setup(tmp_path, [dec()], existing=("0001-bad.md",))
    (adr / "0001-bad.md").write_bytes(b"\xff\xfe not an adr")
    r = run(adr, inp)
    assert r.returncode == 0, r.stderr
    assert len(json.loads(r.stdout)) == 1


def test_boundary_and_uat_get_no_file_but_a_table_row(tmp_path):
    ds = [dec(title="Boundary: leave X", needs_review=True), dec(title="Scope", boundary=True),
          dec(title="UAT not run for #7"), dec(title="One option", options=["a"]),
          dec(title="No options", options=["n/a"]), dec(title="Real")]
    adr, inp = setup(tmp_path, ds, existing=())
    table = tmp_path / "t.md"
    r = run(adr, inp, "--table-out", str(table))
    assert r.returncode == 0, r.stderr
    assert [o["title"] for o in json.loads(r.stdout)] == ["Real"]
    rows = [l for l in table.read_text().splitlines() if l.startswith("| #")]
    assert len(rows) == 6 and sum("table only" in l for l in rows) == 5


def test_needs_review_never_makes_a_file(tmp_path):
    adr, inp = setup(tmp_path, [dec(adr=False, needs_review=True)], existing=())
    assert json.loads(run(adr, inp).stdout) == []
    assert md_files(adr) == []


def test_status_proposed_when_needs_review(tmp_path):
    adr, inp = setup(tmp_path, [dec(needs_review=True)], existing=())
    run(adr, inp)
    text = (adr / "0001-use-a-queue.md").read_text()
    assert "status: proposed" in text and "needs_review: true" in text
    assert "status: accepted" not in text


def test_no_needs_review_status_in_docs_or_script():
    root = SCRIPT.parent.parent.parent.parent
    for p in (root / "docs/adr/README.md", root / "docs/adr/TEMPLATE.md", SCRIPT):
        assert "needs-review" not in p.read_text(), p
