import json
import subprocess
import sys
from pathlib import Path

import pytest

from score_review_chain_eval import check_truth, classify, normalise_file, parse_findings, score, score_case

SCRIPTS = Path(__file__).resolve().parent

TRUTH = {
    "schema_version": 1,
    "expected_oracle": "correctness",
    "core": True,
    "correctness_clean": False,
    "planted": {"file": "app/stats.py", "match_any": ["count_active"], "and_any": ["filter", "deleted"]},
    "false_positives": [{"file": "app/cache.py", "match_any": ["ttl"], "and_any": []}],
}


def finding(**kw):
    base = {"oracle": "correctness", "class": "bug", "file": "app/stats.py", "line": 3, "confidence": 80, "summary": ""}
    base.update(kw)
    return base


def block(findings):
    return "Review done.\n```json\n" + json.dumps(findings) + "\n```\n"


def test_planted_match():
    f = finding(summary="count_active does not filter deleted rows")
    assert classify(f, TRUTH) == "planted"


def test_planted_needs_and_any_term():
    f = finding(summary="count_active is slow")
    assert classify(f, TRUTH) == "other"


def test_listed_false_positive_match():
    f = finding(file="app/cache.py", summary="TTL never expires")
    assert classify(f, TRUTH) == "false_positive"


def test_correctness_finding_on_clean_fixture_is_false_positive():
    clean = dict(TRUTH, correctness_clean=True, expected_oracle="intent")
    f = finding(file="app/other.py", summary="possible crash")
    assert classify(f, clean) == "false_positive"
    assert classify(dict(f, oracle="intent"), clean) == "other"


def test_unknown_class_is_always_other():
    f = finding(**{"class": "unknown", "summary": "count_active may not filter deleted rows"})
    assert classify(f, TRUTH) == "other"
    clean = dict(TRUTH, correctness_clean=True)
    assert classify(f, clean) == "other"


def test_other_finding():
    f = finding(file="app/views.py", summary="unrelated naming concern")
    assert classify(f, TRUTH) == "other"


def test_file_normalisation():
    assert normalise_file("a/app/stats.py:12") == "app/stats.py"
    assert normalise_file("./app/stats.py") == "app/stats.py"
    f = finding(file="b/src/app/stats.py:12", summary="Count_Active ignores DELETED flag")
    assert classify(f, TRUTH) == "planted"
    # path-segment boundary: "myapp/stats.py" must not match "app/stats.py"
    assert classify(dict(f, file="myapp/stats.py"), TRUTH) == "other"


def test_oracle_match_true_and_false():
    hit = finding(summary="count_active does not filter deleted rows", confidence=90)
    case = score_case(block([hit]), TRUTH)
    assert case["caught"] and case["oracle_match"] and case["confidence"] == 90
    case = score_case(block([dict(hit, oracle="intent")]), TRUTH)
    assert case["caught"] and not case["oracle_match"]


def test_missing_json_block_counts_zero_findings():
    findings, blocks = parse_findings("I found nothing worth a JSON block.")
    assert findings == [] and blocks == 0
    case = score_case("no block here", TRUTH)
    assert not case["caught"] and case["blocks"] == 0 and case["classes"] == []


def test_last_json_block_is_used():
    text = block([finding(summary="x")]) + block([])
    findings, blocks = parse_findings(text)
    assert findings == [] and blocks == 2


def write_fixture(root: Path, name: str, truth) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "intent.md").write_text("Add a counter.\n")
    (d / "diff.patch").write_text("--- a/app/stats.py\n+++ b/app/stats.py\n")
    (d / "truth.json").write_text(json.dumps(truth) if not isinstance(truth, str) else truth)
    return d


def test_check_truth_accepts_valid(tmp_path):
    write_fixture(tmp_path, "one", TRUTH)
    assert check_truth(tmp_path) == []


@pytest.mark.parametrize("bad", [
    dict(TRUTH, planted={"file": "app/stats.py", "match_any": [], "and_any": []}),
    dict(TRUTH, expected_oracle="style"),
    {k: v for k, v in TRUTH.items() if k != "core"},
    "{not json",
])
def test_check_truth_rejects_invalid(tmp_path, bad):
    write_fixture(tmp_path, "bad", bad)
    errors = check_truth(tmp_path)
    assert errors and "bad/truth.json" in errors[0]
    proc = subprocess.run([sys.executable, str(SCRIPTS / "score_review_chain_eval.py"), "--check-truth", str(tmp_path)], capture_output=True, text=True)
    assert proc.returncode == 1 and "truth.json" in proc.stdout + proc.stderr


