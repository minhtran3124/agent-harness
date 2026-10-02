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
                      "fp": 2, "fp_at_threshold": 1, "other": 1}
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
