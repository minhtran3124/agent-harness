"""Acceptance tests for #653: write_adrs.py writes a file only for a decision from a stage before implement.

Black box: the script runs as a subprocess against a temp ADR folder.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "plugins/harness/scripts/write_adrs.py"
TEMPLATE = ROOT / "docs/adr/TEMPLATE.md"


def dec(**kw):
    d = {
        "ticket": 1, "stage": "design", "title": "Use a queue", "context": "ctx one",
        "options": ["a", "b"], "decision": "pick-a", "why": "w", "consequences": "q",
        "how_to_reverse": "git revert", "confidence": "medium", "needs_review": False, "adr": True,
        "decided_by": "claude",
    }
    d.update(kw)
    return d


def go(tmp_path, decision, drop=(), needs_out=False):
    adr = tmp_path / "adr"
    adr.mkdir()
    (adr / "README.md").write_text("r")
    (adr / "TEMPLATE.md").write_text(TEMPLATE.read_text())
    for k in drop:
        decision.pop(k, None)
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps({"run": "r", "decisions": [decision]}))
    table, needs = tmp_path / "table.md", tmp_path / "needs.md"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(inp), "--adr-dir", str(adr),
         "--table-out", str(table), *(["--needs-out", str(needs)] if needs_out else [])],
        capture_output=True, text=True,
    )
    files = sorted(p.name for p in adr.glob("[0-9][0-9][0-9][0-9]-*.md"))
    return r, files, table, needs


def test_late_implement_decision_writes_no_file(tmp_path):
    """AC1: a stage-implement adr decision prints [], writes no file, table says late decision, no file."""
    r, files, table, _ = go(tmp_path, dec(stage="implement"))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == []
    assert files == []
    rows = [l for l in table.read_text().splitlines() if l.startswith("| #")]
    assert len(rows) == 1 and "late decision, no file" in rows[0], rows


def test_late_decision_forces_needs_review(tmp_path):
    """AC2: the late decision is listed under ## Needs your decision."""
    r, _, _, needs = go(tmp_path, dec(stage="implement", needs_review=False), needs_out=True)
    assert r.returncode == 0, r.stderr
    text = needs.read_text()
    assert "## Needs your decision" in text
    assert "Use a queue" in text.split("## Needs your decision", 1)[1]


def test_early_design_decision_writes_file(tmp_path):
    """AC3: the same decision with stage design writes one file."""
    r, files, _, _ = go(tmp_path, dec(stage="design"))
    assert r.returncode == 0, r.stderr
    assert len(json.loads(r.stdout)) == 1
    assert len(files) == 1


def test_late_missing_stage_is_late(tmp_path):
    """AC4: adr true and no stage key writes no file."""
    r, files, _, _ = go(tmp_path, dec(), drop=("stage",))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == []
    assert files == []
