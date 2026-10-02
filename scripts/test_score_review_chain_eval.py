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
                      "fp": 2, "fp_at_threshold": 1, "other": 1, "unknown_planted": 0, "unknown_clean_correctness": 0,
                      "errored": 0, "core_errored": 0, "unparseable": 0, "core_unparseable": 0, "tokens": 0}
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
    cases = json.loads(out.read_text())["cases"]
    assert sorted(cases) == ["no-diff", "one"]
    assert cases["no-diff"]["rc"] == "skipped" and cases["no-diff"]["result"] == ""
    assert "diff.patch" in cases["no-diff"]["reason"]


# --- follow-ups: unknown buckets, confidence coercion, fences, warnings, truth checks, tokens ---

CLEAN = dict(TRUTH, correctness_clean=True, expected_oracle="intent")


def test_unknown_buckets_keep_classification_other():
    from score_review_chain_eval import unknown_bucket
    hit = finding(**{"class": "unknown", "summary": "count_active may not filter deleted rows"})
    assert classify(hit, TRUTH) == "other" and unknown_bucket(hit, TRUTH) == "unknown_planted"
    crash = finding(**{"class": "UNKNOWN", "file": "z.py", "summary": "may crash"})
    assert classify(crash, CLEAN) == "other" and unknown_bucket(crash, CLEAN) == "unknown_clean_correctness"
    assert unknown_bucket(dict(crash, oracle="intent"), CLEAN) is None
    assert unknown_bucket(crash, TRUTH) is None
    assert unknown_bucket(finding(summary="count_active does not filter deleted rows"), TRUTH) is None


