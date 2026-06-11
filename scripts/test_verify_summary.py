"""Tests for verify_summary.py.

Run:

    python -m pytest scripts/test_verify_summary.py -x -q
"""

import importlib.util
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "verify_summary", Path(__file__).resolve().parent / "verify_summary.py"
)
assert _SPEC and _SPEC.loader, "could not load verify_summary.py"
vs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(vs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SUMMARY_HEADER = """\
# test-slug — Summary

Lane: tiny
Confidence: high
Reason: test
Flags: none
Affects: none
Input-type: maintenance

## What changed

Test change.

### Verify

"""

SUMMARY_FOOTER = """
### Rollback

- `git revert abc123`
"""


def make_summary(table_rows: str) -> str:
    """Build a minimal SUMMARY.md with the given table rows."""
    header_row = "| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n"
    return SUMMARY_HEADER + header_row + table_rows + SUMMARY_FOOTER


def write_summary(tmp_path: Path, slug: str, content: str) -> Path:
    """Write a fake specs/<slug>/SUMMARY.md and return its path."""
    slug_dir = tmp_path / "specs" / slug
    slug_dir.mkdir(parents=True)
    p = slug_dir / "SUMMARY.md"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# parse_verify_table
# ---------------------------------------------------------------------------


class TestParseVerifyTable:
    def test_parses_rows(self):
        text = make_summary("| unit tests | `pytest tests/ -x` | 0 | ok |\n")
        rows = vs.parse_verify_table(text)
        assert len(rows) == 1
        assert rows[0]["check"] == "unit tests"
        assert rows[0]["command"] == "pytest tests/ -x"
        assert rows[0]["claimed_exit"] == "0"

    def test_strips_backticks_from_command(self):
        text = make_summary("| lint | `ruff check .` | 0 | |\n")
        rows = vs.parse_verify_table(text)
        assert rows[0]["command"] == "ruff check ."

    def test_placeholder_em_dash_skipped(self):
        text = make_summary("| placeholder | — | 0 | |\n")
        rows = vs.parse_verify_table(text)
        assert rows == []

    def test_placeholder_angle_bracket_skipped(self):
        text = make_summary("| placeholder | `<command>` | 0 | |\n")
        rows = vs.parse_verify_table(text)
        assert rows == []

    def test_placeholder_empty_command_skipped(self):
        text = make_summary("| placeholder |  | 0 | |\n")
        rows = vs.parse_verify_table(text)
        assert rows == []

    def test_multiple_rows(self):
        rows_text = (
            "| unit | `pytest tests/ -x` | 0 | |\n| lint | `ruff check .` | 0 | |\n"
        )
        rows = vs.parse_verify_table(make_summary(rows_text))
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# run_checks
# ---------------------------------------------------------------------------


class TestRunChecks:
    def test_passing_command_returns_zero(self):
        results = vs.run_checks(
            [{"check": "true cmd", "command": "true", "claimed_exit": "0"}],
            repo_root=Path("/tmp"),
            timeout=5,
        )
        assert results[0]["actual_exit"] == 0
        assert results[0]["timed_out"] is False

    def test_failing_command_returns_nonzero(self):
        results = vs.run_checks(
            [{"check": "false cmd", "command": "false", "claimed_exit": "0"}],
            repo_root=Path("/tmp"),
            timeout=5,
        )
        assert results[0]["actual_exit"] != 0

    def test_timeout_sets_timed_out_flag(self):
        results = vs.run_checks(
            [{"check": "slow", "command": "sleep 10", "claimed_exit": "0"}],
            repo_root=Path("/tmp"),
            timeout=1,
        )
        assert results[0]["timed_out"] is True
        assert results[0]["actual_exit"] != 0


# ---------------------------------------------------------------------------
# main — pass-and-match → exit 0 + Verified line written
# ---------------------------------------------------------------------------


class TestMainPassAndMatch:
    def test_exit_0_and_verified_line_written(self, tmp_path):
        content = make_summary("| true cmd | `true` | 0 | |\n")
        write_summary(tmp_path, "my-slug", content)
        rc = vs.main(["my-slug", "--timeout", "10"], specs_root=tmp_path / "specs")
        assert rc == 0

        updated = (tmp_path / "specs" / "my-slug" / "SUMMARY.md").read_text(
            encoding="utf-8"
        )
        assert "Verified:" in updated


# ---------------------------------------------------------------------------
# main — failing command → exit 1
# ---------------------------------------------------------------------------


class TestMainFailingCommand:
    def test_exit_1_on_failing_command(self, tmp_path):
        content = make_summary("| fail cmd | `false` | 0 | |\n")
        write_summary(tmp_path, "fail-slug", content)
        rc = vs.main(["fail-slug", "--timeout", "10"], specs_root=tmp_path / "specs")
        assert rc == 1


# ---------------------------------------------------------------------------
# main — claimed 0 but actual 1 → exit 1 + mismatch message
# ---------------------------------------------------------------------------


class TestMainMismatch:
    def test_exit_1_and_mismatch_reported(self, tmp_path, capsys):
        content = make_summary("| mismatch | `false` | 0 | |\n")
        write_summary(tmp_path, "mismatch-slug", content)
        rc = vs.main(
            ["mismatch-slug", "--timeout", "10"], specs_root=tmp_path / "specs"
        )
        assert rc == 1
        captured = capsys.readouterr()
        assert "claimed" in captured.out.lower() or "mismatch" in captured.out.lower()

    def test_mismatch_shows_claimed_and_actual(self, tmp_path, capsys):
        content = make_summary("| check | `false` | 0 | |\n")
        write_summary(tmp_path, "mismatch2-slug", content)
        vs.main(["mismatch2-slug", "--timeout", "10"], specs_root=tmp_path / "specs")
        captured = capsys.readouterr()
        # Output must mention both claimed (0) and actual (nonzero)
        assert "0" in captured.out


# ---------------------------------------------------------------------------
# main — placeholder-only table → exit 0 + "no checks ran" warning
# ---------------------------------------------------------------------------


class TestMainPlaceholderOnly:
    def test_exit_0_with_warning(self, tmp_path, capsys):
        content = make_summary("| placeholder | — | 0 | |\n")
        write_summary(tmp_path, "placeholder-slug", content)
        rc = vs.main(
            ["placeholder-slug", "--timeout", "10"], specs_root=tmp_path / "specs"
        )
        assert rc == 0
        captured = capsys.readouterr()
        assert "no checks ran" in captured.out.lower()


# ---------------------------------------------------------------------------
# main — timeout → exit 1
# ---------------------------------------------------------------------------


class TestMainTimeout:
    def test_timeout_causes_exit_1(self, tmp_path):
        # Use sleep 5 with --timeout 1 so the test finishes quickly
        content = make_summary("| slow | `sleep 5` | 0 | |\n")
        write_summary(tmp_path, "timeout-slug", content)
        rc = vs.main(["timeout-slug", "--timeout", "1"], specs_root=tmp_path / "specs")
        assert rc == 1


# ---------------------------------------------------------------------------
# main — --check mode does NOT modify file
# ---------------------------------------------------------------------------


class TestMainCheckMode:
    def test_check_mode_does_not_modify_file(self, tmp_path):
        content = make_summary("| true cmd | `true` | 0 | |\n")
        write_summary(tmp_path, "check-slug", content)
        summary_path = tmp_path / "specs" / "check-slug" / "SUMMARY.md"
        before = summary_path.read_text(encoding="utf-8")

        vs.main(
            ["check-slug", "--check", "--timeout", "10"], specs_root=tmp_path / "specs"
        )

        after = summary_path.read_text(encoding="utf-8")
        assert before == after

    def test_check_mode_still_exits_1_on_failure(self, tmp_path):
        content = make_summary("| fail | `false` | 0 | |\n")
        write_summary(tmp_path, "check-fail-slug", content)
        rc = vs.main(
            ["check-fail-slug", "--check", "--timeout", "10"],
            specs_root=tmp_path / "specs",
        )
        assert rc == 1

    def test_check_mode_exits_0_on_pass(self, tmp_path):
        content = make_summary("| pass | `true` | 0 | |\n")
        write_summary(tmp_path, "check-pass-slug", content)
        rc = vs.main(
            ["check-pass-slug", "--check", "--timeout", "10"],
            specs_root=tmp_path / "specs",
        )
        assert rc == 0


# ---------------------------------------------------------------------------
# main — bad invocation
# ---------------------------------------------------------------------------


class TestMainBadArgs:
    def test_no_args_returns_2(self):
        assert vs.main([]) == 2
