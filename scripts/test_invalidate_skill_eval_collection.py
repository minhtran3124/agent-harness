from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("invalidate_skill_eval_collection.py")


def run(results: Path, ledger: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--results", str(results), "--case", "case-1", "--reason", "collector parser lost response", "--ledger", str(ledger), *extra],
        capture_output=True,
        text=True,
    )


def test_moves_only_an_explicit_collection_failure_to_ledger(tmp_path):
    results, ledger = tmp_path / "candidate.json", tmp_path / "invalid.json"
    results.write_text(json.dumps({"records": [{
        "case_id": "case-1", "verdict": "blocked", "observation": "runner did not preserve the response"
    }]}))
    moved = run(results, ledger)
    assert moved.returncode == 0, moved.stderr
    assert json.loads(results.read_text())["records"] == []
    assert json.loads(ledger.read_text())[0]["record"]["case_id"] == "case-1"


def test_refuses_a_real_model_miss_or_pass(tmp_path):
    results, ledger = tmp_path / "candidate.json", tmp_path / "invalid.json"
    results.write_text(json.dumps({"records": [{
        "case_id": "case-1", "verdict": "missed", "observation": "model omitted route"
    }]}))
    rejected = run(results, ledger)
    assert rejected.returncode == 1
    assert "only explicitly unobserved" in rejected.stderr
