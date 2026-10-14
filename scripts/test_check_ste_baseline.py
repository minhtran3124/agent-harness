"""Tests for scripts/check_ste_baseline.py. Run them with pytest.

Each test builds a fake tree under tmp_path with a fake linter at the real linter path.
The fake linter reads hard counts from `counts.json` next to it. Every case asserts exit 0,
because the default run never blocks. The `--strict` cases assert exit 1 only on a WARN line.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_ste_baseline.py"
LINTER = "skills/asd-ste100/scripts/ste-lint.py"

FAKE_LINTER = """\
import json, sys
from pathlib import Path
mode = (Path(__file__).parent / "mode.txt").read_text().strip()
if mode == "crash":
    sys.stderr.write("boom")
    sys.exit(2)
if mode == "garbage":
    print("not json")
    sys.exit(0)
counts = json.loads((Path(__file__).parent / "counts.json").read_text())
path = [a for a in sys.argv[1:] if not a.startswith("--") and "," not in a][-1]
hard = counts.get(path, 0)
print(json.dumps({"violations": [], "count": hard, "hard_count": hard}))
sys.exit(1 if hard else 0)
"""


def make_tree(root: Path, counts: dict[str, int], baseline: dict[str, int] | None,
              mode: str = "ok") -> None:
    linter = root / LINTER
    linter.parent.mkdir(parents=True)
    linter.write_text(FAKE_LINTER)
    (linter.parent / "mode.txt").write_text(mode)
    (linter.parent / "counts.json").write_text(json.dumps(counts))
    for rel in counts:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("text\n")
    if baseline is not None:
        (root / "scripts").mkdir(exist_ok=True)
        (root / "scripts" / "ste-baseline.json").write_text(json.dumps(baseline))


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CHECKER), "--root", str(root), *args],
                          capture_output=True, text=True)


def test_above_baseline_warns_and_exits_0(tmp_path):
    make_tree(tmp_path, {"rules/a.md": 5}, {"rules/a.md": 3})
    result = run(tmp_path)
    assert result.returncode == 0
    assert "WARN rules/a.md" in result.stdout


def test_below_baseline_notes_and_exits_0(tmp_path):
    make_tree(tmp_path, {"agents/a.md": 1}, {"agents/a.md": 3})
    result = run(tmp_path)
    assert result.returncode == 0
    assert "NOTE agents/a.md" in result.stdout
    assert "WARN" not in result.stdout


def test_equal_baseline_prints_nothing(tmp_path):
    make_tree(tmp_path, {"skills/x/SKILL.md": 2}, {"skills/x/SKILL.md": 2})
    result = run(tmp_path, "--strict")
    assert result.returncode == 0
    assert "WARN" not in result.stdout and "NOTE" not in result.stdout


def test_file_missing_from_baseline_uses_0_and_warns(tmp_path):
    make_tree(tmp_path, {"skills/x/sub/new.md": 2}, {})
    result = run(tmp_path)
    assert result.returncode == 0
    assert "WARN skills/x/sub/new.md" in result.stdout
    assert "baseline 0" in result.stdout


def test_baseline_entry_for_deleted_file_warns(tmp_path):
    make_tree(tmp_path, {"rules/a.md": 0}, {"rules/a.md": 0, "rules/gone.md": 4})
    result = run(tmp_path)
    assert result.returncode == 0
    assert "WARN rules/gone.md" in result.stdout


def test_linter_crash_skips_and_exits_0(tmp_path):
    make_tree(tmp_path, {"rules/a.md": 1}, {"rules/a.md": 0}, mode="crash")
    result = run(tmp_path, "--strict")
    assert result.returncode == 0
    assert "ste-baseline: skipped (" in result.stdout


def test_invalid_json_skips_and_exits_0(tmp_path):
    make_tree(tmp_path, {"rules/a.md": 1}, {"rules/a.md": 0}, mode="garbage")
    result = run(tmp_path, "--strict")
    assert result.returncode == 0
    assert "ste-baseline: skipped (" in result.stdout


def test_missing_baseline_file_skips_and_exits_0(tmp_path):
    make_tree(tmp_path, {"rules/a.md": 1}, None)
    result = run(tmp_path, "--strict")
    assert result.returncode == 0
    assert "ste-baseline: skipped (" in result.stdout


def test_strict_exits_1_on_warn(tmp_path):
    make_tree(tmp_path, {"rules/a.md": 5}, {"rules/a.md": 3})
    result = run(tmp_path, "--strict")
    assert result.returncode == 1
    assert "WARN rules/a.md" in result.stdout


def test_strict_exits_0_on_note_only(tmp_path):
    make_tree(tmp_path, {"rules/a.md": 1}, {"rules/a.md": 3})
    assert run(tmp_path, "--strict").returncode == 0


def test_update_rewrites_baseline(tmp_path):
    make_tree(tmp_path, {"rules/a.md": 2, "agents/b.md": 0}, {"rules/gone.md": 9})
    result = run(tmp_path, "--update")
    assert result.returncode == 0
    data = json.loads((tmp_path / "scripts" / "ste-baseline.json").read_text())
    assert data == {"agents/b.md": 0, "rules/a.md": 2}
    assert run(tmp_path, "--strict").returncode == 0
