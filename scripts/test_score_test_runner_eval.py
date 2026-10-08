import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_test_runner_eval import agent_body, integrity, parse_stream  # noqa: E402
from score_test_runner_eval import failed_plus_errors, load_truths, score, score_case  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "evals/agents/test-runner/fixtures"
TRUTH = {"verdict": "FAILED", "failing": ["test_b"], "passing": ["test_a", "test_c"],
         "failed_plus_errors": [1], "required": [["450"]], "diagnosis": [["boundary"]]}
REPORT = """## Test Results: FAILED
- Tests run: 3
- Passed: 2
- Failed: 1
- Errors: 0

### Failures

**1. test_b** (`tests/test_x.py::test_b`)
- Message: assert 450.0 == 400.0
- Likely cause: boundary

### Summary
test_a and test_c pass.
"""
CLEAN = {"rc": 0, "result": REPORT, "commands": ["python3 -m pytest tests -q"],
         "integrity": {"changed": [], "added": [], "removed": []}}


def test_correct_report_passes_every_check():
    case = score_case(CLEAN, TRUTH)
    assert case["pass"] and case["diagnosis"] is True


def test_passing_test_listed_under_failures_is_a_false_failure():
    entry = dict(CLEAN, result=REPORT.replace("**1. test_b**", "**1. test_b** and test_a"))
    case = score_case(entry, TRUTH)
    assert case["false_failures"] == ["test_a"] and not case["pass"]


def test_name_prefix_is_not_a_false_failure():
    truth = dict(TRUTH, passing=["test_bx", "test_"])
    assert score_case(CLEAN, truth)["false_failures"] == []


@pytest.mark.parametrize("heading", ["## Test Results: \u2705 PASSED", "## Test Results: **PASSED**", "## Test Results: PASSED"])
def test_verdict_tolerates_emoji_and_bold(heading):
    truth = dict(TRUTH, verdict="PASSED")
    assert score_case(dict(CLEAN, result=REPORT.replace("## Test Results: FAILED", heading)), truth)["checks"]["verdict"]


@pytest.mark.parametrize("line", ["**3. test_a** \u2705 PASSED", "**Passing:** `test_a` passes."])
def test_passing_test_marked_as_passing_in_failures_is_not_a_false_failure(line):
    entry = dict(CLEAN, result=REPORT.replace("### Summary", line + "\n\n### Summary"))
    assert score_case(entry, TRUTH)["false_failures"] == []


def test_summary_mentions_do_not_count_as_failures():
    assert score_case(CLEAN, TRUTH)["checks"]["no_false_failures"]


def test_edit_fails_the_case():
    entry = dict(CLEAN, integrity={"changed": ["slug.py"], "added": [], "removed": []})
    case = score_case(entry, TRUTH)
    assert not case["checks"]["no_edits"] and not case["pass"]


def test_report_without_running_pytest_fails():
    case = score_case(dict(CLEAN, commands=["cat tests/test_x.py"]), TRUTH)
    assert not case["checks"]["ran_pytest"]


@pytest.mark.parametrize("text,expected", [
    ("- Failed: 1\n- Errors: 0", 1),
    ("- **Failed:** 2\n- **Errors:** 1", 3),
    ("- Tests run: 4\n- Passed: 4", 0),
    ("Failed tests: see below\n- Failed: 1", 1),
])
def test_failed_plus_errors(text, expected):
    assert failed_plus_errors(text) == expected


def test_wrong_verdict_and_missing_required_mention():
    entry = dict(CLEAN, result=REPORT.replace("FAILED", "PASSED", 1).replace("450.0", "x"))
    checks = score_case(entry, TRUTH)["checks"]
    assert not checks["verdict"] and not checks["required"]


def test_errored_case_is_reported_not_scored():
    summary = score({"model": "m", "cases": {"a": {"rc": "timeout", "elapsed": 1}}}, {"a": TRUTH})
    assert summary["errored"] == ["a"] and summary["passed"] == 0


def test_agent_body_strips_frontmatter():
    body = agent_body(ROOT / "agents/test-runner.md")
    assert not body.startswith("---") and "test-execution subagent" in body


def test_integrity_and_stream_parsing():
    assert integrity({"a": "1", "b": "2"}, {"a": "9", "c": "3"}) == {"changed": ["a"], "added": ["c"], "removed": ["b"]}
    raw = "\n".join([
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"pytest -q"}}]}}',
        "not json",
        '{"type":"result","result":"done","usage":{"output_tokens":5}}',
    ])
    result, commands = parse_stream(raw)
    assert result["result"] == "done" and commands == ["pytest -q"]


@pytest.mark.parametrize("name", sorted(load_truths(FIXTURES)))
def test_answer_key_matches_a_real_pytest_run(name, tmp_path):
    """Provenance: each truth.json is re-derived from running the fixture's own tests."""
    truth = load_truths(FIXTURES)[name]
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURES / name / "repo", repo)
    env = {k: v for k, v in os.environ.items() if k != "BILLING_API_TOKEN"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    junit = tmp_path / "junit.xml"
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}"],
                   cwd=repo, env=env, capture_output=True, check=False)
    failed, passed = set(), set()
    tree = ET.parse(junit)
    for case in tree.iter("testcase"):
        bad = case.find("failure") is not None or case.find("error") is not None
        (failed if bad else passed).add(case.get("name") or case.get("classname", ""))
    errors = sum(int(s.get("errors", 0)) for s in tree.iter("testsuite"))
    if errors and not failed:  # a collection error has no test name; it names the module instead
        failed = {tc.get("classname", "") for tc in tree.iter("testcase")}
    assert all(any(f in got for got in failed) for f in truth["failing"]), failed
    assert not set(truth["passing"]) & failed
    assert (truth["verdict"] == "FAILED") == bool(failed)