def test_summary_totals(tmp_path):
    write_fixture(tmp_path, "core-hit", TRUTH)
    write_fixture(tmp_path, "core-miss", TRUTH)
    write_fixture(tmp_path, "bonus", dict(TRUTH, core=False, correctness_clean=True, expected_oracle="context-propagation-audit"))
    hit = finding(summary="count_active does not filter deleted rows", confidence=90)
    results = {"model": "m", "effort": "low", "client": "x", "cases": {
        "core-hit": {"rc": 0, "elapsed": 1.0, "result": block([hit, finding(file="app/cache.py", summary="ttl", confidence=80)]), "usage": {}},
        "core-miss": {"rc": 0, "elapsed": 1.0, "result": "no json", "usage": {}},
        "bonus": {"rc": 0, "elapsed": 1.0, "result": block([dict(hit, oracle="intent"), finding(file="z.py", summary="crash", confidence=50), finding(file="y.py", oracle="intent", summary="gap")]), "usage": {}},
    }}
    totals, lines = score(results, tmp_path, threshold=75)
    assert totals == {"core": 2, "core_caught": 1, "core_oracle_match": 1, "bonus_caught": 1, "all_caught": 2,
                      "fp": 2, "fp_at_threshold": 1, "other": 1, "errored": 0, "core_errored": 0}
    assert any("core-miss" in line and "blocks=0" in line for line in lines)
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results))
    proc = subprocess.run([sys.executable, str(SCRIPTS / "score_review_chain_eval.py"), "--score", str(path), "--fixtures", str(tmp_path)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "core catches: 1/2" in proc.stdout


STUB = """#!/bin/sh
echo "$PWD" >> "{log}"
if [ "$1" = "--version" ]; then echo "9.9.9 (stub)"; exit 0; fi
printf '%s\\n' "$@" > "{args}"
printf '[{{"type":"system"}},{{"type":"result","result":"```json\\\\n[]\\\\n```","usage":{{"input_tokens":3,"output_tokens":4}}}}]'
"""


def make_stub(tmp_path: Path) -> tuple[Path, Path, Path]:
    log, args = tmp_path / "calls.log", tmp_path / "args.txt"
    stub = tmp_path / "claude-stub"
    stub.write_text(STUB.format(log=log, args=args))
    stub.chmod(0o755)
    return stub, log, args


def test_runner_end_to_end_with_stub(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    write_fixture(fixtures, "two", TRUTH)
    stub, log, args = make_stub(tmp_path)
    out = tmp_path / "out" / "results.json"
    proc = subprocess.run([sys.executable, str(SCRIPTS / "run_review_chain_eval.py"), "--claude", str(stub), "--model", "m1",
                           "--effort", "high", "--output", str(out), "--fixtures", str(fixtures)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text())
    assert data["model"] == "m1" and data["effort"] == "high" and "9.9.9" in data["client"]
    assert sorted(data["cases"]) == ["one", "two"]
    case = data["cases"]["one"]
    assert case["rc"] == 0 and case["usage"] == {"input_tokens": 3, "output_tokens": 4}
    assert "```json" in case["result"] and isinstance(case["elapsed"], float)
    argv = args.read_text()
    assert "--tools\n\n--model\nm1\n--effort\nhigh\n--output-format\njson" in argv
    assert "You are a blind code reviewer running two oracles over one change." in argv
    assert "## User request (intent.md)" in argv and "Add a counter." in argv and "## Diff (diff.patch)" in argv
    cwds = [line for line in log.read_text().splitlines()]
    review_cwds = cwds[1:]
    assert review_cwds and all(c != str(SCRIPTS.parent) and c != str(fixtures) for c in review_cwds)


def test_runner_refuses_existing_output(tmp_path):
    stub, log, _ = make_stub(tmp_path)
    out = tmp_path / "exists.json"
    out.write_text("{}")
    proc = subprocess.run([sys.executable, str(SCRIPTS / "run_review_chain_eval.py"), "--claude", str(stub), "--model", "m",
                           "--effort", "low", "--output", str(out)], capture_output=True, text=True)
    assert proc.returncode == 1
    assert not log.exists()
    assert out.read_text() == "{}"


SCORER = str(SCRIPTS / "score_review_chain_eval.py")
RUNNER = str(SCRIPTS / "run_review_chain_eval.py")


def run_score(results_path: Path, fixtures: Path):
    return subprocess.run([sys.executable, SCORER, "--score", str(results_path), "--fixtures", str(fixtures)],
                          capture_output=True, text=True)


def test_score_counts_fixture_absent_from_results_as_missed(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "ran", TRUTH)
    write_fixture(fixtures, "never-ran", TRUTH)
    hit = finding(summary="count_active does not filter deleted rows", confidence=90)
    results = {"cases": {"ran": {"result": block([hit])}}}
    totals, lines = score(results, fixtures, threshold=75)
    assert totals["core"] == 2 and totals["core_caught"] == 1
    assert any("never-ran" in line and "MISSED" in line and "not run" in line for line in lines)
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results))
    proc = run_score(path, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert "core catches: 1/2" in proc.stdout
    assert "all catches: 1/2" in proc.stdout
    assert "warning" in proc.stderr and "never-ran" in proc.stderr


def test_errored_cases_are_flagged_and_excluded_from_totals(tmp_path):
    fixtures = tmp_path / "fixtures"
    for name in ("ok", "rc-fail", "empty", "absent", "not-dict"):
        write_fixture(fixtures, name, TRUTH)
    hit = finding(summary="count_active does not filter deleted rows", confidence=90)
    results = {"cases": {
        "ok": {"rc": 0, "result": block([hit])},
        "rc-fail": {"rc": 2, "result": block([hit, finding(file="app/cache.py", summary="ttl")])},
        "empty": {"rc": 0, "result": "  "},
        "absent": {"rc": 0},
        "not-dict": None,
    }}
    totals, lines = score(results, fixtures, threshold=75)
    assert totals["core"] == 1 and totals["core_caught"] == 1 and totals["all_caught"] == 1
    assert totals["errored"] == 4 and totals["core_errored"] == 4
    assert totals["fp"] == 0 and totals["other"] == 0
    assert any(line.startswith("rc-fail [core]: ERROR (rc=2)") for line in lines)
    for name in ("empty", "absent", "not-dict"):
        assert any(line.startswith(f"{name} [core]: ERROR (no output)") for line in lines)
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results))
    proc = run_score(path, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert "core catches: 1/1 (4 errored)" in proc.stdout
    assert "all catches: 1/1 (4 errored)" in proc.stdout
    assert "review-chain-eval: warning: fixture rc-fail errored (rc=2); excluded from totals" in proc.stderr
    assert "review-chain-eval: warning: fixture empty errored (no output); excluded from totals" in proc.stderr


def test_totals_without_errors_have_no_errored_suffix(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "ok", TRUTH)
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"cases": {"ok": {"rc": 0, "result": "no json"}}}))
    proc = run_score(path, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert "errored" not in proc.stdout + proc.stderr
    assert "core catches: 0/1" in proc.stdout and "MISSED" in proc.stdout


@pytest.mark.parametrize("bad", [
    {k: v for k, v in TRUTH.items() if k != "planted"},
    dict(TRUTH, planted={"file": "app/stats.py", "match_any": ["x"]}),
    "{not json",
])
def test_score_rejects_invalid_truth_without_traceback(tmp_path, bad):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "bad", bad)
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"cases": {"bad": {"result": ""}}}))
    proc = run_score(path, fixtures)
    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr
    assert proc.stderr.startswith("review-chain-eval: bad/truth.json: ")


