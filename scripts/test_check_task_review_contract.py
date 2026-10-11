import shutil
import subprocess
import sys
from pathlib import Path

import check_task_review_contract as contract

ROOT = Path(__file__).resolve().parent.parent
PROMPT = "skills/subagent-driven-development/task-reviewer-prompt.md"
COPIED = (
    "skills/subagent-driven-development/SKILL.md",
    "skills/subagent-driven-development/references/review-chain.md",
    "harness-manifest.json",
)


def test_contract_checker_passes():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check_task_review_contract.py")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_contract_checker_fails_without_checked_against(tmp_path, monkeypatch):
    for rel in COPIED:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    prompt = (ROOT / PROMPT).read_text()
    stripped = "\n".join(line for line in prompt.splitlines() if "checked_against" not in line)
    (tmp_path / PROMPT).write_text(stripped)
    monkeypatch.setattr(contract, "ROOT", tmp_path)
    assert contract.main() == 1
