"""Tests for the deterministic skill-eval result scorer."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("score_skill_eval.py")
SPEC = importlib.util.spec_from_file_location("score_skill_eval", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


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


def test_compare_repo_artifacts_require_canonical_corpus(tmp_path):
    baseline, candidate = tmp_path / "baseline.json", tmp_path / "candidate.json"
    baseline.write_text(json.dumps(result("b-1")))
    candidate.write_text(json.dumps(result("b-1")))
    assert MODULE.compare(json.loads(baseline.read_text()), json.loads(candidate.read_text())) == []


def test_compare_strict_mode_rejects_partial_corpus(tmp_path):
    eval_root = tmp_path / "evals/skills/prompt-refactor"
    (eval_root / "activation").mkdir(parents=True)
    (eval_root / "behavior").mkdir()
    (eval_root / "activation/alpha.json").write_text(json.dumps({"cases": [{"id": "a-1"}]}))
    (eval_root / "behavior/alpha.json").write_text(json.dumps({"cases": [{"id": "b-1"}]}))
    (eval_root / "end-to-end.json").write_text(json.dumps({"cases": [{"id": "e-1"}]}))
    (eval_root / "corpus-manifest.json").write_text(json.dumps({
        "skills": [{
            "name": "alpha",
            "activation": "evals/skills/prompt-refactor/activation/alpha.json",
            "behavior": "evals/skills/prompt-refactor/behavior/alpha.json",
        }],
        "end_to_end": "evals/skills/prompt-refactor/end-to-end.json",
    }))
    data = result("b-1")
    errors = MODULE.compare(data, data, require_corpus=True, root=tmp_path)
    assert any("baseline is missing 2 canonical corpus cases" in error for error in errors)


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


def test_candidate_coverage_rejects_missing_and_blocked_cases(tmp_path):
    base = tmp_path / "evals/skills/prompt-refactor"
    (base / "behavior").mkdir(parents=True)
    (base / "activation").mkdir()
    (base / "behavior/alpha.json").write_text(json.dumps({"cases": [{"id": "behavior-1"}, {"id": "behavior-2"}]}))
    (base / "activation/alpha.json").write_text(json.dumps({"cases": []}))
    (base / "end-to-end.json").write_text(json.dumps({"cases": []}))
    (base / "corpus-manifest.json").write_text(json.dumps({
        "skills": [{
            "name": "alpha",
            "activation": "evals/skills/prompt-refactor/activation/alpha.json",
            "behavior": "evals/skills/prompt-refactor/behavior/alpha.json",
        }],
        "end_to_end": "evals/skills/prompt-refactor/end-to-end.json",
    }))
    data = result("behavior-1", "blocked")
    errors = MODULE.candidate_errors(tmp_path, data, "behavior")
    assert "candidate: missing behavior cases: behavior-2" in errors
    assert "candidate: behavior case behavior-1 has non-passing first-run verdict: blocked" in errors


def test_blocked_candidate_is_unmeasured_coverage_not_a_regression():
    """A candidate that returned no observation is unknown, not proven worse."""
    baseline = result("b-1", "pass")
    candidate = result("b-1", "blocked")
    unmeasured: list[str] = []
    errors = MODULE.compare(baseline, candidate, unmeasured=unmeasured)
    assert errors == []
    assert unmeasured == ["b-1"]


def test_missed_candidate_is_still_a_regression():
    """Only `blocked` is exempt — an observed wrong answer still fails the comparison."""
    unmeasured: list[str] = []
    errors = MODULE.compare(result("b-1", "pass"), result("b-1", "missed"), unmeasured=unmeasured)
    assert any("regression for b-1" in error for error in errors)
    assert unmeasured == []


def test_suite_scoped_compare_rejects_a_pass_count_drop():
    def collection(verdicts: dict[str, str]) -> dict:
        data = result("seed")
        data["records"] = [
            {"case_id": case_id, "skill": "alpha", "suite": "activation", "split": "train",
             "first_run": True, "observation": "observed", "verdict": verdict,
             "safety_critical": False}
            for case_id, verdict in verdicts.items()
        ]
        return data

    baseline = collection({"a-1": "pass", "a-2": "pass"})
    # One case improves and two regress, so no single case blocks on the improvement alone.
    candidate = collection({"a-1": "missed", "a-2": "missed"})
    errors = MODULE.compare(baseline, candidate, suite="activation")
    assert any("activation pass count regressed: 2 -> 0" in error for error in errors)

    held = MODULE.compare(baseline, collection({"a-1": "pass", "a-2": "pass"}), suite="activation")
    assert held == []


def test_suite_scoped_compare_ignores_other_suites():
    baseline = result("b-1", "pass")          # suite: behavior
    candidate = result("b-1", "missed")       # would regress if not filtered out
    assert MODULE.compare(baseline, candidate, suite="activation") == []
