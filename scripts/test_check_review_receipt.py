"""Tests for check_review_receipt.py.

Run:

    python -m pytest scripts/test_check_review_receipt.py -x -q

Hermetic: each test builds a throwaway git repo in tmp_path, writes a
.review-receipt.json under a slug dir inside it, and invokes the checker with
HEAD resolved from that repo.
"""

import importlib.util
import json
import subprocess
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "check_review_receipt", Path(__file__).resolve().parent / "check_review_receipt.py"
)
assert _SPEC and _SPEC.loader, "could not load check_review_receipt.py"
crr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(crr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def make_repo(tmp_path: Path) -> Path:
    """Init a throwaway repo with one commit; return the repo root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def head_sha(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD")


def new_commit(repo: Path) -> None:
    (repo / "seed.txt").write_text("changed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "second")


def write_receipt(repo: Path, slug: str, data) -> Path:
    slug_dir = repo / "specs" / slug
    slug_dir.mkdir(parents=True)
    receipt = slug_dir / crr.RECEIPT_NAME
    if isinstance(data, str):
        receipt.write_text(data, encoding="utf-8")
    else:
        receipt.write_text(json.dumps(data), encoding="utf-8")
    return slug_dir


def valid_data(sha: str) -> dict:
    return {
        "reviewed_head_sha": sha,
        "reviews": [
            {
                "type": "correctness",
                "reviewer": "opus",
                "result": "pass",
                "blocking_open": 0,
                "advisory_open": 1,
            },
            {
                "type": "intent",
                "reviewer": "opus",
                "result": "pass",
                "blocking_open": 0,
                "advisory_open": 0,
            },
        ],
        "created": "2026-07-22T00:00:00",
    }


# ---------------------------------------------------------------------------
# Test cases (mapped to the task's required 6)
# ---------------------------------------------------------------------------


def test_fresh_receipt_with_required_types_passes(tmp_path):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    assert crr.main([str(slug_dir), "--require", "correctness,intent"]) == 0


def test_new_commit_makes_receipt_stale(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    new_commit(repo)
    assert crr.main([str(slug_dir)]) == 1
    assert "stale-sha" in capsys.readouterr().err


def test_blocking_open_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    data = valid_data(head_sha(repo))
    data["reviews"][0]["blocking_open"] = 2
    slug_dir = write_receipt(repo, "gh-x", data)
    assert crr.main([str(slug_dir)]) == 1
    assert "blocking-open" in capsys.readouterr().err


def test_review_result_fail_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    data = valid_data(head_sha(repo))
    data["reviews"][1]["result"] = "fail"
    slug_dir = write_receipt(repo, "gh-x", data)
    assert crr.main([str(slug_dir)]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_missing_required_type_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    assert (
        crr.main([str(slug_dir), "--require", "correctness,context-propagation-audit"])
        == 1
    )
    assert "missing-required-type" in capsys.readouterr().err


def test_malformed_json_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", "{not valid json,,,")
    assert crr.main([str(slug_dir)]) == 1
    assert "malformed" in capsys.readouterr().err


def test_missing_receipt_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = repo / "specs" / "gh-x"
    slug_dir.mkdir(parents=True)
    assert crr.main([str(slug_dir)]) == 1
    assert "missing" in capsys.readouterr().err


def test_require_present_but_failed_is_not_satisfied(tmp_path, capsys):
    repo = make_repo(tmp_path)
    data = valid_data(head_sha(repo))
    data["reviews"][1]["result"] = "fail"  # intent present but failed
    slug_dir = write_receipt(repo, "gh-x", data)
    # review-failed is caught before the --require check
    assert crr.main([str(slug_dir), "--require", "intent"]) == 1
    assert "review-failed" in capsys.readouterr().err