@pytest.mark.parametrize("content", [json.dumps({"model": "m"}), json.dumps([1]), "{not json"])
def test_score_rejects_results_without_cases(tmp_path, content):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    path = tmp_path / "results.json"
    path.write_text(content)
    proc = run_score(path, fixtures)
    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr
    assert proc.stderr.startswith("review-chain-eval: ") and len(proc.stderr.strip().splitlines()) == 1


def test_check_truth_missing_path_is_one_line_error(tmp_path):
    proc = subprocess.run([sys.executable, SCORER, "--check-truth", str(tmp_path / "nope")], capture_output=True, text=True)
    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr
    assert proc.stderr.startswith("review-chain-eval: ") and len(proc.stderr.strip().splitlines()) == 1


def test_runner_missing_binary_is_one_line_error(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    out = tmp_path / "results.json"
    proc = subprocess.run([sys.executable, RUNNER, "--claude", str(tmp_path / "no-such-claude"), "--model", "m",
                           "--effort", "low", "--output", str(out), "--fixtures", str(fixtures)], capture_output=True, text=True)
    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr
    assert "review-chain-eval: " in proc.stdout + proc.stderr
    assert not out.exists()


def test_runner_reports_skipped_fixture(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    (write_fixture(fixtures, "no-diff", TRUTH) / "diff.patch").unlink()
    stub, _, _ = make_stub(tmp_path)
    out = tmp_path / "out.json"
    proc = subprocess.run([sys.executable, RUNNER, "--claude", str(stub), "--model", "m", "--effort", "low",
                           "--output", str(out), "--fixtures", str(fixtures)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    notices = [line for line in proc.stdout.splitlines() if "skipping" in line]
    assert len(notices) == 1 and "no-diff" in notices[0] and "diff.patch" in notices[0]
    assert sorted(json.loads(out.read_text())["cases"]) == ["one"]
