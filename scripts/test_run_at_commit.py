"""Tests for run_at_commit.py.

Run:

    python -m pytest scripts/test_run_at_commit.py -q
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parent / "run_at_commit.py"
_SPEC = importlib.util.spec_from_file_location("run_at_commit", SCRIPT)
assert _SPEC and _SPEC.loader, "could not load run_at_commit.py"
rac = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rac)

PY = sys.executable


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway git repo with one commit; cwd is set to its root."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "marker.txt").write_text("at commit\n")
    _git(root, "add", "marker.txt")
    _git(root, "commit", "-q", "-m", "init")
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def tmpdirs(monkeypatch):
    """Record every directory the helper creates with mkdtemp."""
    made = []
    real = rac.tempfile.mkdtemp

    def recording(*a, **kw):
        path = real(*a, **kw)
        made.append(path)
        return path

    monkeypatch.setattr(rac.tempfile, "mkdtemp", recording)
    return made


def _assert_clean(repo, made):
    assert len(_git(repo, "worktree", "list").splitlines()) == 1
    for path in made:
        assert not os.path.exists(path)


def test_exit_code_comes_through(repo, tmpdirs):
    code = rac.main(["HEAD", "--", PY, "-c", "raise SystemExit(3)"])
    assert code == 3
    assert len(tmpdirs) == 1
    _assert_clean(repo, tmpdirs)


def test_runs_in_worktree_at_commit(repo, tmpdirs):
    sha = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "marker.txt").write_text("changed later\n")
    _git(repo, "commit", "-q", "-am", "later")
    check = "import sys; sys.exit(0 if open('marker.txt').read() == 'at commit\\n' else 5)"
    assert rac.main([sha, "--", PY, "-c", check]) == 0
    _assert_clean(repo, tmpdirs)


def test_unknown_sha_gives_125(repo, tmpdirs, capsys):
    assert rac.main(["0000000", "--", PY, "-c", "pass"]) == 125
    assert capsys.readouterr().err.startswith("run_at_commit:")
    _assert_clean(repo, tmpdirs)


def test_missing_separator_gives_125(repo, tmpdirs, capsys):
    assert rac.main(["HEAD", PY, "-c", "pass"]) == 125
    assert capsys.readouterr().err.startswith("run_at_commit:")
    _assert_clean(repo, tmpdirs)


def test_empty_command_gives_125(repo, tmpdirs, capsys):
    assert rac.main(["HEAD", "--"]) == 125
    assert capsys.readouterr().err.startswith("run_at_commit:")
    _assert_clean(repo, tmpdirs)


def test_unknown_binary_gives_125(repo, tmpdirs, capsys):
    assert rac.main(["HEAD", "--", "no-such-binary-xyz"]) == 125
    assert capsys.readouterr().err.startswith("run_at_commit:")
    _assert_clean(repo, tmpdirs)


def test_sigkill_gives_137(repo, tmpdirs):
    kill = "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"
    assert rac.main(["HEAD", "--", PY, "-c", kill]) == 137
    _assert_clean(repo, tmpdirs)


def test_timeout_gives_124(repo, tmpdirs, monkeypatch):
    monkeypatch.setattr(rac, "TIMEOUT_SECONDS", 1)
    assert rac.main(["HEAD", "--", PY, "-c", "import time; time.sleep(30)"]) == 124
    _assert_clean(repo, tmpdirs)


def test_absolute_path_invocation_from_repo_root(repo):
    result = subprocess.run(
        [PY, str(SCRIPT), "HEAD", "--", PY, "-c", "raise SystemExit(3)"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 3, result.stderr
    assert len(_git(repo, "worktree", "list").splitlines()) == 1
