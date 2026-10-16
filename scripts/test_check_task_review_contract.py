import shutil
import subprocess
import sys
from pathlib import Path

import check_task_review_contract as contract

ROOT = Path(__file__).resolve().parent.parent
PROMPT = "skills/subagent-driven-development/task-reviewer-prompt.md"
IMPLEMENTER = "skills/subagent-driven-development/implementer-prompt.md"
COPIED = (
    IMPLEMENTER,
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


def _fails_without(phrase, rel, tmp_path, monkeypatch):
    for path in COPIED + (PROMPT,):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / path, tmp_path / path)
    text = (ROOT / rel).read_text()
    assert phrase in text, phrase
    (tmp_path / rel).write_text(text.replace(phrase, ""))
    monkeypatch.setattr(contract, "ROOT", tmp_path)
    return contract.main() == 1


def test_contract_checker_fails_without_implementer_seam_pin(tmp_path, monkeypatch):
    assert _fails_without("from a source that is independent of the code", IMPLEMENTER, tmp_path, monkeypatch)


def test_contract_checker_fails_without_reviewer_seam_pin(tmp_path, monkeypatch):
    assert _fails_without("only synthetic fixtures", PROMPT, tmp_path, monkeypatch)
