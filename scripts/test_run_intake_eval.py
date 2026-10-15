"""Tests for run_intake_eval.py: each runs on a throwaway git repo with a stub client."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import run_intake_eval

SCORER = Path(__file__).resolve().parent / "score_intake_eval.py"
FIXTURES = "evals/workflow/intake-classifier/fixtures"
TRUTH = ("expected_lane: tiny\nexpected_confidence: high\nexpected_hard_gate: none\n"
         "expected_flags_include: none\nexpected_escalate: no\n---\n# truth\n")
DEPLOY = '#!/bin/bash\nmkdir -p "$2/.claude"\necho deployed > "$2/.claude/marker"\n'
STUB = f"""#!{sys.executable}
import json, os, subprocess, sys
from pathlib import Path
if "--version" in sys.argv:
    print("stub-claude 1.0")
    sys.exit(0)
prompt = sys.argv[sys.argv.index("-p") + 1]
wt = Path.cwd()
head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(json.dumps({{"head": head, "only_in_head": (wt / "only-in-head.txt").exists(),
                          "evals": (wt / "evals").exists(),
                          "marker": (wt / ".claude" / "marker").exists()}}) + "\\n")
(wt / "specs" / "x").mkdir(parents=True, exist_ok=True)
(wt / "specs" / "x" / "SUMMARY.md").write_text("Lane: tiny\\n")
if "MODE:readme" in prompt:
    (wt / "README.md").write_text("changed by the agent\\n")
if "MODE:branch" in prompt:
    subprocess.run(["git", "branch", "stray-branch"], check=True)
if "MODE:tamper" in prompt:
    Path(os.environ["STUB_REPO"], "scripts", "score_intake_eval.py").write_text('print("TAMPERED")\\n')
