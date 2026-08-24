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


def install_root(repo_root) -> str:
    """Where registry ``script`` paths resolve: ``<root>/.claude`` for a deployed tree."""
    deployed = os.path.join(repo_root, ".claude")
    if os.path.isfile(os.path.join(deployed, "runtime", "evaluators.py")):
        return deployed
    return repo_root


def deploy_tree(tmp_path, scripts=()):
    """Build ``<tmp>/.claude/{runtime,scripts}/`` the way deploy-harness.sh lays it out."""
    install = tmp_path / ".claude"
    (install / "runtime").mkdir(parents=True)
    (install / "scripts").mkdir()
    for name in (
        "evaluators.py",
        "evaluator_result.py",
        "evaluator-result.schema.json",
        "evaluators.json",
    ):
        shutil.copy(os.path.join(RUNTIME_DIR, name), install / "runtime")
    for name in scripts:
        shutil.copy(os.path.join(REPO_ROOT, "scripts", name), install / "scripts")
    return install


def direct(evaluator_id, args, repo_root) -> subprocess.CompletedProcess:
    """Run the wrapped checker itself, bypassing the adapter — the parity oracle."""
    entry = ev.load_registry()[evaluator_id]
    argv = [
        "python3",
        os.path.join(install_root(repo_root), entry["script"]),
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
            os.path.join(install_root(repo_root), "runtime", "evaluators.py"),
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
def check_root(tmp_path, monkeypatch):
    """verify_summary.py resolves specs/ from ITS OWN location, not cwd — so
    `<slug> --check` can only see a temp spec when a deployed copy of the script lives
    under a temp project's `.claude/scripts/` (the adapter resolves scripts against its
    install root, so the in-process runs need that root pointed at the temp tree)."""
    install = deploy_tree(tmp_path, scripts=["verify_summary.py"])
    monkeypatch.setattr(ev, "INSTALL_ROOT", install)
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
            "requires_args",
        }
        assert entry["tier"] == "deterministic"
        assert entry["requires_args"] is True
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
    assert_parity("verify-summary-lane", ["--no-such-flag"], REPO_ROOT, 2)


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
    assert_parity("check-review-receipt", ["--no-such-flag"], REPO_ROOT, 2)


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


def test_status_mapping_bad_invocation_is_error(check_root):
    result = ev.run("verify-summary-check", ["absent-slug"], repo_root=str(check_root))
    assert result["status"] == "error"
    assert result["exit"] == 2


def test_status_mapping_missing_script_is_error(monkeypatch):
    reg = ev.load_registry()
    reg["check-verify-rows"]["script"] = "scripts/does-not-exist.py"
    monkeypatch.setattr(ev, "load_registry", lambda: reg)
    result = ev.run("check-verify-rows", ["x"], repo_root=REPO_ROOT)
    assert result["status"] == "error"
    assert result["exit"] == 2  # python3 itself exits 2 on a missing script
    assert er.validate(result) == []


def test_status_mapping_unspawnable_interpreter_is_error(monkeypatch):
    monkeypatch.setattr(ev, "PYTHON", "/nonexistent/python3")
    result = ev.run("check-verify-rows", ["x"], repo_root=REPO_ROOT)
    assert result["status"] == "error"
    assert result["exit"] == 127
    assert result["evidence"][0]["source"] == "stderr"
    assert er.validate(result) == []


