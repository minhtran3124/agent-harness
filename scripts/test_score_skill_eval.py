"""Tests for the deterministic skill-eval result scorer."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("score_skill_eval.py")


def result(case_id: str, verdict: str = "pass", *, critical: bool = False) -> dict:
    return {
        "schema_version": 1,
        "commit_sha": "abc123",
        "environment": {"model": "test-model", "client_version": "1", "reasoning": "low"},
        "records": [
            {
                "case_id": case_id,
                "skill": "alpha",
                "suite": "behavior",
                "split": "holdout",
                "first_run": True,
                "observation": "observed pass",
                "verdict": verdict,
                "safety_critical": critical,
            }
        ],
    }


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_compare_accepts_matching_passes(tmp_path):
    baseline, candidate = tmp_path / "baseline.json", tmp_path / "candidate.json"
    baseline.write_text(json.dumps(result("b-1")))
    candidate.write_text(json.dumps(result("b-1")))
    assert run("--compare", str(baseline), str(candidate)).returncode == 0


def test_compare_rejects_quality_regression_and_new_false_positive(tmp_path):
    baseline, candidate = tmp_path / "baseline.json", tmp_path / "candidate.json"
    baseline.write_text(json.dumps(result("b-1")))
    candidate.write_text(json.dumps(result("b-1", "false-positive")))
    result_run = run("--compare", str(baseline), str(candidate))
    assert result_run.returncode == 1
    assert "regression" in result_run.stderr
    assert "new false positive" in result_run.stderr


def test_compare_rejects_environment_mismatch_and_safety_miss(tmp_path):
    baseline, candidate = tmp_path / "baseline.json", tmp_path / "candidate.json"
    baseline.write_text(json.dumps(result("b-1", critical=True)))
    changed = result("b-1", "missed", critical=True)
    changed["environment"]["model"] = "different"
    candidate.write_text(json.dumps(changed))
    result_run = run("--compare", str(baseline), str(candidate))
    assert result_run.returncode == 1
    assert "environment mismatch" in result_run.stderr
    assert "safety-critical" in result_run.stderr


def test_rejects_non_first_run_record(tmp_path):
    path = tmp_path / "candidate.json"
    data = result("b-1")
    data["records"][0]["first_run"] = False
    path.write_text(json.dumps(data))
    result_run = run("--compare", str(path), str(path))
    assert result_run.returncode == 1
    assert "first_run" in result_run.stderr


def test_rejects_missing_result_metadata(tmp_path):
    path = tmp_path / "candidate.json"
    data = result("b-1")
    data.pop("commit_sha")
    path.write_text(json.dumps(data))
    result_run = run("--compare", str(path), str(path))
    assert result_run.returncode == 1
    assert "commit_sha" in result_run.stderr
