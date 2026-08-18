"""Tests for the stable prompt-inventory baseline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("audit_skill_prompts.py")


def write_fixture(root: Path) -> None:
    (root / "skills" / "alpha").mkdir(parents=True)
    (root / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: Use when alpha work is requested.\n---\n# Alpha\n"
    )
    (root / "skills" / "alpha" / "worker-prompt.md").write_text("# Worker\n")
    (root / "harness-manifest.json").write_text(json.dumps({"skills": ["alpha"]}))


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
    )


def test_inventory_counts_registered_skill_and_companion_prompt(tmp_path):
    write_fixture(tmp_path)
    result = run(tmp_path, "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["totals"] == {
        "skills": 1,
        "companion_prompts": 1,
        "lines": 6,
        "words": 15,
        "characters": 84,
    }
    assert data["inventory"][0]["description_characters"] == 33


def test_unowned_prompt_fails(tmp_path):
    write_fixture(tmp_path)
    stray = tmp_path / "skills" / "orphan"
    stray.mkdir()
    (stray / "worker-prompt.md").write_text("# orphan\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "unowned companion prompt" in result.stderr


def test_description_and_skill_surface_ceilings_fail_with_named_diagnostics(tmp_path):
    write_fixture(tmp_path)
    skill = tmp_path / "skills/alpha/SKILL.md"
    skill.write_text("---\nname: alpha\ndescription: " + "x" * 1025 + "\n---\n# Alpha\n" + ("word " * 601))
    result = run(tmp_path)
    assert result.returncode == 1
    assert "description exceeds" in result.stderr
    assert "progressive-disclosure ceiling" in result.stderr


def test_check_baseline_ignores_git_sha_but_detects_surface_drift(tmp_path):
    write_fixture(tmp_path)
    first = run(tmp_path, "--json")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(first.stdout)
    assert run(tmp_path, "--check-baseline", str(baseline)).returncode == 0
    (tmp_path / "skills" / "alpha" / "worker-prompt.md").write_text("# changed\nmore\n")
    changed = run(tmp_path, "--check-baseline", str(baseline))
    assert changed.returncode == 1
    assert "differs from baseline" in changed.stderr


def test_writes_json_and_markdown_baselines(tmp_path):
    write_fixture(tmp_path)
    json_path = tmp_path / "results" / "baseline.json"
    markdown_path = tmp_path / "results" / "baseline.md"
    result = run(tmp_path, "--write-json", str(json_path), "--write-markdown", str(markdown_path))
    assert result.returncode == 0, result.stderr
    assert json.loads(json_path.read_text())["totals"]["skills"] == 1
    assert "# Skill prompt inventory baseline" in markdown_path.read_text()


def test_compare_requires_a_real_reduction(tmp_path):
    write_fixture(tmp_path)
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    assert run(tmp_path, "--write-json", str(baseline)).returncode == 0
    (tmp_path / "skills" / "alpha" / "SKILL.md").write_text("# Alpha\n")
    assert run(tmp_path, "--write-json", str(candidate)).returncode == 0
    result = run(tmp_path, "--compare", str(baseline), str(candidate))
    assert result.returncode == 0, result.stderr
    assert "reduction" in result.stdout


def test_validate_inventory_allows_a_pinned_pre_refactor_baseline(tmp_path):
    write_fixture(tmp_path)
    baseline = tmp_path / "baseline.json"
    assert run(tmp_path, "--write-json", str(baseline)).returncode == 0
    (tmp_path / "skills" / "alpha" / "SKILL.md").write_text("# changed\n")
    result = run(tmp_path, "--validate-inventory", str(baseline))
    assert result.returncode == 0, result.stderr


def test_real_repository_matches_expected_surface_shape():
    root = SCRIPT.parent.parent
    result = run(root, "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["totals"]["skills"] == 12
    assert data["totals"]["companion_prompts"] == 11