reply = "Classified.\\n\\nLane: tiny\\nConfidence: high\\nReason: stub\\nFlags: none\\nEscalate: no\\n"
print(json.dumps({{"type": "result", "result": reply}}))
"""


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo,
                          check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def env(tmp_path, monkeypatch):
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(SCORER, repo / "scripts" / "score_intake_eval.py")
    (repo / "scripts" / "deploy-harness.sh").write_text(DEPLOY)
    (repo / "README.md").write_text("original\n")
    (repo / FIXTURES).mkdir(parents=True)
    (repo / "evals" / "pinned.txt").write_text("tracked at the pinned commit\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "older")
    pinned = git(repo, "rev-parse", "HEAD")
    (repo / "only-in-head.txt").write_text("newer\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "newer")
    stub = tmp_path / "claude"
    stub.write_text(STUB)
    stub.chmod(0o755)
    log = tmp_path / "stub.log"
    monkeypatch.setenv("STUB_LOG", str(log))
    monkeypatch.setenv("STUB_REPO", str(repo))
    monkeypatch.chdir(repo)
    return argparse.Namespace(repo=repo, pinned=pinned, stub=stub, log=log, out=tmp_path / "out")


def add_fixture(env, name, mode="", meta=None):
    fixture = env.repo / FIXTURES / name
    fixture.mkdir(parents=True)
    (fixture / "request.md").write_text(f"Fix a typo in the README. {mode}\n")
    (fixture / "truth.md").write_text(TRUTH)
    meta = meta if meta is not None else {"from": env.pinned, "may_change": ["specs/*/SUMMARY.md"]}
    (fixture / "eval.json").write_text(json.dumps(meta))
    return fixture


def run(env, *extra):
    return run_intake_eval.main(["--model", "m", "--output-dir", str(env.out),
                                 "--claude", str(env.stub), *extra])


def cases(env):
    return json.loads((env.out / "run.json").read_text())["fixtures"]


def test_scratch_worktree_starts_at_from_without_evals(env):
    add_fixture(env, "clean")
    assert "evals/pinned.txt" in git(env.repo, "ls-tree", "-r", "--name-only", env.pinned).splitlines()
    assert run(env) == 0
    seen = [json.loads(line) for line in env.log.read_text().splitlines()]
    assert seen == [{"head": env.pinned, "only_in_head": False, "evals": False, "marker": True}]
    assert git(env.repo, "rev-parse", "HEAD") != env.pinned


def test_stray_outside_may_change_fails_inside_passes(env):
    add_fixture(env, "clean")
    add_fixture(env, "readme", "MODE:readme")
    add_fixture(env, "branch", "MODE:branch")
    assert run(env) == 1
    got = cases(env)
    assert (got["clean"]["status"], got["clean"]["stray"]) == ("ok", [])
    assert (got["readme"]["status"], got["readme"]["stray"]) == ("stray", ["README.md"])
    assert (got["branch"]["status"], got["branch"]["stray"]) == ("stray", ["ref:refs/heads/stray-branch"])
    assert not (env.out / "readme.md").exists()
    assert (env.out / "readme.raw.txt").is_file()


def test_scorer_copy_ignores_in_tree_tamper(env):
    add_fixture(env, "tamper", "MODE:tamper")
    assert run(env) == 0
    assert "TAMPERED" in (env.repo / "scripts" / "score_intake_eval.py").read_text()
    scorecard = (env.out / "scorecard.txt").read_text()
    assert "TAMPERED" not in scorecard
    assert "Intake-Classifier Scorecard" in scorecard


def test_bare_never_in_client_command(monkeypatch):
    cmd = run_intake_eval.build_cmd(argparse.Namespace(claude="claude", model="m"), "prompt")
    assert "--bare" not in cmd
    i = cmd.index("--setting-sources")
    assert cmd[i + 1] == "project"
    monkeypatch.setattr(run_intake_eval, "CLIENT_FLAGS", [*run_intake_eval.CLIENT_FLAGS, "--bare"])
    with pytest.raises(ValueError):
        run_intake_eval.build_cmd(argparse.Namespace(claude="claude", model="m"), "prompt")


def test_end_to_end_one_clean_one_stray(env):
    add_fixture(env, "clean")
    add_fixture(env, "readme", "MODE:readme")
    assert run(env) == 1
    assert sorted(p.name for p in env.out.glob("*.md")) == ["clean.md"]
    assert "Lane: tiny" in (env.out / "clean.md").read_text()
    record = json.loads((env.out / "run.json").read_text())
    assert record["schema_version"] == 1 and record["client"] == "stub-claude 1.0"
    assert record["head"] == git(env.repo, "rev-parse", "HEAD")
    assert len(git(env.repo, "worktree", "list").splitlines()) == 1


def test_end_to_end_refuses_existing_output_dir(env):
    add_fixture(env, "clean")
    env.out.mkdir()
    with pytest.raises(SystemExit):
        run(env)


@pytest.mark.parametrize("meta", [
    {"from": "xyz", "may_change": []},
    {"from": "0" * 40, "may_change": []},
    {"from": "PINNED", "may_change": "specs/*"},
    {"from": "PINNED", "may_change": [1]},
])
def test_load_meta_rejects_invalid(env, meta):
    meta = {k: (env.pinned if v == "PINNED" else v) for k, v in meta.items()}
    fixture = add_fixture(env, "bad", meta=meta)
    with pytest.raises(ValueError, match="bad"):
        run_intake_eval.load_meta(fixture)


def test_load_meta_rejects_missing_file(env):
    fixture = add_fixture(env, "bad")
    (fixture / "eval.json").unlink()
    with pytest.raises(ValueError, match="bad"):
        run_intake_eval.load_meta(fixture)


def test_check_fixtures_exit_codes(env):
    add_fixture(env, "good")
    assert run_intake_eval.main(["--check-fixtures"]) == 0
    add_fixture(env, "bad", meta={"from": "xyz", "may_change": []})
    assert run_intake_eval.main(["--check-fixtures"]) == 1
