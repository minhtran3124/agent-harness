from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("record_skill_eval.py")


def corpus(root: Path) -> None:
    base = root / "evals/skills/prompt-refactor"
    (base / "activation").mkdir(parents=True)
    (base / "behavior").mkdir()
    (base / "activation/alpha.json").write_text(json.dumps({"cases": [{"id": "alpha-a", "split": "holdout"}]}))
    (base / "behavior/alpha.json").write_text(json.dumps({"cases": []}))
    (base / "end-to-end.json").write_text(json.dumps({"cases": []}))
    (base / "corpus-manifest.json").write_text(json.dumps({"skills": [{"name": "alpha", "activation": "evals/skills/prompt-refactor/activation/alpha.json", "behavior": "evals/skills/prompt-refactor/behavior/alpha.json"}], "end_to_end": "evals/skills/prompt-refactor/end-to-end.json"}))


def run(root: Path, result: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), "--results", str(result), "--case", "alpha-a", "--verdict", "pass", "--model", "m", "--client-version", "c", "--reasoning", "r", "--observation", "observed pass", *args], capture_output=True, text=True)


def test_appends_first_run_and_rejects_duplicate(tmp_path, monkeypatch):
    corpus(tmp_path)
    monkeypatch.setattr("subprocess.check_output", lambda *a, **k: "sha\n")
    # A lightweight git directory lets the subprocess use the real git command.
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=tmp_path, check=True)
    result = tmp_path / "result.json"
    first = run(tmp_path, result)
    assert first.returncode == 0, first.stderr
    assert json.loads(result.read_text())["records"][0]["first_run"] is True
    assert json.loads(result.read_text())["records"][0]["observation"] == "observed pass"
    duplicate = run(tmp_path, result)
    assert duplicate.returncode == 1
    assert "already exists" in duplicate.stderr
