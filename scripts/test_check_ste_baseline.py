"""Tests for scripts/check_ste_baseline.py. Run them with pytest.

Each test builds a fake tree under tmp_path with a fake linter at the real linter path.
The fake linter reads hard counts from `counts.json` next to it. The default run never blocks,
so every default case asserts exit 0. The `--strict` cases assert exit 1 on a WARN line or on a
skipped run. The `--against` cases also make the tree a git repo and commit the baseline file.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_ste_baseline.py"
LINTER = "plugins/harness/skills/asd-ste100/scripts/ste-lint.py"

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
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 5}, {"plugins/harness/rules/a.md": 3})
    result = run(tmp_path)
    assert result.returncode == 0
    assert "WARN plugins/harness/rules/a.md" in result.stdout


def test_below_baseline_notes_and_exits_0(tmp_path):
    make_tree(tmp_path, {"plugins/harness/agents/a.md": 1}, {"plugins/harness/agents/a.md": 3})
    result = run(tmp_path)
    assert result.returncode == 0
    assert "NOTE plugins/harness/agents/a.md" in result.stdout
    assert "WARN" not in result.stdout


def test_equal_baseline_prints_nothing(tmp_path):
    make_tree(tmp_path, {"plugins/harness/skills/x/SKILL.md": 2}, {"plugins/harness/skills/x/SKILL.md": 2})
    result = run(tmp_path, "--strict")
    assert result.returncode == 0
    assert "WARN" not in result.stdout and "NOTE" not in result.stdout


def test_file_missing_from_baseline_uses_0_and_warns(tmp_path):
    make_tree(tmp_path, {"plugins/harness/skills/x/sub/new.md": 2}, {})
    result = run(tmp_path)
    assert result.returncode == 0
    assert "WARN plugins/harness/skills/x/sub/new.md" in result.stdout
    assert "baseline 0" in result.stdout


def test_baseline_entry_for_deleted_file_warns(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 0}, {"plugins/harness/rules/a.md": 0, "plugins/harness/rules/gone.md": 4})
    result = run(tmp_path)
    assert result.returncode == 0
    assert "WARN plugins/harness/rules/gone.md" in result.stdout


def test_linter_crash_skips_exits_0_default_and_1_strict(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 1}, {"plugins/harness/rules/a.md": 0}, mode="crash")
    assert run(tmp_path).returncode == 0
    result = run(tmp_path, "--strict")
    assert result.returncode == 1
    assert "ste-baseline: skipped (" in result.stdout


def test_invalid_json_skips_exits_0_default_and_1_strict(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 1}, {"plugins/harness/rules/a.md": 0}, mode="garbage")
    assert run(tmp_path).returncode == 0
    result = run(tmp_path, "--strict")
    assert result.returncode == 1
    assert "ste-baseline: skipped (" in result.stdout


def test_missing_baseline_file_skips_exits_0_default_and_1_strict(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 1}, None)
    assert run(tmp_path).returncode == 0
    result = run(tmp_path, "--strict")
    assert result.returncode == 1
    assert "ste-baseline: skipped (" in result.stdout


def test_non_int_baseline_value_skips_and_exits_0_by_default(tmp_path):
    for bad in ("3", 2.5, None, True, [1]):
        root = tmp_path / repr(bad)
        make_tree(root, {"plugins/harness/rules/a.md": 1}, {"plugins/harness/rules/a.md": bad})
        result = run(root)
        assert result.returncode == 0, (bad, result.stderr)
        assert "ste-baseline: skipped (" in result.stdout, (bad, result.stdout)


def test_non_int_baseline_value_skips_and_exits_1_strict(tmp_path):
    for bad in ("3", 2.5, None, True, [1]):
        root = tmp_path / repr(bad)
        make_tree(root, {"plugins/harness/rules/a.md": 1}, {"plugins/harness/rules/a.md": bad})
        result = run(root, "--strict")
        assert result.returncode == 1, (bad, result.stderr)
        assert "ste-baseline: skipped (" in result.stdout, (bad, result.stdout)


def test_strict_exits_1_on_warn(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 5}, {"plugins/harness/rules/a.md": 3})
    result = run(tmp_path, "--strict")
    assert result.returncode == 1
    assert "WARN plugins/harness/rules/a.md" in result.stdout


def test_strict_exits_0_on_note_only(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 1}, {"plugins/harness/rules/a.md": 3})
    assert run(tmp_path, "--strict").returncode == 0


def test_update_rewrites_baseline(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 2, "plugins/harness/agents/b.md": 0}, {"plugins/harness/rules/gone.md": 9})
    result = run(tmp_path, "--update")
    assert result.returncode == 0
    data = json.loads((tmp_path / "scripts" / "ste-baseline.json").read_text())
    assert data == {"plugins/harness/agents/b.md": 0, "plugins/harness/rules/a.md": 2}
    assert run(tmp_path, "--strict").returncode == 0


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                             "-c", "commit.gpgsign=false", *args],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def commit_tree(root: Path) -> str:
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    return git(root, "rev-parse", "HEAD")


def test_against_rise_above_ref_warns_and_strict_exits_1(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 5}, {"plugins/harness/rules/a.md": 3})
    ref = commit_tree(tmp_path)
    # The working baseline allows the rise. The baseline at the ref does not.
    (tmp_path / "scripts" / "ste-baseline.json").write_text(json.dumps({"plugins/harness/rules/a.md": 5}))
    assert "WARN" not in run(tmp_path).stdout
    result = run(tmp_path, "--against", ref)
    assert result.returncode == 0
    assert "WARN plugins/harness/rules/a.md: hard 5 > baseline 3" in result.stdout
    result = run(tmp_path, "--strict", "--against", ref)
    assert result.returncode == 1
    assert "WARN plugins/harness/rules/a.md" in result.stdout


def test_against_at_or_below_ref_prints_no_warn(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 3, "plugins/harness/agents/b.md": 1}, {"plugins/harness/rules/a.md": 3, "plugins/harness/agents/b.md": 2})
    ref = commit_tree(tmp_path)
    # The working baseline would warn on both files. The baseline at the ref does not.
    (tmp_path / "scripts" / "ste-baseline.json").write_text(json.dumps({}))
    result = run(tmp_path, "--strict", "--against", ref)
    assert result.returncode == 0
    assert "WARN" not in result.stdout


def test_against_ref_that_does_not_resolve_skips(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 0}, {"plugins/harness/rules/a.md": 0})
    commit_tree(tmp_path)
    result = run(tmp_path, "--against", "no-such-ref")
    assert result.returncode == 0
    assert "ste-baseline: skipped (" in result.stdout
    result = run(tmp_path, "--strict", "--against", "no-such-ref")
    assert result.returncode == 1
    assert "ste-baseline: skipped (" in result.stdout


def test_against_ref_without_baseline_file_skips(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 0}, None)
    ref = commit_tree(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "ste-baseline.json").write_text(json.dumps({"plugins/harness/rules/a.md": 0}))
    result = run(tmp_path, "--against", ref)
    assert result.returncode == 0
    assert "ste-baseline: skipped (" in result.stdout
    result = run(tmp_path, "--strict", "--against", ref)
    assert result.returncode == 1
    assert "ste-baseline: skipped (" in result.stdout


def test_against_with_update_is_refused(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 2}, {"plugins/harness/rules/a.md": 0})
    ref = commit_tree(tmp_path)
    result = run(tmp_path, "--update", "--against", ref)
    assert result.returncode == 2
    data = json.loads((tmp_path / "scripts" / "ste-baseline.json").read_text())
    assert data == {"plugins/harness/rules/a.md": 0}


def test_non_utf8_baseline_file_skips_exits_0_default_and_1_strict(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 1}, {})
    (tmp_path / "scripts" / "ste-baseline.json").write_bytes(b'{"a\xff": 1}')
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "ste-baseline: skipped (" in result.stdout
    result = run(tmp_path, "--strict")
    assert result.returncode == 1, result.stderr
    assert "ste-baseline: skipped (" in result.stdout
    assert "Traceback" not in result.stderr


def test_against_non_utf8_blob_skips_exits_0_default_and_1_strict(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 1}, {})
    (tmp_path / "scripts" / "ste-baseline.json").write_bytes(b'{"a\xff": 1}')
    ref = commit_tree(tmp_path)
    (tmp_path / "scripts" / "ste-baseline.json").write_text(json.dumps({"plugins/harness/rules/a.md": 1}))
    result = run(tmp_path, "--against", ref)
    assert result.returncode == 0, result.stderr
    assert "ste-baseline: skipped (" in result.stdout
    result = run(tmp_path, "--strict", "--against", ref)
    assert result.returncode == 1, result.stderr
    assert "ste-baseline: skipped (" in result.stdout
    assert "Traceback" not in result.stderr


def test_empty_against_is_refused(tmp_path):
    make_tree(tmp_path, {"plugins/harness/rules/a.md": 0}, {"plugins/harness/rules/a.md": 0})
    commit_tree(tmp_path)
    for empty in ("", "   "):
        result = run(tmp_path, "--strict", "--against", empty)
        assert result.returncode == 2, (empty, result.stdout, result.stderr)
        assert "--against" in result.stderr
