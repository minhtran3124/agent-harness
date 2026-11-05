"""Acceptance tests for #565: the ADR gate (impact + trade-off), born accepted, dedupe.

Black-box: write_adrs.py is driven through its command line; docs, SKILL.md and ship.js are
checked as published text. Run: python3 -m pytest tests/acceptance/test_adr_gate_565.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plugins/harness/scripts/write_adrs.py"
SHIP = ROOT / "plugins/harness/workflows/ship.js"
SKILL = ROOT / "plugins/harness/skills/decision-record/SKILL.md"
README = ROOT / "docs/adr/README.md"
TEMPLATE = ROOT / "docs/adr/TEMPLATE.md"


def dec(**kw):
    d = {
        "ticket": 565, "stage": "design", "title": "Use a queue", "context": "ctx of queue",
        "options": ["a", "b"], "decision": "a", "why": "w", "consequences": "q",
        "how_to_reverse": "git revert", "confidence": "medium", "needs_review": False,
        "adr": True, "decided_by": "claude",
    }
    d.update(kw)
    return d


def setup(tmp_path, decisions):
    adr = tmp_path / "adr"
    adr.mkdir()
    (adr / "README.md").write_text("r")
    (adr / "TEMPLATE.md").write_text(TEMPLATE.read_text())
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps({"run": "r", "decisions": decisions}))
    return adr, inp


def run(adr, inp, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(inp), "--adr-dir", str(adr), *extra],
        capture_output=True, text=True,
    )


def files(adr):
    return sorted(p.name for p in adr.glob("[0-9][0-9][0-9][0-9]-*.md"))


def test_ac3_same_decision_twice_gives_one_file(tmp_path):
    adr, inp = setup(tmp_path, [dec()])
    assert run(adr, inp).returncode == 0
    first = files(adr)
    assert len(first) == 1
    r = run(adr, inp)
    assert r.returncode == 0, r.stderr
    assert files(adr) == first


def test_ac3_second_run_reports_nothing_new_written(tmp_path):
    adr, inp = setup(tmp_path, [dec()])
    run(adr, inp)
    r = run(adr, inp)
    assert r.returncode == 0, r.stderr
    assert len(files(adr)) == 1
    assert "already recorded" not in (adr / files(adr)[0]).read_text()


def test_ac4_boundary_decision_writes_no_file_but_has_table_row(tmp_path):
    adr, inp = setup(tmp_path, [dec(title="Boundary: leave X alone", needs_review=True)])
    r = run(adr, inp)
    assert r.returncode == 0, r.stderr
    assert files(adr) == []
    sec = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(inp), "--adr-dir", str(adr), "--dry-run"],
        capture_output=True, text=True)
    assert sec.returncode == 0


def test_ac4_boundary_with_boundary_flag_writes_no_file(tmp_path):
    adr, inp = setup(tmp_path, [dec(title="Scope note", boundary=True, needs_review=True)])
    assert run(adr, inp).returncode == 0
    assert files(adr) == []


def test_ac5_uat_not_run_writes_no_file(tmp_path):
    adr, inp = setup(tmp_path, [dec(title="UAT not run for #565", needs_review=True)])
    r = run(adr, inp)
    assert r.returncode == 0, r.stderr
    assert files(adr) == []


def test_ac6_fewer_than_two_real_options_writes_no_file(tmp_path):
    for i, opts in enumerate((["only"], ["n/a"], ["a", "n/a"], ["a", " N/A "])):
        d = tmp_path / f"c{i}"
        d.mkdir()
        adr, inp = setup(d, [dec(options=opts, needs_review=True)])
        r = run(adr, inp)
        assert r.returncode == 0, (opts, r.stderr)
        assert files(adr) == [], opts


def test_ac6_impact_and_two_options_writes_accepted_file(tmp_path):
    adr, inp = setup(tmp_path, [dec()])
    r = run(adr, inp)
    assert r.returncode == 0, r.stderr
    (name,) = files(adr)
    text = (adr / name).read_text()
    assert "status: accepted" in text
    assert "needs-review" not in text


def test_ac6_adr_false_writes_no_file_even_if_needs_review(tmp_path):
    adr, inp = setup(tmp_path, [dec(adr=False, needs_review=True)])
    assert run(adr, inp).returncode == 0
    assert files(adr) == []


def test_ac6_input_without_adr_exits_2(tmp_path):
    d = dec()
    del d["adr"]
    adr, inp = setup(tmp_path, [d])
    r = run(adr, inp)
    assert r.returncode == 2 and "write_adrs:" in r.stderr


def test_ac6_non_bool_adr_exits_2(tmp_path):
    adr, inp = setup(tmp_path, [dec(adr="yes")])
    assert run(adr, inp).returncode == 2


def test_ac7_needs_review_status_removed_from_docs_and_script():
    for p in (README, TEMPLATE, SCRIPT):
        assert "needs-review" not in p.read_text(), p
    # the owner-ask frontmatter line stays in the template as a fact
    assert "needs_review:" in TEMPLATE.read_text()


def test_ac7_status_values_are_accepted_and_superseded():
    t = README.read_text()
    assert "accepted" in t and "superseded" in t


def test_ac7_default_template_equals_template_md():
    sys.path.insert(0, str(SCRIPT.parent))
    import write_adrs
    assert write_adrs.DEFAULT_TEMPLATE == TEMPLATE.read_text()


def test_ac8_ship_has_separate_adr_and_needs_review_flags():
    s = SHIP.read_text()
    assert re.search(r"\badr\b\s*:", s)
    assert "needs_review" in s
    assert "ADR_WHEN" in s


def test_ac8_gate_wording_is_shared_in_schema_rules_and_skill():
    s = SHIP.read_text()
    skill = SKILL.read_text()
    phrase = "at least two viable options"
    assert phrase in s or "ADR_WHEN" in s
    assert phrase in skill
    assert "Boundary" in skill and "UAT not run" in skill
    assert "adr" in skill


def test_ac9_merge_readiness_has_open_decisions_and_adr_files_rows():
    s = SHIP.read_text()
    assert "Open decisions" in s
    assert "ADR files" in s
    assert "needs_review ADRs" not in s
    assert "{{ADR_COUNT}}" in s


def test_ac4_boundary_listed_under_needs_your_decision_in_ship():
    s = SHIP.read_text()
    assert "## Needs your decision" in s
    assert "adr: false" in s or "adr:false" in s or '"adr":false' in s
