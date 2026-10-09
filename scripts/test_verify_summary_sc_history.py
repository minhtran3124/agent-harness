"""Tests for `verify_summary.py --sc-history <slug> --base <ref>` (issue #258 item 5).

Run:

    python3 -m pytest scripts/test_verify_summary_sc_history.py -q

Hermetic: every test builds a throwaway git repository under pytest's tmp_path
(a base commit on `main`, then commits on `feature`) and runs the CLI as a
subprocess with `cwd` set to that repository. No test runs git against the
repository this file lives in.

One test per row of the error-behavior table in
specs/gh-258-sc-goalpost-guard/design.md; where the default and
REQUIRE_SC_STABLE=1 exit columns differ, both are asserted.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "verify_summary.py"
SLUG = "demo"
PLAN = f"specs/{SLUG}/PLAN.md"
SUMMARY = f"specs/{SLUG}/SUMMARY.md"
DELETE = object()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def plan_text(*rows: tuple[str, str, str]) -> str:
    """A PLAN.md with a §3 SC table; rows are (id, check, expected)."""
    lines = [
        "# Plan",
        "",
        "## 3. Success Criteria",
        "",
        "| ID | Behavior | Check | Expected |",
        "|---|---|---|---|",
    ]
    lines += [f"| {sc} | behaves | {check} | {expected} |" for sc, check, expected in rows]
    return "\n".join(lines) + "\n"


def summary_text(*rows: tuple[str, str, str, str], deviations: str | None = None,
                 extra: str = "") -> str:
    """A SUMMARY.md with a Verify table; rows are (check, command, exit, criterion)."""
    lines = [
        "# Summary",
        "",
        "Lane: high-risk",
        "",
        "### Verify",
        "",
        "| Check | Command | Exit | Notes | Criterion |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {c} | `{cmd}` | {ex} | n | {crit} |" for c, cmd, ex, crit in rows]
    lines.append("")
    if deviations is not None:
        lines += ["### Deviations", "", deviations, ""]
    if extra:
        lines += [extra, ""]
    return "\n".join(lines)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(r, "add", "seed.txt")
    _git(r, "commit", "-q", "--no-verify", "-m", "base")
    _git(r, "branch", "-M", "main")
    _git(r, "checkout", "-q", "-b", "feature")
    return r


def commit(repo: Path, plan=None, summary=None, other: str | None = None) -> str:
    """Write (or DELETE) the spec files, commit, and return the commit sha."""
    for rel, content in ((PLAN, plan), (SUMMARY, summary)):
        path = repo / rel
        if content is DELETE:
            path.unlink()
        elif content is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if other is not None:
        (repo / "other.txt").write_text(other, encoding="utf-8")
    _git(repo, "add", "-A", ".")
    _git(repo, "commit", "-q", "--no-verify", "--allow-empty", "-m", "step")
    return _git(repo, "rev-parse", "HEAD")


def run(cwd: Path, *args: str, require: bool = False, env_extra: dict | None = None,
        base: str | None = "main") -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("REQUIRE_SC_STABLE", None)
    if require:
        env["REQUIRE_SC_STABLE"] = "1"
    env.update(env_extra or {})
    argv = [sys.executable, str(SCRIPT), "--sc-history", SLUG]
    if base is not None:
        argv += ["--base", base]
    return subprocess.run(
        argv + list(args), cwd=cwd, capture_output=True, text=True, env=env
    )


def both(cwd: Path, *args: str, **kw):
    return run(cwd, *args, **kw), run(cwd, *args, require=True, **kw)


def short(repo: Path, sha: str) -> str:
    return _git(repo, "rev-parse", "--short", sha)


def finding(repo: Path, sha: str, kind: str, sc: str = "SC-1") -> str:
    return (
        f"SC-GOALPOST [{sc}] {kind} after it failed at {short(repo, sha)}; "
        f"name {sc} in ### Deviations to acknowledge"
    )


PLAN0 = plan_text(("SC-1", "`pytest a`", "exit 0"))
FAILED = summary_text(("tests", "pytest a", "1", "SC-1"))
PASSED = summary_text(("tests", "pytest a", "0", "SC-1"))


def record_failure(repo: Path) -> str:
    return commit(repo, plan=PLAN0, summary=FAILED)


def assert_finding(repo, sha, kind, sc="SC-1"):
    default, required = both(repo)
    line = finding(repo, sha, kind, sc)
    assert line in default.stdout.splitlines(), default.stdout + default.stderr
    assert default.returncode == 0, default.stdout + default.stderr
    assert line in required.stdout.splitlines(), required.stdout + required.stderr
    assert required.returncode == 1, required.stdout + required.stderr


def assert_clean(repo):
    default, required = both(repo)
    for proc in (default, required):
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "SC-GOALPOST" not in proc.stdout
        assert proc.stdout.strip(), "expected a summary or skip line"
    return default


# ---------------------------------------------------------------------------
# Error-behavior table rows
# ---------------------------------------------------------------------------


def test_no_failure_record_prints_summary_line(repo):
    commit(repo, plan=PLAN0, summary=PASSED)
    assert_clean(repo)


def test_expected_changed_after_failure(repo):
    sha = record_failure(repo)
    commit(repo, plan=plan_text(("SC-1", "`pytest a`", "exit 1")))
    assert_finding(repo, sha, "changed")


def test_check_changed_after_failure(repo):
    sha = record_failure(repo)
    commit(repo, plan=plan_text(("SC-1", "`pytest b`", "exit 0")))
    assert_finding(repo, sha, "changed")


def test_first_failure_record_is_the_reference(repo):
    sha = record_failure(repo)
    # Goalpost moved while still failing, then the new check passes.
    commit(repo, plan=plan_text(("SC-1", "`pytest b`", "exit 0")))
    commit(repo, summary=summary_text(("tests", "pytest b", "0", "SC-1")))
    assert_finding(repo, sha, "changed")


def test_removed_after_failure(repo):
    sha = record_failure(repo)
    commit(repo, plan=plan_text(("SC-2", "`pytest z`", "exit 0")))
    assert_finding(repo, sha, "removed")


@pytest.mark.parametrize(
    "new_plan",
    [
        plan_text(("SC-1", "`pytest a`", "exit 1")),
        plan_text(("SC-1", "`pytest b`", "exit 0")),
        plan_text(("SC-2", "`pytest z`", "exit 0")),
    ],
    ids=["expected", "check", "removed"],
)
def test_deviations_naming_sc_suppresses_finding(repo, new_plan):
    record_failure(repo)
    commit(
        repo,
        plan=new_plan,
        summary=summary_text(
            ("tests", "pytest a", "1", "SC-1"),
            deviations="- Rule 1 — SC-1 relaxed: the original check was wrong.",
        ),
    )
    assert_clean(repo)


def test_summary_missing_at_head_does_not_suppress(repo):
    sha = record_failure(repo)
    commit(repo, plan=plan_text(("SC-1", "`pytest b`", "exit 0")), summary=DELETE)
    assert_finding(repo, sha, "changed")


def test_deviations_section_missing_at_head_does_not_suppress(repo):
    sha = record_failure(repo)
    commit(
        repo,
        plan=plan_text(("SC-1", "`pytest b`", "exit 0")),
        summary=summary_text(
            ("tests", "pytest b", "1", "SC-1"), extra="### Notes\n\nSC-1 was relaxed."
        ),
    )
    assert_finding(repo, sha, "changed")


def test_plan_missing_at_head_reports_removed(repo):
    sha = record_failure(repo)
    commit(repo, plan=DELETE)
    assert_finding(repo, sha, "removed")


@pytest.mark.parametrize("with_failure", [True, False])
def test_spec_dir_gone_at_head_is_skipped(repo, with_failure):
    if with_failure:
        record_failure(repo)
    else:
        commit(repo, plan=PLAN0, summary=PASSED)
    commit(repo, plan=DELETE, summary=DELETE)
    out = assert_clean(repo)
    assert "skip" in out.stdout


def test_changed_but_never_failed(repo):
    commit(repo, plan=PLAN0, summary=PASSED)
    commit(repo, plan=plan_text(("SC-1", "`pytest b`", "exit 1")))
    assert_clean(repo)


def test_prose_only_expected_edit_and_whitespace_check_edit(repo):
    commit(
        repo,
        plan=plan_text(("SC-1", "`pytest a`", "exit 0 — all pass")),
        summary=FAILED,
    )
    commit(repo, plan=plan_text(("SC-1", "`pytest   a`", "exit 0 — every test passes")))
    assert_clean(repo)


@pytest.mark.parametrize("later", ["still-failing", "later-passing"])
def test_failed_and_unchanged(repo, later):
    record_failure(repo)
    if later == "later-passing":
        commit(repo, summary=PASSED)
    else:
        commit(repo, summary=summary_text(("tests", "pytest a", "2", "SC-1")))
    assert_clean(repo)


def test_malformed_sc_row_produces_no_record(repo):
    # At this commit SC-1's Expected is malformed (`ERROR:` from parse_sc_table),
    # so the failing row records nothing.
    commit(repo, plan=plan_text(("SC-1", "`pytest a`", "passes")), summary=FAILED)
    commit(repo, plan=PLAN0, summary=PASSED)
    commit(repo, plan=plan_text(("SC-1", "`pytest b`", "exit 0")))
    assert_clean(repo)


@pytest.mark.parametrize("exit_cell", ["", "pending", "<exit>", "n/a"])
def test_non_integer_exit_is_ignored(repo, exit_cell):
    commit(repo, plan=PLAN0, summary=summary_text(("tests", "pytest a", exit_cell, "SC-1")))
    commit(repo, plan=plan_text(("SC-1", "`pytest b`", "exit 0")))
    assert_clean(repo)


def test_exit_124_counts_as_failure_record(repo):
    sha = commit(repo, plan=PLAN0, summary=summary_text(("tests", "pytest a", "124", "SC-1")))
    commit(repo, plan=plan_text(("SC-1", "`pytest b`", "exit 0")))
    assert_finding(repo, sha, "changed")


def test_no_spec_files_in_any_commit(repo):
    commit(repo, other="unrelated\n")
    out = assert_clean(repo)
    assert "skip" not in out.stdout


def test_sc1_not_matched_inside_sc12(repo):
    plan = plan_text(("SC-1", "`pytest a`", "exit 0"), ("SC-12", "`pytest c`", "exit 0"))
    sha = commit(
        repo,
        plan=plan,
        summary=summary_text(("a", "pytest a", "1", "SC-1"), ("c", "pytest c", "0", "SC-12")),
    )
    commit(
        repo,
        plan=plan_text(("SC-1", "`pytest b`", "exit 0"), ("SC-12", "`pytest c`", "exit 0")),
        summary=summary_text(
            ("a", "pytest a", "1", "SC-1"),
            ("c", "pytest c", "0", "SC-12"),
            deviations="- SC-12 wording tidied.",
        ),
    )
    assert_finding(repo, sha, "changed")


# ---------------------------------------------------------------------------
# Usage errors: exit 2 in both modes
# ---------------------------------------------------------------------------


def assert_usage(proc_pair):
    for proc in proc_pair:
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "SC-GOALPOST" not in proc.stdout


def test_usage_base_missing(repo):
    assert_usage(both(repo, base=None))


@pytest.mark.parametrize(
    "extra",
    [["--check"], ["--lane"], ["--plan-dir", "x"], ["--timeout", "5"], ["demo2"]],
    ids=["check", "lane", "plan-dir", "timeout", "positional"],
)
def test_usage_combined_with_other_mode(repo, extra):
    record_failure(repo)
    assert_usage(both(repo, *extra))


def test_usage_ref_does_not_resolve(repo):
    record_failure(repo)
    assert_usage(both(repo, base="no-such-ref"))


def test_usage_no_merge_base(repo):
    record_failure(repo)
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    orphan = _git(repo, "commit-tree", tree, "-m", "unrelated root")
    assert_usage(both(repo, base=orphan))


def test_usage_not_a_git_repository(tmp_path):
    outside = tmp_path / "nogit"
    outside.mkdir()
    assert_usage(both(outside, env_extra={"GIT_CEILING_DIRECTORIES": str(tmp_path)}))


def test_usage_git_cannot_run(repo, tmp_path):
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    assert_usage(both(repo, env_extra={"PATH": str(empty_bin)}))


def test_base_without_sc_history_is_a_usage_error(repo):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "demo", "--base", "main"],
        cwd=repo, capture_output=True, text=True,
    )
    assert proc.returncode == 2