def test_unknown_buckets_in_totals_and_labels(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "core", TRUTH)
    write_fixture(fixtures, "clean", CLEAN)
    unk_hit = finding(**{"class": "unknown", "summary": "count_active may not filter deleted rows"})
    unk_crash = finding(**{"class": "unknown", "file": "z.py", "summary": "may crash"})
    results = {"cases": {"core": {"rc": 0, "result": block([unk_hit])},
                         "clean": {"rc": 0, "result": block([unk_crash])}}}
    totals, lines = score(results, fixtures, threshold=75)
    assert totals["core_caught"] == 0 and totals["fp"] == 0 and totals["other"] == 2
    assert totals["unknown_planted"] == 1 and totals["unknown_clean_correctness"] == 1
    assert any(line.startswith("core [core]") and "=other(unknown_planted)" in line for line in lines)
    assert any(line.startswith("clean [core]") and "=other(unknown_clean_correctness)" in line for line in lines)
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results))
    proc = run_score(path, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert "unknown findings (counted in other): unknown_planted=1, unknown_clean_correctness=1" in proc.stdout


@pytest.mark.parametrize("value, expected, ok", [
    (80, 80, True), (80.5, 80.5, True), ("90", 90, True), (" 70 ", 70, True), ("62.5", 62.5, True),
    (150, 100, True), (-5, 0, True), (True, 0, False), (False, 0, False), ("high", 0, False),
    (None, 0, False), ([90], 0, False), (float("nan"), 0, False),
    (float("inf"), 0, False), (float("-inf"), 0, False), ("inf", 0, False), ("Infinity", 0, False),
    ("1_0", 0, False), ("1e2", 0, False), ("+80", 80, True), ("nan", 0, False),
])
def test_confidence_coercion(value, expected, ok):
    from score_review_chain_eval import coerce_confidence
    assert coerce_confidence(value) == (expected, ok)


def test_string_confidence_counts_at_threshold_and_bad_value_warns(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    fps = [finding(file="app/cache.py", summary="ttl", confidence="90"),
           finding(file="app/cache.py", summary="ttl again", confidence="high")]
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"cases": {"one": {"rc": 0, "result": block(fps)}}}))
    proc = run_score(path, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert "false positives: 2 (at or above 75: 1)" in proc.stdout
    assert "review-chain-eval: warning: fixture one: confidence 'high' is not a number; treated as 0" in proc.stderr


@pytest.mark.parametrize("fence", ["```JSON", "```json5", "```Json  ", "```json title=findings"])
def test_fence_is_case_insensitive_and_tolerates_tag_suffix(fence):
    text = f"{fence}\n" + json.dumps([finding(summary="x")]) + "\n```\n"
    findings, blocks = parse_findings(text)
    assert blocks == 1 and len(findings) == 1


def test_last_block_that_parses_as_a_list_is_used():
    good = block([finding(summary="kept")])
    text = good + "```json\n{not json\n```\n" + "```json\n{\"a\": 1}\n```\n"
    findings, blocks = parse_findings(text)
    assert blocks == 3 and [f["summary"] for f in findings] == ["kept"]


def test_unparseable_blocks_mark_fixture_excluded(tmp_path):
    findings, blocks = parse_findings("```json\n{broken\n```\n")
    assert findings is None and blocks == 1
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "ok", TRUTH)
    write_fixture(fixtures, "garbled", TRUTH)
    hit = finding(summary="count_active does not filter deleted rows", confidence=90)
    results = {"cases": {"ok": {"rc": 0, "result": block([hit])},
                         "garbled": {"rc": 0, "result": "```json\n[{\"oracle\": \n```\n"}}}
    totals, lines = score(results, fixtures, threshold=75)
    assert totals["unparseable"] == 1 and totals["core_unparseable"] == 1
    assert totals["core"] == 1 and totals["core_caught"] == 1 and totals["errored"] == 0
    assert any(line.startswith("garbled [core]: UNPARSEABLE") for line in lines)
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results))
    proc = run_score(path, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert "core catches: 1/1 (1 unparseable)" in proc.stdout
    assert "all catches: 1/1 (1 unparseable)" in proc.stdout
    assert "warning: fixture garbled" in proc.stderr and "unparseable" in proc.stderr


def test_warns_on_fixture_without_truth_and_case_without_fixture(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    (write_fixture(fixtures, "untruthed", TRUTH) / "truth.json").unlink()
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"cases": {"one": {"rc": 0, "result": "no json"}, "stray": {"rc": 0, "result": "x"}}}))
    proc = run_score(path, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert "warning: fixture untruthed has intent.md/diff.patch but no truth.json; not scored" in proc.stderr
    assert "warning: result case stray has no matching fixture; ignored" in proc.stderr


@pytest.mark.parametrize("bad, needle", [
    (dict(TRUTH, planted={"file": "", "match_any": ["count_active"], "and_any": []}), "planted.file"),
    (dict(TRUTH, false_positives=[{"file": "app/cache.py", "match_any": [], "and_any": []}]), "false_positives[0].match_any"),
    (dict(TRUTH, schema_version=True), "schema_version"),
    (dict(TRUTH, schema_version=1.0), "schema_version"),
    (dict(TRUTH, schema_version="1"), "schema_version"),
    (dict(TRUTH, planted={"file": "app/other.py", "match_any": ["count_active"], "and_any": ["filter"]}), "diff.patch"),
    (dict(TRUTH, planted={"file": "app/stats.py", "match_any": ["count_active"], "and_any": []}), "planted.and_any"),
])
def test_check_truth_stricter_rules(tmp_path, bad, needle):
    write_fixture(tmp_path, "bad", bad)
    errors = check_truth(tmp_path)
    assert errors and any(needle in e for e in errors), errors


def test_check_truth_accepts_planted_file_as_path_suffix(tmp_path):
    d = write_fixture(tmp_path, "one", TRUTH)
    (d / "diff.patch").write_text("diff --git a/src/app/stats.py b/src/app/stats.py\n--- a/src/app/stats.py\n+++ b/src/app/stats.py\n")
    assert check_truth(tmp_path) == []


def test_token_totals_per_arm(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "a", TRUTH)
    write_fixture(fixtures, "b", TRUTH)
    usage_a = {"input_tokens": 1, "output_tokens": 2, "cache_creation_input_tokens": 3, "cache_read_input_tokens": 4,
               "output_tokens_details": {"thinking_tokens": 99}}
    usage_b = {"input_tokens": 10, "output_tokens": 20, "cache_read_input_tokens": True}
    results = {"cases": {"a": {"rc": 0, "result": "x", "usage": usage_a}, "b": {"rc": 2, "result": "", "usage": usage_b}}}
    totals, _ = score(results, fixtures, threshold=75)
    assert totals["tokens"] == 40
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results))
    proc = run_score(path, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert "tokens: 40 (input 11, output 22, cache creation 3, cache read 4) over 2 cases" in proc.stdout


def test_timeout_rc_is_errored():
    from score_review_chain_eval import case_error
    assert case_error({"rc": "timeout", "result": block([])}) == "rc=timeout"


# --- runner robustness ---

def custom_stub(tmp_path: Path, body: str, name: str = "claude-custom") -> Path:
    stub = tmp_path / name
    stub.write_text("#!/bin/sh\n" + body)
    stub.chmod(0o755)
    return stub


def run_runner(stub, out, fixtures, *extra):
    return subprocess.run([sys.executable, RUNNER, "--claude", str(stub), "--model", "m", "--effort", "low",
                           "--output", str(out), "--fixtures", str(fixtures), *extra], capture_output=True, text=True)


OK_BODY = ("if [ \"$1\" = \"--version\" ]; then echo \"1.0 (stub)\"; exit 0; fi\n"
           "printf '[{\"type\":\"result\",\"result\":\"```json\\\\n[]\\\\n```\",\"usage\":{\"input_tokens\":1}}]'\n")


def test_runner_missing_fixtures_dir_fails_before_version(tmp_path):
    stub, log, _ = make_stub(tmp_path)
    out = tmp_path / "out.json"
    proc = run_runner(stub, out, tmp_path / "nope")
    assert proc.returncode == 1
    assert proc.stderr.strip() == f"review-chain-eval: fixtures directory not found: {tmp_path / 'nope'}"
    assert not log.exists() and not out.exists()


@pytest.mark.parametrize("version_body", ["echo '1.0'; exit 3", "exit 0"])
def test_runner_unknown_client_on_bad_version(tmp_path, version_body):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    stub = custom_stub(tmp_path, f"if [ \"$1\" = \"--version\" ]; then {version_body}; fi\n" + OK_BODY)
    out = tmp_path / "out.json"
    proc = run_runner(stub, out, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(out.read_text())["client"] == "unknown"
    assert "review-chain-eval: warning:" in proc.stderr and "--version" in proc.stderr


def test_runner_skips_unreadable_fixture(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    (write_fixture(fixtures, "binary", TRUTH) / "intent.md").write_bytes(b"\xff\xfe\x00bad")
    stub = custom_stub(tmp_path, OK_BODY)
    out = tmp_path / "out.json"
    proc = run_runner(stub, out, fixtures)
    assert proc.returncode == 0, proc.stderr
    notices = [line for line in proc.stdout.splitlines() if "skipping" in line]
    assert len(notices) == 1 and "binary" in notices[0] and "cannot read" in notices[0]
    cases = json.loads(out.read_text())["cases"]
    assert sorted(cases) == ["binary", "one"]
    assert cases["binary"]["rc"] == "skipped" and cases["binary"]["result"] == "" and "cannot read" in cases["binary"]["reason"]
    scored = run_score(out, fixtures)
    assert scored.returncode == 0, scored.stderr
    assert "binary [core]: ERROR (skipped: cannot read" in scored.stdout and "binary [core]: MISSED" not in scored.stdout
    assert "core catches: 0/1 (1 errored)" in scored.stdout


def test_runner_timeout_is_recorded_and_scored_as_errored(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "slow", TRUTH)
    stub = custom_stub(tmp_path, "if [ \"$1\" = \"--version\" ]; then echo 1.0; exit 0; fi\nexec sleep 30\n")
    out = tmp_path / "out.json"
    proc = run_runner(stub, out, fixtures, "--timeout", "0.5")
    assert proc.returncode == 0, proc.stderr
    case = json.loads(out.read_text())["cases"]["slow"]
    assert case["rc"] == "timeout" and case["result"] == ""
    scored = run_score(out, fixtures)
    assert scored.returncode == 1 and "slow [core]: ERROR (rc=timeout)" in scored.stdout  # nothing scorable


def test_runner_interrupted_keeps_completed_cases_in_partial(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "a-first", TRUTH)
    (write_fixture(fixtures, "b-second", TRUTH) / "intent.md").write_text("STOP-HERE\n")
    stub = custom_stub(tmp_path, "case \"$*\" in *STOP-HERE*) kill -9 $PPID; exit 1;; esac\n" + OK_BODY)
    out = tmp_path / "out.json"
    proc = run_runner(stub, out, fixtures)
    assert proc.returncode != 0
    assert not out.exists()
    partials = list(tmp_path.glob("out.json.*.partial"))
    assert len(partials) == 1
    assert sorted(json.loads(partials[0].read_text())["cases"]) == ["a-first"]


def test_runner_success_removes_partial(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    out = tmp_path / "out.json"
    proc = run_runner(custom_stub(tmp_path, OK_BODY), out, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert out.is_file() and not list(tmp_path.glob("*.partial"))


def test_runner_leaves_partials_it_did_not_create(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    out = tmp_path / "out.json"
    foreign = [tmp_path / "out.json.partial", tmp_path / "out.json.12345.partial"]
    for path in foreign:
        path.write_text("{}")
    proc = run_runner(custom_stub(tmp_path, OK_BODY), out, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert out.is_file() and all(path.read_text() == "{}" for path in foreign)
    assert sorted(tmp_path.glob("*.partial")) == sorted(foreign)


def test_runner_refuses_when_its_own_partial_name_exists(tmp_path, monkeypatch, capsys):
    import run_review_chain_eval as runner
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    out = tmp_path / "out.json"
    taken = tmp_path / "out.json.4242.partial"
    taken.write_text("{}")
    stub = custom_stub(tmp_path, OK_BODY)
    monkeypatch.setattr(runner.os, "getpid", lambda: 4242)
    monkeypatch.setattr(sys, "argv", ["run", "--claude", str(stub), "--model", "m", "--effort", "low",
                                      "--output", str(out), "--fixtures", str(fixtures)])
    assert runner.main() == 1
    assert taken.read_text() == "{}" and not out.exists()
    assert "out.json.4242.partial" in capsys.readouterr().err


def test_runner_does_not_overwrite_output_that_appeared_during_run(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    out = tmp_path / "out.json"
    stub = custom_stub(tmp_path, f"[ \"$1\" = \"--version\" ] || echo intruder > \"{out}\"\n" + OK_BODY)
    proc = run_runner(stub, out, fixtures)
    assert proc.returncode == 1
    assert out.read_text() == "intruder\n"
    partials = list(tmp_path.glob("out.json.*.partial"))
    assert len(partials) == 1 and sorted(json.loads(partials[0].read_text())["cases"]) == ["one"]
    assert "review-chain-eval:" in proc.stderr and partials[0].name in proc.stderr


def test_runner_fatal_errors_go_to_stderr(tmp_path):
    stub, _, _ = make_stub(tmp_path)
    out = tmp_path / "exists.json"
    out.write_text("{}")
    proc = run_runner(stub, out, tmp_path)
    assert proc.returncode == 1 and proc.stderr.startswith("review-chain-eval: refusing to overwrite")


# --- fix-loop round 2 ---

def test_concurrent_run_on_same_output_keeps_each_runs_results(tmp_path):
    """A second runner on the same --output starts and finishes while the first is mid-run (after it has
    already saved a partial); both keep their results and neither touches the other's partial."""
    fixtures_a, fixtures_b = tmp_path / "fa", tmp_path / "fb"
    write_fixture(fixtures_a, "a-one", TRUTH)
    write_fixture(fixtures_a, "a-two", TRUTH)
    write_fixture(fixtures_b, "b-one", TRUTH)
    out = tmp_path / "out.json"
    ok_stub = custom_stub(tmp_path, OK_BODY, name="claude-ok")
    calls = tmp_path / "a-calls"
    other_run = (f"[ \"$1\" = \"--version\" ] || echo x >> \"{calls}\"\n"
                 f"if [ \"$1\" != \"--version\" ] && [ \"$(wc -l < \"{calls}\")\" -eq 2 ]; then "
                 f"\"{sys.executable}\" \"{RUNNER}\" --claude \"{ok_stub}\" --model m --effort low "
                 f"--output \"{out}\" --fixtures \"{fixtures_b}\" > \"{tmp_path / 'b.log'}\" 2>&1; fi\n")
    proc = run_runner(custom_stub(tmp_path, other_run + OK_BODY, name="claude-a"), out, fixtures_a)
    assert proc.returncode == 1, proc.stderr
    assert sorted(json.loads(out.read_text())["cases"]) == ["b-one"]
    partials = list(tmp_path.glob("out.json*.partial"))
    assert len(partials) == 1 and partials[0].name in proc.stderr
    assert sorted(json.loads(partials[0].read_text())["cases"]) == ["a-one", "a-two"]


def test_relative_claude_path_works_from_temp_cwd(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    custom_stub(tmp_path, OK_BODY, name="claude-rel")
    out = tmp_path / "out.json"
    proc = subprocess.run([sys.executable, RUNNER, "--claude", "./claude-rel", "--model", "m", "--effort", "low",
                           "--output", str(out), "--fixtures", str(fixtures)], capture_output=True, text=True, cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(out.read_text())["cases"]["one"]["rc"] == 0


def test_review_call_oserror_is_recorded_as_errored(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "one", TRUTH)
    stub = custom_stub(tmp_path, "if [ \"$1\" = \"--version\" ]; then rm -f \"$0\"; echo 1.0; exit 0; fi\n" + OK_BODY)
    out = tmp_path / "out.json"
    proc = run_runner(stub, out, fixtures)
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr
    case = json.loads(out.read_text())["cases"]["one"]
    assert case["rc"] == "error" and case["result"] == "" and case["reason"]
    scored = run_score(out, fixtures)
    assert "one [core]: ERROR (rc=error)" in scored.stdout


def test_inline_fence_mention_does_not_swallow_the_real_block():
    text = ("I'll return the findings in a ```json block below.\n\n```json\n"
            + json.dumps([finding(summary="kept")]) + "\n```\n")
    findings, blocks = parse_findings(text)
    assert blocks == 1 and [f["summary"] for f in findings] == ["kept"]


def test_indented_fence_is_accepted():
    text = "  ```json\n" + json.dumps([finding(summary="kept")]) + "\n  ```\n"
    findings, blocks = parse_findings(text)
    assert blocks == 1 and len(findings) == 1


def test_score_exits_1_when_no_fixture_could_be_scored(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_fixture(fixtures, "a", TRUTH)
    write_fixture(fixtures, "b", TRUTH)
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"cases": {"a": {"rc": 2, "result": ""}, "b": {"rc": 0, "result": "```json\n{x\n```\n"}}}))
    proc = run_score(path, fixtures)
    assert proc.returncode == 1
    assert "review-chain-eval: no fixture could be scored (1 errored, 1 unparseable of 2)" in proc.stderr


def test_check_truth_names_missing_truth_and_ignores_non_fixture_dirs(tmp_path):
    write_fixture(tmp_path, "good", TRUTH)
    (write_fixture(tmp_path, "keyless", TRUTH) / "truth.json").unlink()
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "README.md").write_text("x")
    assert check_truth(tmp_path) == ["keyless: missing truth.json (every fixture needs an answer key)"]
    proc = subprocess.run([sys.executable, SCORER, "--check-truth", str(tmp_path)], capture_output=True, text=True)
    assert proc.returncode == 1
    assert proc.stderr.strip() == "review-chain-eval: keyless: missing truth.json (every fixture needs an answer key)"


def test_diff_paths_reads_headers_only():
    from score_review_chain_eval import diff_paths
    diff = ("diff --git a/app/x.py b/app/x.py\n--- a/app/x.py\n+++ b/app/x.py\n@@ -1,3 +1,3 @@\n"
            "--- body/removed.py\n context\n+++ body/added.py\n+++ also/added.py\n"
            "--- a/app/y.py\n+++ b/app/y.py\n")
    assert diff_paths(diff) == {"app/x.py", "app/y.py"}


FIXTURES = SCRIPTS.parent / "evals" / "skills" / "review-chain" / "fixtures"


@pytest.mark.parametrize("fixture, expected, summary", [
    ("none-deref", "false_positive", "Any authenticated caller can read another user's address by accessing `user.email` "
                                     "for an arbitrary `user_id`; there is no ownership check."),
    ("none-deref", "false_positive", "`response_model` is missing so the raw `user.email` is returned; accessing it "
                                     "directly leaks fields."),
    ("none-deref", "planted", "The handler reads .email on a null value when the id is unknown, causing a server error."),
    ("none-deref", "planted", "user may be None for an unknown id; accessing user.email fails."),
    ("missing-await", "false_positive", "`count_active` does not await anything, so it should not be async; make it synchronous."),
    ("missing-await", "planted", "The call to count_active isn't awaited, so count is a coroutine."),
    ("missing-await", "planted", "count_active is not awaited; comparing count < 0 raises TypeError."),
])
def test_real_answer_keys_classify_known_phrasings(fixture, expected, summary):
    from score_review_chain_eval import load_truth
    truth = load_truth(FIXTURES / fixture)
    f = finding(file=truth["planted"]["file"], summary=summary)
    assert classify(f, truth) == expected
