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
        "how_to_reverse": "git revert", "confidence": "medium", "needs_review": False,
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
    assert "status: accepted" in text and "# 0002. One" in text and "- a\n- b" in text


def test_needs_review_first_then_ticket_stage(tmp_path):
    ds = [dec(title="a", ticket=2), dec(title="b", ticket=1, stage="plan"),
          dec(title="c", ticket=9, needs_review=True), dec(title="d", ticket=1, stage="design")]
    adr, inp = setup(tmp_path, ds)
    out = json.loads(run(adr, inp).stdout)
    assert [o["title"] for o in out] == ["c", "d", "b", "a"]
    assert "status: needs-review" in (adr / "0002-c.md").read_text()


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
            "title": "One", "needs_review": False, "_text": "new"}
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
                {"decisions": [dec(needs_review="yes")]},
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
    adr, inp = setup(tmp_path, [dec(title="Plain"), dec(title="Risky", needs_review=True, ticket=5)])
    written = tmp_path / "w.json"
    written.write_text(run(adr, inp, "--dry-run").stdout)
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--render-section", str(written), "--artifact", "https://x/y"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    s = r.stdout
    assert s.startswith("## Decisions") and "Artifact: https://x/y" in s
    assert "- [ADR 0002](docs/adr/0002-risky.md) (#5, design): Risky" in s
    assert "- [ADR 0003](docs/adr/0003-plain.md) (#1, design): Plain" in s
    assert s.index("Risky") < s.index("Plain")


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
    assert not w.needs_adr(dec(confidence="high", needs_review=False))
    assert w.needs_adr(dec(confidence="high", needs_review=True))
    assert w.needs_adr(dec(confidence="medium"))
    assert w.needs_adr(dec(confidence="low"))
    assert not w.needs_adr(dec(confidence="low", needs_review=False, owner_confirmed=True))
    # needs_review wins over owner_confirmed: file, table row and PR section must agree
    assert w.needs_adr(dec(confidence="low", needs_review=True, owner_confirmed=True))
    assert "ADR file" in w.decisions_table([dec(needs_review=True, owner_confirmed=True)])


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


def test_merge_keeps_lowest_confidence_and_ties_to_first():
    w = wa()
    out = w.dedupe([dec(title="Same", confidence="high", decision="first"),
                    dec(title="Same", confidence="low", decision="second"),
                    dec(title="Same", confidence="low", decision="third")])
    assert len(out) == 1 and out[0]["decision"] == "second"
    tie = w.dedupe([dec(title="Same", decision="first"), dec(title="Same", decision="second")])
    assert tie[0]["decision"] == "first"


def test_merge_keeps_detail_of_confident_item_and_lowest_confidence():
    w = wa()
    out = w.dedupe([dec(title="Same", confidence="high", decision="real decision", why="real why"),
                    dec(title="Same", confidence="low", decision="n/a", why="n/a", consequences="n/a")])
    assert len(out) == 1
    assert out[0]["decision"] == "real decision" and out[0]["why"] == "real why"
    assert out[0]["confidence"] == "low"


def test_merge_carries_needs_review():
    w = wa()
    out = w.dedupe([dec(title="Same", confidence="high", needs_review=False),
                    dec(title="Same", confidence="low", needs_review=True)])
    assert out[0]["confidence"] == "low" and out[0]["needs_review"] is True


def test_merge_owner_confirmed_only_when_all_confirmed():
    w = wa()
    mixed = w.dedupe([dec(title="Same", confidence="high", owner_confirmed=True),
                      dec(title="Same", confidence="low")])
    assert mixed[0]["confidence"] == "low" and not mixed[0].get("owner_confirmed")
    assert w.needs_adr(mixed[0])
    both = w.dedupe([dec(title="Same", owner_confirmed=True), dec(title="Same", owner_confirmed=True)])
    assert both[0]["owner_confirmed"] is True


def test_table_owner_confirmed_row_and_escaping():
    w = wa()
    t = w.decisions_table([dec(title="A|B", owner_confirmed=True, decision="line\nbreak"),
                           dec(title="C", confidence="high"), dec(title="D")])
    assert t.splitlines()[0].startswith("| Ticket | Title")
    assert "| #1 | A\\|B | line break | w | owner-confirmed |" in t
    assert "| table only |" in t and "| ADR file |" in t


def test_zero_adr_run_writes_nothing_and_prints_empty_list(tmp_path):
    adr, inp = setup(tmp_path, [dec(confidence="high"), dec(title="Two", confidence="high")])
    before = sorted(p.name for p in adr.iterdir())
    table = tmp_path / "t.md"
    r = run(adr, inp, "--table-out", str(table))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == []
    assert sorted(p.name for p in adr.iterdir()) == before
    assert table.read_text().count("\n| #1 |") == 2


def test_six_decisions_give_two_adr_files_and_five_table_rows(tmp_path):
    """2 near-duplicates merge to 1, so 6 decisions are 5 table rows; only the needs_review one and
    the low-confidence one get a file."""
    ds = [
        dec(title="Insert the step", confidence="high", context="c1"),
        dec(title="Insert the step", stage="plan", confidence="high", context="c2"),   # near-duplicate
        dec(title="Owner said so", confidence="low", needs_review=False, owner_confirmed=True),
        dec(title="Touches contract", confidence="high", needs_review=True),
        dec(title="Guessed", confidence="low"),
        dec(title="Plain", confidence="high"),
    ]
    adr, inp = setup(tmp_path, ds)
    table = tmp_path / "t.md"
    r = run(adr, inp, "--table-out", str(table))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert [o["title"] for o in out] == ["Touches contract", "Guessed"]
    assert sorted(p.name for p in adr.iterdir() if p.name[:4].isdigit()) == [
        "0001-workflow-capabilities.md", "0002-touches-contract.md", "0003-guessed.md"]
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
    assert "Keep the lowest `confidence`" in flat
    assert "highest `confidence`" not in flat
    assert "`needs_review` wins over `owner_confirmed`" in flat
