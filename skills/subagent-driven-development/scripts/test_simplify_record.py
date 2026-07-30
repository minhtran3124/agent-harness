"""Tests for simplify_record.py.

Run:

    python -m pytest skills/subagent-driven-development/scripts/test_simplify_record.py -x -q

Hermetic: each test builds a throwaway git repo in tmp_path and drives
begin()/finish() against it.
"""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("simplify_record.py")
SPEC = importlib.util.spec_from_file_location("simplify_record", SCRIPT)
assert SPEC and SPEC.loader
sr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def commit_file(repo: Path, relpath: str, content: str) -> str:
    p = repo / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _git(repo, "add", relpath)
    _git(repo, "commit", "-q", "-m", f"update {relpath}")
    return _git(repo, "rev-parse", "HEAD")


PASS_DELTA = {"spec_verdict": "pass", "quality_verdict": "approved"}


# ---------------------------------------------------------------------------
# begin() — positive, negative, boundary
# ---------------------------------------------------------------------------


def test_begin_resolves_base_and_pre_on_clean_worktree(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    pre = commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    assert state == {"base_sha": base, "pre_sha": pre, "claude_code_version": "2.1.220"}


def test_begin_rejects_dirty_worktree(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "seed.txt").write_text("dirty\n", encoding="utf-8")  # uncommitted
    with pytest.raises(sr.SimplifyRecordError, match="dirty worktree"):
        sr.begin(
            repo_root=repo,
            base_ref=base,
            target_ref="HEAD",
            claude_code_version="2.1.220",
        )


def test_begin_rejects_dirty_worktree_from_untracked_file(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "untracked.txt").write_text("new\n", encoding="utf-8")
    with pytest.raises(sr.SimplifyRecordError, match="dirty worktree"):
        sr.begin(
            repo_root=repo,
            base_ref=base,
            target_ref="HEAD",
            claude_code_version="2.1.220",
        )


def test_begin_rejects_unresolvable_base_ref(tmp_path):
    repo = make_repo(tmp_path)
    with pytest.raises(sr.SimplifyRecordError, match="cannot resolve ref"):
        sr.begin(
            repo_root=repo,
            base_ref="not-a-real-ref",
            target_ref="HEAD",
            claude_code_version="2.1.220",
        )


def test_begin_rejects_base_equal_to_target(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(sr.SimplifyRecordError, match="same commit"):
        sr.begin(
            repo_root=repo,
            base_ref=base,
            target_ref="HEAD",
            claude_code_version="2.1.220",
        )


def test_begin_rejects_base_not_ancestor_of_target(tmp_path):
    repo = make_repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "side")
    side_head = commit_file(repo, "side.txt", "side\n")
    _git(repo, "checkout", "-q", "main")
    main_head = commit_file(repo, "main.txt", "main\n")
    # side_head is not an ancestor of main's HEAD (they diverged from root).
    with pytest.raises(sr.SimplifyRecordError, match="not an ancestor"):
        sr.begin(
            repo_root=repo,
            base_ref=side_head,
            target_ref="HEAD",
            claude_code_version="2.1.220",
        )
    assert main_head  # keep referenced


def test_begin_rejects_missing_claude_code_version(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    with pytest.raises(sr.SimplifyRecordError, match="capability"):
        sr.begin(
            repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version=None
        )


def test_begin_rejects_old_claude_code_version(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    with pytest.raises(sr.SimplifyRecordError, match="capability"):
        sr.begin(
            repo_root=repo,
            base_ref=base,
            target_ref="HEAD",
            claude_code_version="2.1.153",
        )


def test_begin_accepts_exact_minimum_version_boundary(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.154"
    )
    assert state["claude_code_version"] == "2.1.154"


# ---------------------------------------------------------------------------
# finish() — positive, negative, mutation-style
# ---------------------------------------------------------------------------


def test_finish_records_changed_outcome_with_passing_evidence(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    post = commit_file(repo, "src/app.py", "x = 1\ny = 2\n")
    entry = sr.finish(
        repo_root=repo,
        begin_state=state,
        target_ref="HEAD",
        outcome="changed",
        changed_files=["src/app.py"],
        reason="non_tiny_source_change",
        verification_result="pass",
        delta_verdict=PASS_DELTA,
    )
    assert entry["type"] == "simplify"
    assert entry["result"] == "pass"
    assert entry["base_sha"] == state["base_sha"]
    assert entry["pre_sha"] == state["pre_sha"]
    assert entry["post_sha"] == post
    assert entry["changed_files"] == ["src/app.py"]
    # Round-trip: check_review_receipt's own independent validators agree.
    assert sr.check_review_receipt.simplify_shape_error(entry) is None
    assert sr.check_review_receipt.simplify_entry_passes(entry) is True


def test_finish_records_no_op_outcome_with_empty_evidence(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    # No further commit — /simplify made no change.
    entry = sr.finish(
        repo_root=repo,
        begin_state=state,
        target_ref="HEAD",
        outcome="no_op",
        changed_files=[],
        reason="non_tiny_source_change",
        verification_result=None,
        delta_verdict=None,
    )
    assert entry["outcome"] == "no_op"
    assert entry["result"] == "pass"
    assert entry["pre_sha"] == entry["post_sha"] == state["pre_sha"]
    assert entry["changed_files"] == []
    assert sr.check_review_receipt.simplify_shape_error(entry) is None
    assert sr.check_review_receipt.simplify_entry_passes(entry) is True


def test_finish_records_failing_verification_as_result_fail_not_a_raise(tmp_path):
    # Mutation guard: a legitimately failing changed outcome is a valid,
    # recordable state (result: "fail") — finish() must not force it to pass,
    # and must not raise either (that decision belongs to the receipt gate).
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    commit_file(repo, "src/app.py", "x = 1\ny = 2\n")
    entry = sr.finish(
        repo_root=repo,
        begin_state=state,
        target_ref="HEAD",
        outcome="changed",
        changed_files=["src/app.py"],
        reason="non_tiny_source_change",
        verification_result="fail",
        delta_verdict=PASS_DELTA,
    )
    assert entry["result"] == "fail"
    assert sr.check_review_receipt.simplify_entry_passes(entry) is False


@pytest.mark.parametrize(
    "delta_verdict",
    [
        {"spec_verdict": "fail", "quality_verdict": "approved"},
        {"spec_verdict": "cannot_verify", "quality_verdict": "approved"},
        {"spec_verdict": "pass", "quality_verdict": "needs_fixes"},
    ],
)
def test_finish_records_non_passing_delta_verdict_as_result_fail(
    tmp_path, delta_verdict
):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    commit_file(repo, "src/app.py", "x = 1\ny = 2\n")
    entry = sr.finish(
        repo_root=repo,
        begin_state=state,
        target_ref="HEAD",
        outcome="changed",
        changed_files=["src/app.py"],
        reason="non_tiny_source_change",
        verification_result="pass",
        delta_verdict=delta_verdict,
    )
    assert entry["result"] == "fail"


def test_finish_rejects_no_op_outcome_with_nonempty_changed_files(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    with pytest.raises(sr.SimplifyRecordError, match="malformed"):
        sr.finish(
            repo_root=repo,
            begin_state=state,
            target_ref="HEAD",
            outcome="no_op",
            changed_files=["src/app.py"],
            reason="non_tiny_source_change",
            verification_result=None,
            delta_verdict=None,
        )


def test_finish_rejects_changed_outcome_with_empty_changed_files(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    commit_file(repo, "src/app.py", "x = 1\ny = 2\n")
    with pytest.raises(sr.SimplifyRecordError, match="malformed"):
        sr.finish(
            repo_root=repo,
            begin_state=state,
            target_ref="HEAD",
            outcome="changed",
            changed_files=[],
            reason="non_tiny_source_change",
            verification_result="pass",
            delta_verdict=PASS_DELTA,
        )


def test_finish_rejects_changed_outcome_with_missing_verification_result(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    commit_file(repo, "src/app.py", "x = 1\ny = 2\n")
    with pytest.raises(sr.SimplifyRecordError, match="malformed"):
        sr.finish(
            repo_root=repo,
            begin_state=state,
            target_ref="HEAD",
            outcome="changed",
            changed_files=["src/app.py"],
            reason="non_tiny_source_change",
            verification_result=None,
            delta_verdict=PASS_DELTA,
        )


def test_finish_rejects_reason_outside_bounded_vocabulary(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    commit_file(repo, "src/app.py", "x = 1\ny = 2\n")
    with pytest.raises(sr.SimplifyRecordError, match="malformed"):
        sr.finish(
            repo_root=repo,
            begin_state=state,
            target_ref="HEAD",
            outcome="changed",
            changed_files=["src/app.py"],
            reason="made_up_reason",
            verification_result="pass",
            delta_verdict=PASS_DELTA,
        )


def test_finish_rejects_post_sha_not_descendant_of_pre_sha(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    # Move HEAD to an unrelated commit instead of committing on top of pre_sha.
    _git(repo, "checkout", "-q", "--orphan", "unrelated")
    (repo / "other.py").write_text("q = 1\n", encoding="utf-8")
    _git(repo, "add", "other.py")
    _git(repo, "commit", "-q", "-m", "unrelated root")
    with pytest.raises(sr.SimplifyRecordError, match="not a descendant"):
        sr.finish(
            repo_root=repo,
            begin_state=state,
            target_ref="HEAD",
            outcome="changed",
            changed_files=["other.py"],
            reason="non_tiny_source_change",
            verification_result="pass",
            delta_verdict=PASS_DELTA,
        )


def test_finish_rejects_unresolvable_target_ref(tmp_path):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")
    state = sr.begin(
        repo_root=repo, base_ref=base, target_ref="HEAD", claude_code_version="2.1.220"
    )
    with pytest.raises(sr.SimplifyRecordError, match="cannot resolve ref"):
        sr.finish(
            repo_root=repo,
            begin_state=state,
            target_ref="not-a-real-ref",
            outcome="no_op",
            changed_files=[],
            reason="non_tiny_source_change",
            verification_result=None,
            delta_verdict=None,
        )


# ---------------------------------------------------------------------------
# is_ancestor / resolve_sha — direct unit coverage (mutation guards)
# ---------------------------------------------------------------------------


def test_is_ancestor_true_for_direct_lineage(tmp_path):
    repo = make_repo(tmp_path)
    root = _git(repo, "rev-parse", "HEAD")
    tip = commit_file(repo, "a.txt", "a\n")
    assert sr.is_ancestor(repo, root, tip) is True


def test_is_ancestor_true_for_identical_commit(tmp_path):
    repo = make_repo(tmp_path)
    root = _git(repo, "rev-parse", "HEAD")
    assert sr.is_ancestor(repo, root, root) is True


def test_is_ancestor_false_for_divergent_history(tmp_path):
    repo = make_repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "side")
    side_head = commit_file(repo, "side.txt", "side\n")
    _git(repo, "checkout", "-q", "main")
    commit_file(repo, "main.txt", "main\n")
    assert sr.is_ancestor(repo, side_head, "HEAD") is False


def test_resolve_sha_returns_full_lowercase_hex(tmp_path):
    repo = make_repo(tmp_path)
    sha = sr.resolve_sha(repo, "HEAD")
    assert sr._SHA_RE.fullmatch(sha)


# ---------------------------------------------------------------------------
# CLI smoke test (begin/finish subcommands)
# ---------------------------------------------------------------------------


def test_cli_begin_then_finish_round_trip(tmp_path, capsys):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    commit_file(repo, "src/app.py", "x = 1\n")

    rc = sr.main(
        [
            "--repo-root",
            str(repo),
            "begin",
            "--base",
            base,
            "--claude-code-version",
            "2.1.220",
            "--output",
            str(tmp_path / "begin.json"),
        ]
    )
    assert rc == 0
    commit_file(repo, "src/app.py", "x = 1\ny = 2\n")

    rc = sr.main(
        [
            "--repo-root",
            str(repo),
            "finish",
            "--begin-state",
            str(tmp_path / "begin.json"),
            "--outcome",
            "changed",
            "--changed-files",
            "src/app.py",
            "--reason",
            "non_tiny_source_change",
            "--verification-result",
            "pass",
            "--delta-verdict",
            '{"spec_verdict": "pass", "quality_verdict": "approved"}',
            "--output",
            str(tmp_path / "finish.json"),
        ]
    )
    assert rc == 0

    finish_entry = json.loads((tmp_path / "finish.json").read_text(encoding="utf-8"))
    assert finish_entry["type"] == "simplify"
    assert finish_entry["result"] == "pass"


def test_cli_begin_reports_dirty_worktree_error(tmp_path, capsys):
    repo = make_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "seed.txt").write_text("dirty\n", encoding="utf-8")
    rc = sr.main(["--repo-root", str(repo), "begin", "--base", base])
    assert rc == 1
    assert "dirty worktree" in capsys.readouterr().err
