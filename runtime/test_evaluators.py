import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import evaluator_result as er
import evaluators as ev

RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(RUNTIME_DIR)
SCRIPT = os.path.join(RUNTIME_DIR, "evaluators.py")
PASS_FIXTURE = os.path.join(RUNTIME_DIR, "testdata", "evaluator-pass", "SUMMARY.md")
FIXTURE_CMD = "`python3 scripts/verify_summary.py --lane runtime/testdata/evaluator-pass/SUMMARY.md`"

REASON_LINE = (
    "Reason: Tracked pass fixture for the Evaluator Protocol v1 adapters; "
    "no hard gate fires."
)

IDS = (
    "verify-summary-lane",
    "verify-summary-check",
    "check-verify-rows",
    "check-review-receipt",
)


def read_fixture() -> str:
    with open(PASS_FIXTURE, encoding="utf-8") as f:
        return f.read()


def direct(evaluator_id, args, repo_root) -> subprocess.CompletedProcess:
    """Run the wrapped checker itself, bypassing the adapter — the parity oracle."""
    entry = ev.load_registry()[evaluator_id]
    argv = [
        "python3",
        os.path.join(repo_root, entry["script"]),
        *entry["argv_prefix"],
        *args,
        *entry["argv_suffix"],
    ]
    return subprocess.run(
        argv,
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def cli(evaluator_id, args, repo_root) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "run",
            "--repo-root",
            repo_root,
            evaluator_id,
            "--",
            *args,
        ],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def assert_parity(evaluator_id, args, repo_root, expected_exit):
    oracle = direct(evaluator_id, args, repo_root)
    assert oracle.returncode == expected_exit, (
        "fixture does not exercise the intended exit path: "
        f"{oracle.stdout}{oracle.stderr}"
    )
    result = ev.run(evaluator_id, args, repo_root=repo_root)
    assert result["exit"] == oracle.returncode
    proc = cli(evaluator_id, args, repo_root)
    assert proc.returncode == oracle.returncode, proc.stderr
    assert json.loads(proc.stdout)["exit"] == oracle.returncode


# --- temp spec fixtures -------------------------------------------------------


@pytest.fixture
def specs(tmp_path):
    """A temp specs/ tree: a passing SUMMARY, a failing one, and a receipt-less dir."""
    good = tmp_path / "specs" / "good"
    good.mkdir(parents=True)
    (good / "SUMMARY.md").write_text(read_fixture(), encoding="utf-8")

    bad = tmp_path / "specs" / "bad"
    bad.mkdir()
    # a placeholder Reason fails the lane check; a piped command trips check_verify_rows.
    text = read_fixture().replace(REASON_LINE, "Reason: <one sentence>")
    text = text.replace(FIXTURE_CMD, "`echo x \\| grep x`")
    (bad / "SUMMARY.md").write_text(text, encoding="utf-8")

    (tmp_path / "specs" / "no-receipt").mkdir()
    return tmp_path


