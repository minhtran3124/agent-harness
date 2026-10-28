import shutil
import subprocess
import sys
from pathlib import Path

import check_task_review_contract as contract

ROOT = Path(__file__).resolve().parent.parent
COPIED = ("skills/implement/SKILL.md", "skills/implement/implementer-prompt.md")


def _copy(tmp_path):
    for rel in COPIED:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)


def test_contract_checker_passes():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check_task_review_contract.py")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_contract_checker_fails_when_a_reviewer_is_dispatched(tmp_path, monkeypatch):
    _copy(tmp_path)
    skill = tmp_path / "skills/implement/SKILL.md"
    skill.write_text(skill.read_text() + "\nDispatch the task-reviewer.\n")
    monkeypatch.setattr(contract, "ROOT", tmp_path)
    assert contract.main() == 1


def test_contract_checker_fails_without_auto_mode(tmp_path, monkeypatch):
    _copy(tmp_path)
    skill = tmp_path / "skills/implement/SKILL.md"
    skill.write_text(skill.read_text().replace("## Auto mode", "## Other"))
    monkeypatch.setattr(contract, "ROOT", tmp_path)
    assert contract.main() == 1


def test_contract_checker_fails_when_retired_path_returns(tmp_path, monkeypatch):
    _copy(tmp_path)
    (tmp_path / "skills/implement/scripts").mkdir()
    monkeypatch.setattr(contract, "ROOT", tmp_path)
    assert contract.main() == 1
