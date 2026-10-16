from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("build_tour.py")
sys.path.insert(0, str(SCRIPT.parent))

import build_tour  # noqa: E402

PAGE_TEXT = (
    "# Commit Gate\n\nIntro line.\n\n## Exit codes\n\n"
    "Run `bash scripts/run-tests.sh` before pushing.\n"
)


def make_wiki(root: Path) -> None:
    wiki = root / "openwiki"
    (wiki / "enforcement").mkdir(parents=True)
    (wiki / "index.md").write_text(
        "# Files\n\n- [Quickstart](quickstart.md) - Entry.\n\n# Directories\n\n- [enforcement](enforcement/)\n",
        encoding="utf-8",
    )
    (wiki / "enforcement" / "index.md").write_text(
        "# Files\n\n- [Commit Gate](commit-gate.md) - Gate.\n", encoding="utf-8")
    (wiki / "quickstart.md").write_text(
        "# Quickstart\n\n| I want to change… | Read first | Then also |\n|---|---|---|\n"
        "| **a hook** (`hooks/*.sh`) | [Commit Gate](enforcement/commit-gate.md) | |\n",
        encoding="utf-8",
    )
    (wiki / "enforcement" / "commit-gate.md").write_text(PAGE_TEXT, encoding="utf-8")
    claims = {"claims": [{"statement": "gate exists", "evidence": []}]}
    (wiki / ".claims").mkdir()
    (wiki / ".claims" / "quickstart.json").write_text(json.dumps({"claims": []}), encoding="utf-8")
    (wiki / ".claims" / "enforcement").mkdir()
    (wiki / ".claims" / "enforcement" / "commit-gate.json").write_text(json.dumps(claims), encoding="utf-8")
    (wiki / ".last-update.json").write_text(json.dumps({
        "updatedAt": "2026-10-16T05:00:41.893Z", "gitHead": "abc", "status": "complete"}), encoding="utf-8")


def record(page="enforcement/commit-gate.md", **overrides) -> dict:
    rec = {
        "page": page,
        "why": "It guards commits.",
        "breaks": [{"t": "Commits get denied.", "src": "Exit codes"}],
        "tests": [{"cmd": "bash scripts/run-tests.sh", "what": "full suite", "src": "Exit codes"}],
    }
    rec.update(overrides)
    return rec


def write_records(root: Path, *recs: dict, section="enforcement") -> None:
    pages_dir = root / ".harness-state" / "onboarding" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / f"{section}.json").write_text(json.dumps({"section": section, "pages": list(recs)}), encoding="utf-8")


def write_start(root: Path) -> None:
    write_records(root, {
        "page": "quickstart.md", "why": "Entry point.",
        "breaks": [{"t": "Edit root sources only.", "src": "Quickstart"}], "tests": [],
    }, section="start")


def build(root: Path) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(SCRIPT), "build"], cwd=root, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def test_plan_lists_quickstart_first_then_directories(tmp_path, monkeypatch):
    make_wiki(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert [s["id"] for s in build_tour.sections()] == ["start", "enforcement"]
    assert build_tour.sections()[1]["pages"] == ["enforcement/commit-gate.md"]


def test_valid_records_write_tour_with_goals(tmp_path, monkeypatch):
    make_wiki(tmp_path)
    write_start(tmp_path)
    write_records(tmp_path, record())
    code, out = build(tmp_path)
    assert code == 0, out
    html = (tmp_path / ".harness-state/onboarding/tour.html").read_text(encoding="utf-8")
    assert "__TOUR_DATA__" not in html
    assert '"goal": "a hook"' in html
    assert "Commit Gate" in html


def test_source_that_is_not_a_heading_is_rejected(tmp_path):
    make_wiki(tmp_path)
    write_start(tmp_path)
    write_records(tmp_path, record(breaks=[{"t": "Denied.", "src": "Made up heading"}]))
    code, out = build(tmp_path)
    assert code == 1
    assert "src is not a heading" in out
    assert not (tmp_path / ".harness-state/onboarding/tour.html").exists()


def test_test_command_not_in_page_is_rejected(tmp_path):
    make_wiki(tmp_path)
    write_start(tmp_path)
    write_records(tmp_path, record(tests=[{"cmd": "make everything", "what": "x", "src": "Exit codes"}]))
    code, out = build(tmp_path)
    assert code == 1
    assert "command is not in the wiki page" in out


def test_missing_record_is_reported(tmp_path):
    make_wiki(tmp_path)
    write_start(tmp_path)
    code, out = build(tmp_path)
    assert code == 1
    assert "enforcement/commit-gate.md: no record" in out


def test_data_cannot_close_the_script_tag(tmp_path):
    make_wiki(tmp_path)
    write_start(tmp_path)
    write_records(tmp_path, record(why="Ends here </script><img src=x>."))
    code, out = build(tmp_path)
    assert code == 0, out
    html = (tmp_path / ".harness-state/onboarding/tour.html").read_text(encoding="utf-8")
    assert "</script><img" not in html
    assert "<\\/script>" in html


def test_verify_counts_come_from_claims(tmp_path):
    make_wiki(tmp_path)
    write_start(tmp_path)
    write_records(tmp_path, record())
    code, out = build(tmp_path)
    assert code == 0, out
    assert "0 of 1 claims ok" in out