@pytest.fixture
def check_root(tmp_path):
    """verify_summary.py resolves specs/ from ITS OWN location, not cwd — so
    `<slug> --check` can only see a temp spec when a copy of the script lives in a
    temp repo root beside it."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(os.path.join(REPO_ROOT, "scripts", "verify_summary.py"), scripts)
    for slug, cmd in (("good", "test -d specs"), ("bad", "test -d nope")):
        d = tmp_path / "specs" / slug
        d.mkdir(parents=True)
        text = read_fixture().replace(FIXTURE_CMD, f"`{cmd}`")
        (d / "SUMMARY.md").write_text(text, encoding="utf-8")
    return tmp_path


@pytest.fixture
def receipt_repo(tmp_path):
    """A git repo whose specs/ok/ carries a receipt pinned at HEAD."""
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run([*git, "init", "-q"], cwd=tmp_path, check=True, env=env)
    subprocess.run(
        [*git, "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        check=True,
        env=env,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()
    ok = tmp_path / "specs" / "ok"
    ok.mkdir(parents=True)
    receipt = {
        "reviewed_head_sha": head,
        "reviews": [{"type": "correctness", "result": "pass", "blocking_open": 0}],
    }
    (ok / ".review-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    return tmp_path


# --- registry (SC-3) ------------------------------------------------------------


def test_registry_has_exactly_four_entries_with_required_keys():
    reg = ev.load_registry()
    assert tuple(reg) == IDS
    for entry in reg.values():
        assert set(entry) == {
            "script",
            "tier",
            "argv_prefix",
            "argv_suffix",
            "description",
        }
        assert entry["tier"] == "deterministic"
        assert os.path.isfile(os.path.join(REPO_ROOT, entry["script"]))


def test_list_check_prints_four_ids_and_exits_0():
    proc = subprocess.run(
        [sys.executable, SCRIPT, "list", "--check"], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == list(IDS)


def test_list_check_fails_when_a_script_is_missing(monkeypatch):
    reg = ev.load_registry()
    reg["check-verify-rows"]["script"] = "scripts/does-not-exist.py"
    monkeypatch.setattr(ev, "load_registry", lambda: reg)
    assert ev.main(["list", "--check"]) == 1
    assert ev.main(["list"]) == 0


def test_list_check_fails_when_count_is_not_four(monkeypatch):
    reg = ev.load_registry()
    del reg["check-verify-rows"]
    monkeypatch.setattr(ev, "load_registry", lambda: reg)
    assert ev.main(["list", "--check"]) == 1


def test_unknown_id_exits_2():
    proc = subprocess.run(
        [sys.executable, SCRIPT, "run", "nope", "--", "x"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "nope" in proc.stderr
    with pytest.raises(KeyError):
        ev.run("nope", [], repo_root=REPO_ROOT)


# --- parity (SC-5) --------------------------------------------------------------


def test_parity_verify_summary_lane(specs):
    good, bad = (
        str(specs / "specs/good/SUMMARY.md"),
        str(specs / "specs/bad/SUMMARY.md"),
    )
    assert_parity("verify-summary-lane", [good], REPO_ROOT, 0)
    assert_parity("verify-summary-lane", [bad], REPO_ROOT, 1)
    assert_parity("verify-summary-lane", [], REPO_ROOT, 2)


def test_parity_verify_summary_check(check_root):
    root = str(check_root)
    assert_parity("verify-summary-check", ["good"], root, 0)
    assert_parity("verify-summary-check", ["bad"], root, 1)
    assert_parity("verify-summary-check", ["absent-slug"], root, 2)


def test_parity_check_verify_rows(specs):
    good, bad = (
        str(specs / "specs/good/SUMMARY.md"),
        str(specs / "specs/bad/SUMMARY.md"),
    )
    assert_parity("check-verify-rows", [good], REPO_ROOT, 0)
    assert_parity("check-verify-rows", [bad], REPO_ROOT, 1)


def test_parity_check_review_receipt(receipt_repo, specs):
    ok, missing = str(receipt_repo / "specs/ok"), str(specs / "specs/no-receipt")
    assert_parity("check-review-receipt", [ok], REPO_ROOT, 0)
    assert_parity("check-review-receipt", [missing], REPO_ROOT, 1)
    assert_parity("check-review-receipt", [], REPO_ROOT, 2)


def test_parity_tracked_pass_fixture_is_schema_valid_json_on_stdout():
    rel = os.path.relpath(PASS_FIXTURE, REPO_ROOT)
    proc = cli("verify-summary-lane", [rel], REPO_ROOT)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)  # a single JSON object, nothing else on stdout
    assert result["status"] == "pass"
    assert er.validate(result) == []


# --- status mapping + evidence (SC-6) --------------------------------------------


def test_status_mapping_pass(specs):
    good = str(specs / "specs/good/SUMMARY.md")
    result = ev.run("verify-summary-lane", [good], repo_root=REPO_ROOT)
    assert result["status"] == "pass"
    assert result["score"] is None
    assert result["evaluator"] == "verify-summary-lane"
    assert result["argv"][0] == "python3"
    assert result["argv"][2:] == ["--lane", good]
    assert isinstance(result["duration_ms"], int)
    assert er.validate(result) == []


def test_status_mapping_fail_captures_stderr_line(specs):
    missing = str(specs / "specs/no-receipt")
    result = ev.run("check-review-receipt", [missing], repo_root=REPO_ROOT)
    assert result["status"] == "fail"
    assert result["exit"] == 1
    lines = [e["message"] for e in result["evidence"] if e["source"] == "stderr"]
    assert len(lines) == 1 and "missing" in lines[0]


def test_status_mapping_fail_captures_stdout_lines(specs):
    bad = str(specs / "specs/bad/SUMMARY.md")
    result = ev.run("check-verify-rows", [bad], repo_root=REPO_ROOT)
    assert result["status"] == "fail"
    assert any(
        e["source"] == "stdout" and "pipe" in e["message"] for e in result["evidence"]
    )
    assert all(e["message"].strip() for e in result["evidence"])


def test_status_mapping_bad_invocation_is_error():
    result = ev.run("verify-summary-lane", [], repo_root=REPO_ROOT)
    assert result["status"] == "error"
    assert result["exit"] == 2


def test_status_mapping_missing_script_is_error(monkeypatch):
    reg = ev.load_registry()
    reg["check-verify-rows"]["script"] = "scripts/does-not-exist.py"
    monkeypatch.setattr(ev, "load_registry", lambda: reg)
    result = ev.run("check-verify-rows", [], repo_root=REPO_ROOT)
    assert result["status"] == "error"
    assert result["exit"] == 2  # python3 itself exits 2 on a missing script
    assert er.validate(result) == []


def test_status_mapping_unspawnable_interpreter_is_error(monkeypatch):
    monkeypatch.setattr(ev, "PYTHON", "/nonexistent/python3")
    result = ev.run("check-verify-rows", [], repo_root=REPO_ROOT)
    assert result["status"] == "error"
    assert result["exit"] == 127
    assert result["evidence"][0]["source"] == "stderr"
    assert er.validate(result) == []


def test_status_mapping_zero_arg_check_verify_rows_returns_instead_of_blocking():
    # check_verify_rows.py reads stdin when given no args; a closed stdin makes it return.
    proc = subprocess.run(
        [sys.executable, SCRIPT, "run", "check-verify-rows", "--"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["status"] == "pass"
    result = ev.run("check-verify-rows", [], repo_root=REPO_ROOT)
    assert result["status"] == "pass"


def test_status_mapping_adapter_leaves_the_worktree_untouched(specs):
    good = str(specs / "specs/good/SUMMARY.md")
    before = sorted(os.listdir(REPO_ROOT))
    ev.run("verify-summary-lane", [good], repo_root=REPO_ROOT)
    assert sorted(os.listdir(REPO_ROOT)) == before
