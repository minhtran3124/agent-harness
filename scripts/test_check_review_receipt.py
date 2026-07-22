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


def new_specs_commit(repo: Path, slug: str) -> None:
    """Advance HEAD with a specs/-only bookkeeping commit (the plan-shipped kind)."""
    plan = repo / "specs" / slug / "PLAN.md"
    plan.write_text("status: shipped\n", encoding="utf-8")
    _git(repo, "add", str(plan.relative_to(repo)))
    _git(repo, "commit", "-q", "-m", "chore: mark plan shipped")


def commit_file(repo: Path, relpath: str, content: str = "x\n") -> None:
    """Create/overwrite relpath and commit it; return nothing."""
    p = repo / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _git(repo, "add", relpath)
    _git(repo, "commit", "-q", "-m", f"add {relpath}")


def audit_data(sha: str, audit_result: str = "pass") -> dict:
    d = valid_data(sha)
    d["reviews"].append(
        {
            "type": "context-propagation-audit",
            "reviewer": "sonnet",
            "result": audit_result,
            "blocking_open": 0,
            "advisory_open": 0,
        }
    )
    return d


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


def test_specs_only_advance_stays_valid(tmp_path):
    # The plan-shipped bookkeeping commit touches only specs/ — it must NOT stale
    # a valid receipt (Codex P1 on PR #155): finishing validates, commits the
    # shipped status, then pushes; the pushed SHA differs only by that commit.
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    new_specs_commit(repo, "gh-x")
    assert crr.main([str(slug_dir), "--require", "correctness,intent"]) == 0


def test_symbolic_reviewed_sha_is_rejected(tmp_path, capsys):
    # A symbolic ref (e.g. literal "HEAD") must NOT be accepted: git diff HEAD..HEAD
    # is always empty and would fail-open. Require a resolved 40-hex sha.
    repo = make_repo(tmp_path)
    data = valid_data("HEAD")
    slug_dir = write_receipt(repo, "gh-x", data)
    new_commit(repo)  # land unreviewed code after review
    assert crr.main([str(slug_dir), "--require", "correctness,intent"]) == 1
    assert "malformed" in capsys.readouterr().err


def test_mixed_advance_with_code_still_stale(tmp_path, capsys):
    # A specs/ change AND a code change after review is unreviewed code → stale.
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    (repo / "specs" / "gh-x" / "PLAN.md").write_text(
        "status: shipped\n", encoding="utf-8"
    )
    (repo / "seed.txt").write_text("sneaky code change\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "shipped + code")
    assert crr.main([str(slug_dir)]) == 1
    assert "stale-sha" in capsys.readouterr().err


def test_non_pass_result_is_rejected(tmp_path, capsys):
    # A recorded review with result 'pending' (or skipped/typo/absent) must fail —
    # not only 'fail'. An incomplete outcome cannot authorize a push.
    repo = make_repo(tmp_path)
    data = audit_data(head_sha(repo), audit_result="pending")
    slug_dir = write_receipt(repo, "gh-x", data)
    assert crr.main([str(slug_dir), "--require", "correctness,intent"]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_missing_result_is_rejected(tmp_path, capsys):
    repo = make_repo(tmp_path)
    data = valid_data(head_sha(repo))
    del data["reviews"][0]["result"]  # absent result
    slug_dir = write_receipt(repo, "gh-x", data)
    assert crr.main([str(slug_dir)]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_require_audit_if_workflow_engine_change_missing_audit(tmp_path, capsys):
    # A workflow-engine diff with a receipt that omits context-propagation-audit
    # must be blocked when --require-audit-if is given.
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "skills/demo/SKILL.md", "# demo skill\n")
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    rc = crr.main(
        [str(slug_dir), "--require", "correctness,intent", "--require-audit-if", base]
    )
    assert rc == 1
    assert "context-propagation-audit" in capsys.readouterr().err


def test_require_audit_if_workflow_engine_change_with_audit_passes(tmp_path):
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "skills/demo/subagents/worker-prompt.md", "# nested prompt\n")
    slug_dir = write_receipt(repo, "gh-x", audit_data(head_sha(repo)))
    rc = crr.main(
        [str(slug_dir), "--require", "correctness,intent", "--require-audit-if", base]
    )
    assert rc == 0


def test_require_audit_if_non_workflow_change_does_not_require_audit(tmp_path):
    # A prose-only / code-only diff that does NOT touch a workflow-engine surface
    # must not demand the audit.
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "app/service.py", "x = 1\n")
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    rc = crr.main(
        [str(slug_dir), "--require", "correctness,intent", "--require-audit-if", base]
    )
    assert rc == 0


def test_require_audit_if_readme_excluded(tmp_path):
    # agents/README.md is prose — excluded from the workflow-engine signal.
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "agents/README.md", "# agents inventory\n")
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    rc = crr.main(
        [str(slug_dir), "--require", "correctness,intent", "--require-audit-if", base]
    )
    assert rc == 0


def test_require_audit_if_bad_base_fails_closed(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    rc = crr.main(
        [
            str(slug_dir),
            "--require-audit-if",
            "0000000000000000000000000000000000000000",
        ]
    )
    assert rc == 1
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
