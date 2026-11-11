"""Acceptance tests for #591: three edge cases of plugins/harness/scripts/write_adrs.py.

Black box: the script runs as a subprocess against a temp ADR folder.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "plugins/harness/scripts/write_adrs.py"
TEMPLATE = ROOT / "docs/adr/TEMPLATE.md"


def dec(**kw):
    d = {
        "ticket": 1, "stage": "design", "title": "Use a queue", "context": "ctx one",
        "options": ["a", "b"], "decision": "a", "why": "w", "consequences": "q",
        "how_to_reverse": "git revert", "confidence": "medium", "needs_review": True, "adr": True,
        "decided_by": "claude",
    }
    d.update(kw)
    return d


def setup(tmp_path):
    adr = tmp_path / "adr"
    adr.mkdir()
    (adr / "README.md").write_text("r")
    (adr / "TEMPLATE.md").write_text(TEMPLATE.read_text())
    return adr, tmp_path / "in.json"


def feed(adr, inp, *decisions, extra=()):
    inp.write_text(json.dumps({"run": "r", "decisions": list(decisions)}))
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(inp), "--adr-dir", str(adr), *extra],
        capture_output=True, text=True,
    )


def md_files(adr):
    return sorted(p.name for p in adr.glob("[0-9][0-9][0-9][0-9]-*.md"))


def snapshot(adr):
    return {p.name: p.read_bytes() for p in adr.iterdir()}


def test_ac1_rerun_repairs_a_failed_mark_superseded(tmp_path):
    """AC1: re-run after a failed mark-superseded repairs the old ADR; clean re-run is idempotent."""
    adr, inp = setup(tmp_path)
    assert feed(adr, inp, dec(decision="a")).returncode == 0
    assert feed(adr, inp, dec(decision="b")).returncode == 0
    old = adr / "0001-use-a-queue.md"
    assert "superseded_by: 0002" in old.read_text()
    # Simulate the failed mark: the new ADR is on disk, the old one is live again.
    text = old.read_text()
    text = text.replace("status: superseded", "status: accepted")
    text = re.sub(r"^superseded_by:.*\n", "", text, flags=re.M)
    old.write_text(text)
    assert "status: accepted" in old.read_text() and "superseded_by" not in old.read_text()

    r = feed(adr, inp, dec(decision="b"))
    assert r.returncode == 0, r.stderr
    fixed = old.read_text()
    assert "status: superseded" in fixed and "superseded_by: 0002" in fixed
    assert md_files(adr) == ["0001-use-a-queue.md", "0002-use-a-queue.md"]

    before = snapshot(adr)
    r = feed(adr, inp, dec(decision="b"))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == []
    assert snapshot(adr) == before


def test_ac1_nothing_to_repair_writes_nothing(tmp_path):
    """AC1: a plain re-run of a recorded decision stays idempotent."""
    adr, inp = setup(tmp_path)
    feed(adr, inp, dec())
    before = snapshot(adr)
    r = feed(adr, inp, dec())
    assert r.returncode == 0 and json.loads(r.stdout) == []
    assert snapshot(adr) == before


def test_ac2_same_slug_different_context_is_not_a_changed_decision(tmp_path):
    """AC2: same title slug, different non-empty context and decision gets its own ADR."""
    adr, inp = setup(tmp_path)
    assert feed(adr, inp, dec(context="ctx about queues", decision="a")).returncode == 0
    r = feed(adr, inp, dec(context="a wholly different problem", decision="use something else entirely"))
    assert r.returncode == 0, r.stderr
    assert len(json.loads(r.stdout)) == 1
    assert len(md_files(adr)) == 2
    old = (adr / "0001-use-a-queue.md").read_text()
    new = (adr / "0002-use-a-queue.md").read_text()
    assert "status: accepted" in old and "superseded" not in old
    assert "Supersedes" not in new


@pytest.mark.parametrize("how", ["invalid_utf8", "unknown_placeholder"])
def test_ac3_broken_template_fails_early_even_with_nothing_to_write(tmp_path, how):
    """AC3: broken TEMPLATE.md exits 2 with a message when no decision is eligible."""
    adr, inp = setup(tmp_path)
    tpl = adr / "TEMPLATE.md"
    # Nothing eligible: the only decision is table-only (adr false).
    if how == "invalid_utf8":
        tpl.write_bytes(b"\xff\xfe\x00 not text {title}\n")
    elif how == "unknown_placeholder":
        tpl.write_text(TEMPLATE.read_text() + "\nOwner: {owner}\n")
    r = feed(adr, inp, dec(adr=False))
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "write_adrs" in r.stderr and r.stderr.strip()
    assert md_files(adr) == []


def test_ac3_broken_template_fails_early_when_decision_already_recorded(tmp_path):
    """AC3: also when the only adr decision is already recorded (nothing to write)."""
    adr, inp = setup(tmp_path)
    assert feed(adr, inp, dec()).returncode == 0
    (adr / "TEMPLATE.md").write_text(TEMPLATE.read_text() + "\nOwner: {owner}\n")
    r = feed(adr, inp, dec())
    assert r.returncode == 2 and "{owner}" in r.stderr


def test_ac3_valid_template_and_default_still_work(tmp_path):
    """AC3: a valid template and the built-in default still work with nothing to write."""
    adr, inp = setup(tmp_path)
    r = feed(adr, inp, dec(adr=False))
    assert r.returncode == 0 and json.loads(r.stdout) == []
    (adr / "TEMPLATE.md").unlink()
    r = feed(adr, inp, dec())
    assert r.returncode == 0, r.stderr
    assert md_files(adr) == ["0001-use-a-queue.md"]
