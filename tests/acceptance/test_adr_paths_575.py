"""Acceptance tests for #575: ADRs keep status accepted, missing paths are marked '(historical)',
and the dangling-path check moves from test_write_adrs.py into a content lint.

Run: python3 -m pytest tests/acceptance/test_adr_paths_575.py
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr"
MIGRATED = sorted(p for p in ADR.glob("*.md") if re.match(r"00(1[3-9]|2\d|30)-", p.name))
PATH_RE = re.compile(r"`([A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-*<>${}]+)+\.[A-Za-z0-9]+)`")


def _exists(path):
    return (ROOT / path).exists() or (ROOT / "plugins/harness" / path).exists()


def _missing_refs():
    for f in sorted(ADR.glob("*.md")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            for m in PATH_RE.finditer(line):
                p = m.group(1)
                if any(c in p for c in "<>*${}"):
                    continue
                if not _exists(p):
                    yield f, n, p, line


def test_ac1_migrated_adrs_keep_status_accepted():
    assert len(MIGRATED) == 18
    for f in sorted(ADR.glob("*.md")):
        if f.name in ("README.md", "TEMPLATE.md"):
            continue
        m = re.search(r"^status:\s*(\S+)", f.read_text(), re.M)
        assert m and m.group(1) == "accepted", f.name


def test_ac1_existing_notes_remain():
    for n in ("0013", "0014"):
        assert "Status note" in next(ADR.glob(f"{n}-*.md")).read_text(), n
    for n in ("0017", "0018", "0019", "0020"):
        assert "Superseded in part" in next(ADR.glob(f"{n}-*.md")).read_text(), n


def test_ac2_every_missing_path_line_is_marked_historical():
    bad = [f"{f.name}:{n} {p}" for f, n, p, line in _missing_refs() if "(historical)" not in line]
    assert not bad, bad


def test_ac2_known_missing_path_is_marked_where_cited():
    cited = [line for f, n, p, line in _missing_refs() if p == "agents/PROJECT.md"]
    assert cited, "expected an ADR to cite agents/PROJECT.md"
    assert all("(historical)" in line for line in cited)


def test_ac2_existing_paths_are_not_marked():
    bad = []
    for f in sorted(ADR.glob("*.md")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            for m in PATH_RE.finditer(line):
                p = m.group(1)
                if _exists(p) and re.search(re.escape(m.group(0)) + r"\s*\(historical\)", line):
                    bad.append(f"{f.name}:{n} {p}")
    assert not bad, bad


def test_ac3_lint_script_passes_on_repo():
    r = subprocess.run(["bash", "scripts/lint-adr-paths.sh"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_ac4_wired_into_run_tests():
    assert 'fail "scripts/lint-adr-paths.sh"' in (ROOT / "scripts/run-tests.sh").read_text()


def test_ac5_old_dangling_path_test_removed_others_untouched():
    text = (ROOT / "scripts/test_write_adrs.py").read_text()
    assert "test_gate_mode_adrs_supersession_note_has_no_dangling_paths" not in text
    assert "def test_date_absent_uses_today" in text