def test_status_mapping_zero_arg_check_verify_rows_is_skipped_exit_3():
    # check_verify_rows.py reads stdin when given no args; the adapter never spawns a
    # requires_args evaluator with no targets, and "skipped" is not a pass (exit 3).
    proc = subprocess.run(
        [sys.executable, SCRIPT, "run", "check-verify-rows", "--"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 3
    assert json.loads(proc.stdout)["status"] == "skipped"
    result = ev.run("check-verify-rows", [], repo_root=REPO_ROOT)
    assert result["status"] == "skipped"
    assert result["exit"] == 3
    assert result["evidence"] == [
        {"source": "adapter", "message": "no targets given; nothing evaluated"}
    ]
    assert er.validate(result) == []


def test_status_mapping_zero_arg_spawn_does_not_block_on_stdin(monkeypatch):
    # With requires_args off the checker really is spawned with no targets, so it
    # reads stdin; stdin=DEVNULL is what makes it return (exit 0 on no targets).
    reg = ev.load_registry()
    reg["check-verify-rows"]["requires_args"] = False
    monkeypatch.setattr(ev, "load_registry", lambda: reg)
    result = ev.run("check-verify-rows", [], repo_root=REPO_ROOT, timeout_s=10)
    assert result["status"] == "pass", result["evidence"]
    assert result["exit"] == 0


def test_status_mapping_adapter_leaves_the_worktree_untouched(specs):
    good = str(specs / "specs/good/SUMMARY.md")
    before = sorted(os.listdir(REPO_ROOT))
    ev.run("verify-summary-lane", [good], repo_root=REPO_ROOT)
    assert sorted(os.listdir(REPO_ROOT)) == before


# --- correctness-review fixes ---------------------------------------------------


def fake_checker(monkeypatch, tmp_path, body: str, *, requires_args=False) -> str:
    """Register a single temp checker script under tmp_path as evaluator 'fake'."""
    (tmp_path / "check.py").write_text(body, encoding="utf-8")
    reg = {
        "fake": {
            "script": "check.py",
            "tier": "deterministic",
            "argv_prefix": [],
            "argv_suffix": [],
            "description": "temp checker",
            "requires_args": requires_args,
        }
    }
    monkeypatch.setattr(ev, "load_registry", lambda: reg)
    monkeypatch.setattr(ev, "INSTALL_ROOT", tmp_path)
    return str(tmp_path)


def test_relative_repo_root_runs_the_checker(monkeypatch):
    # F1: a relative root must not be prefixed onto argv AND used as cwd.
    monkeypatch.chdir(os.path.dirname(REPO_ROOT))
    rel_root = os.path.basename(REPO_ROOT)
    rel_fixture = os.path.relpath(PASS_FIXTURE, REPO_ROOT)
    result = ev.run("verify-summary-lane", [rel_fixture], repo_root=rel_root)
    assert result["status"] == "pass", result["evidence"]
    assert os.path.isabs(result["argv"][1])


def test_default_repo_root_strips_a_deployed_dot_claude(monkeypatch, tmp_path):
    # F2/R1: a deployed copy lives at <project>/.claude/runtime/evaluators.py, so the
    # install root is <project>/.claude and the project root one level further out.
    monkeypatch.setattr(ev, "INSTALL_ROOT", tmp_path / ".claude")
    assert ev.default_repo_root() == tmp_path
    monkeypatch.setattr(ev, "INSTALL_ROOT", tmp_path / "harness")
    assert ev.default_repo_root() == tmp_path / "harness"


def test_list_check_resolves_scripts_under_install_root(monkeypatch, tmp_path):
    monkeypatch.setattr(ev, "INSTALL_ROOT", tmp_path)
    assert ev.main(["list", "--check"]) == 1
    monkeypatch.setattr(ev, "INSTALL_ROOT", ev.Path(REPO_ROOT))
    assert ev.main(["list", "--check"]) == 0


def test_deployed_adapter_uses_dot_claude_scripts_and_project_cwd(tmp_path):
    # R1: deployed, the registry's scripts live under <project>/.claude/scripts/ while
    # the checker must run with cwd=<project> so relative targets resolve there.
    install = deploy_tree(tmp_path)
    fake = install / "scripts" / "fake.py"
    fake.write_text(
        "import os, sys\n"
        "print(os.getcwd())\n"
        "print(os.path.abspath(__file__))\n"
        "print(sys.argv[1])\n",
        encoding="utf-8",
    )
    registry = {
        "fake": {
            "script": "scripts/fake.py",
            "tier": "deterministic",
            "argv_prefix": [],
            "argv_suffix": [],
            "description": "records cwd + own path",
            "requires_args": True,
        }
    }
    (install / "runtime" / "evaluators.json").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    proc = subprocess.run(
        [sys.executable, str(install / "runtime" / "evaluators.py"), "run", "fake"]
        + ["--", "specs/x"],
        cwd=REPO_ROOT,  # somewhere else entirely: the adapter must not use its caller's cwd
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    project, script = str(tmp_path.resolve()), str(fake.resolve())
    seen = [e["message"] for e in result["evidence"] if e["source"] == "stdout"]
    assert seen == [project, script, "specs/x"]
    assert result["argv"][1] == script


def test_crashed_checker_is_error_not_fail(monkeypatch, tmp_path):
    # F4a: an uncaught exception exits 1 but is not a verdict.
    root = fake_checker(monkeypatch, tmp_path, "raise RuntimeError('boom')\n")
    result = ev.run("fake", ["x"], repo_root=root)
    assert result["exit"] == 125
    assert result["status"] == "error"
    assert any("Traceback" in e["message"] for e in result["evidence"])
    assert result["evidence"][-1] == {
        "source": "adapter",
        "message": "wrapped checker crashed (raw exit 1)",
    }
    assert er.validate(result) == []
    assert ev.main(["run", "--repo-root", root, "fake", "--", "x"]) == 125


def test_requires_args_evaluator_with_no_args_is_skipped_without_spawning(
    monkeypatch, tmp_path
):
    # F4b: the checker would write a marker file if it ran.
    body = "open('ran.txt', 'w').close()\n"
    root = fake_checker(monkeypatch, tmp_path, body, requires_args=True)
    result = ev.run("fake", [], repo_root=root)
    assert result["status"] == "skipped"
    assert result["exit"] == 3
    assert not (tmp_path / "ran.txt").exists()
    result = ev.run("fake", ["x"], repo_root=root)
    assert result["status"] == "pass"
    assert (tmp_path / "ran.txt").exists()


def test_missing_registry_file_exits_2(monkeypatch, tmp_path, capsys):
    # F5: a broken registry is a bad invocation, not a traceback.
    monkeypatch.setattr(ev, "REGISTRY_PATH", tmp_path / "absent.json")
    assert ev.main(["list"]) == 2
    assert "evaluators:" in capsys.readouterr().err
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    monkeypatch.setattr(ev, "REGISTRY_PATH", tmp_path / "bad.json")
    assert ev.main(["run", "x", "--", "y"]) == 2


def test_registry_entry_missing_a_key_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(ev, "load_registry", lambda: {"x": {"tier": "deterministic"}})
    assert ev.main(["list", "--check"]) == 2
    assert ev.main(["run", "x", "--", "y"]) == 2
    assert "script" in capsys.readouterr().err


def test_run_failures_are_not_reported_as_registry_errors(monkeypatch, capsys):
    # R4: only registry loading/lookup is guarded; a failure inside run() propagates.
    def boom(*_args, **_kwargs):
        raise BrokenPipeError("stdout closed")

    monkeypatch.setattr(ev, "run", boom)
    with pytest.raises(BrokenPipeError):
        ev.main(["run", "check-verify-rows", "--", "x"])
    assert "cannot use registry" not in capsys.readouterr().err


@pytest.mark.parametrize("bad", ["0", "nan", "inf", "-1"])
def test_run_cli_rejects_non_positive_or_non_finite_timeout(bad, capsys):
    # R5: one stderr line, exit 2, nothing spawned.
    assert ev.main(["run", "--timeout", bad, "check-verify-rows", "--", "x"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.count("\n") == 1 and "--timeout" in err


@pytest.mark.parametrize("bad", [0, float("nan"), float("inf")])
def test_run_rejects_non_positive_or_non_finite_timeout_s(bad):
    with pytest.raises(ValueError):
        ev.run("check-verify-rows", ["x"], repo_root=REPO_ROOT, timeout_s=bad)


def test_timeout_is_error_exit_124(monkeypatch, tmp_path):
    # F6: a hung checker is killed and reported, not awaited forever.
    root = fake_checker(monkeypatch, tmp_path, "import time; time.sleep(30)\n")
    result = ev.run("fake", ["x"], repo_root=root, timeout_s=1)
    assert result["exit"] == 124
    assert result["status"] == "error"
    assert any("timed out" in e["message"] for e in result["evidence"])
    assert result["duration_ms"] < 10_000
    assert er.validate(result) == []


def test_run_cli_accepts_timeout(monkeypatch, tmp_path):
    root = fake_checker(monkeypatch, tmp_path, "import time; time.sleep(30)\n")
    argv = ["run", "--repo-root", root, "--timeout", "1", "fake", "--", "x"]
    assert ev.main(argv) == 124
