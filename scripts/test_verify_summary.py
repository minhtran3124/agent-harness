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
            [{"check": "true cmd", "command": "test 1 = 1", "claimed_exit": "0"}],
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
        content = make_summary("| true cmd | `test 1 = 1` | 0 | |\n")
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
        content = make_summary("| true cmd | `test 1 = 1` | 0 | |\n")
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
        content = make_summary("| pass | `test 1 = 1` | 0 | |\n")
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


# ---------------------------------------------------------------------------
# Phase 3 (verify-substance): trivial denylist, negative proof, stamp semantics
# ---------------------------------------------------------------------------


class TestTrivialDenylist:
    def _rc(self, tmp_path, command, claimed="0"):
        content = make_summary(f"| c | `{command}` | {claimed} | |\n")
        write_summary(tmp_path, "triv-slug", content)
        return vs.main(
            ["triv-slug", "--check", "--timeout", "10"], specs_root=tmp_path / "specs"
        )

    def test_true_is_rejected(self, tmp_path):
        assert self._rc(tmp_path, "true") == 1

    def test_colon_is_rejected(self, tmp_path):
        assert self._rc(tmp_path, ":") == 1

    def test_exit_0_is_rejected(self, tmp_path):
        assert self._rc(tmp_path, "exit 0") == 1

    def test_bare_echo_is_rejected(self, tmp_path):
        assert self._rc(tmp_path, "echo all good here") == 1

    def test_echo_chained_into_real_check_is_not_trivial(self, tmp_path):
        # echo COMBINED with a real assertion is not a no-op — must run and pass.
        # (A literal `|` can't sit unescaped in a markdown table cell, so the
        # pipe variant is exercised at the regex level in test_trivial_regex_shapes.)
        assert self._rc(tmp_path, "echo x && test 1 = 1") == 0

    def test_trivial_regex_shapes(self):
        assert vs._TRIVIAL_RE.match("echo anything at all")
        assert not vs._TRIVIAL_RE.match("echo x | grep -q x")
        assert not vs._TRIVIAL_RE.match("echo $(run-something)")
        assert not vs._TRIVIAL_RE.match("bash scripts/run-tests.sh")

    def test_trivial_row_is_not_executed(self):
        results = vs.run_checks(
            [{"check": "t", "command": "true", "claimed_exit": "0", "notes": ""}],
            repo_root=Path("."),
        )
        assert results[0].get("trivial") is True
        assert results[0]["actual_exit"] is None


class TestNegativeProof:
    def test_claimed_nonzero_matching_actual_passes(self, tmp_path):
        # "this command must fail" is a legitimate, pinnable check
        content = make_summary("| must-fail | `test 1 = 2` | 1 | |\n")
        write_summary(tmp_path, "neg-slug", content)
        rc = vs.main(
            ["neg-slug", "--check", "--timeout", "10"], specs_root=tmp_path / "specs"
        )
        assert rc == 0

    def test_claimed_zero_actual_nonzero_mismatches(self, tmp_path):
        content = make_summary("| lie | `test 1 = 2` | 0 | |\n")
        write_summary(tmp_path, "lie-slug", content)
        rc = vs.main(
            ["lie-slug", "--check", "--timeout", "10"], specs_root=tmp_path / "specs"
        )
        assert rc == 1


class TestStampSemantics:
    def test_no_verified_stamp_on_failure(self, tmp_path):
        content = make_summary("| bad | `test 1 = 2` | 0 | |\n")
        p = write_summary(tmp_path, "stamp-slug", content)
        rc = vs.main(["stamp-slug", "--timeout", "10"], specs_root=tmp_path / "specs")
        assert rc == 1
        assert "Verified:" not in p.read_text()

    def test_stale_verified_stamp_dropped_on_failure(self, tmp_path):
        content = make_summary("| bad | `test 1 = 2` | 0 | |\n").replace(
            "\n### Rollback", "Verified: 2026-01-01T00:00:00\n\n### Rollback"
        )
        p = write_summary(tmp_path, "stale-slug", content)
        assert "Verified:" in p.read_text()  # precondition
        vs.main(["stale-slug", "--timeout", "10"], specs_root=tmp_path / "specs")
        assert "Verified:" not in p.read_text()

    def test_duplicate_check_names_rewrite_by_row_order(self, tmp_path):
        # two rows named "dup": first passes (exit 0), second fails (exit 1) —
        # the old name-keyed map collided; row order must keep them distinct
        rows = "| dup | `test 1 = 1` | 0 | |\n| dup | `test 1 = 2` | 1 | |\n"
        content = make_summary(rows)
        p = write_summary(tmp_path, "dup-slug", content)
        rc = vs.main(["dup-slug", "--timeout", "10"], specs_root=tmp_path / "specs")
        assert rc == 0  # both claims match reality (negative proof on row 2)
        text = p.read_text()
        table_lines = [ln for ln in text.splitlines() if ln.startswith("| dup")]
        assert "| 0 |" in table_lines[0].replace(" ", " ")
        assert "| 1 |" in table_lines[1].replace(" ", " ")


class TestPlaceholderSet:
    def test_hyphen_and_endash_rows_are_placeholders(self):
        rows = vs.parse_verify_table(
            make_summary("| a | - | 0 | |\n| b | – | 0 | |\n| c | — | 0 | |\n")
        )
        assert rows == []


class TestRewriteQueueAlignment:
    def test_bracketed_placeholder_between_real_rows_keeps_queue_aligned(
        self, tmp_path
    ):
        # Regression (review MEDIUM): a `<...>`-prefixed placeholder row is skipped
        # by the parser but was NOT skipped by the rewriter — every exit after it
        # shifted one row up, writing a fabricated exit onto the placeholder and
        # leaving the last real row unverified.
        rows = (
            "| a | `test 1 = 1` | 0 | |\n"
            "| b | `<todo fill later>` | 9 | |\n"
            "| c | `test 1 = 2` | 1 | |\n"
        )
        content = make_summary(rows)
        p = write_summary(tmp_path, "align-slug", content)
        rc = vs.main(["align-slug", "--timeout", "10"], specs_root=tmp_path / "specs")
        assert rc == 0  # a passes, b skipped, c is a matching negative proof
        text = p.read_text()
        line_a = next(ln for ln in text.splitlines() if ln.startswith("| a"))
        line_b = next(ln for ln in text.splitlines() if ln.startswith("| b"))
        line_c = next(ln for ln in text.splitlines() if ln.startswith("| c"))
        assert "| 0 |" in line_a
        assert "| 9 |" in line_b  # placeholder row untouched — no fabricated exit
        assert "| 1 |" in line_c  # real row got ITS OWN actual exit


# ---------------------------------------------------------------------------
# --lane mode
# ---------------------------------------------------------------------------


def _lane_summary(
    lane="tiny",
    confidence="high",
    reason="obvious one-file edit",
    verify=None,
    rollback=None,
):
    parts = [
        "# demo — Summary",
        "",
        f"Lane: {lane}",
        f"Confidence: {confidence}",
        f"Reason: {reason}",
        "Flags: none",
        "",
        "## What changed",
        "Did the thing.",
    ]
    if verify is not None:
        parts += [
            "",
            "### Verify",
            "",
            "| Check | Command | Exit | Notes |",
            "| --- | --- | --- | --- |",
            verify,
        ]
    if rollback is not None:
        parts += ["", "### Rollback", "", rollback]
    return "\n".join(parts) + "\n"


REAL_LANE_VERIFY = "| unit | `pytest -q` | 0 | all pass |"
PLACEHOLDER_LANE_VERIFY = "| <unit / lint> | `<command>` | 0 | <excerpt> |"


class TestLaneEvidence:
    def test_tiny_header_only_passes(self):
        assert vs.check_lane_evidence(_lane_summary(lane="tiny")) == []

    def test_missing_and_placeholder_headers_fail(self):
        missing = _lane_summary(lane="tiny").replace("Confidence: high\n", "")
        assert any("Confidence" in e for e in vs.check_lane_evidence(missing))

        placeholder = _lane_summary(reason="<one sentence — why this lane>")
        errors = vs.check_lane_evidence(placeholder)
        assert any("Reason" in e and "placeholder" in e for e in errors)

    def test_normal_requires_a_real_verify_row(self):
        assert (
            vs.check_lane_evidence(
                _lane_summary(lane="normal", verify=REAL_LANE_VERIFY)
            )
            == []
        )
        assert any(
            "Verify" in e for e in vs.check_lane_evidence(_lane_summary(lane="normal"))
        )
        assert any(
            "no real command row" in e
            for e in vs.check_lane_evidence(
                _lane_summary(lane="normal", verify=PLACEHOLDER_LANE_VERIFY)
            )
        )

    def test_high_risk_requires_a_real_rollback(self):
        complete = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            rollback="- `alembic downgrade -1`",
        )
        assert vs.check_lane_evidence(complete) == []

        missing = _lane_summary(lane="high-risk", verify=REAL_LANE_VERIFY)
        assert any("Rollback" in e for e in vs.check_lane_evidence(missing))

        comment_only = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            rollback="<!-- only a comment -->",
        )
        assert any(
            "Rollback" in e and "empty" in e
            for e in vs.check_lane_evidence(comment_only)
        )

    def test_unresolvable_lane_values_fail(self):
        for raw_lane in ("maybe", "not-normal", "tiny | normal | high-risk"):
            text = _lane_summary().replace("Lane: tiny", f"Lane: {raw_lane}")
            errors = vs.check_lane_evidence(text)
            assert errors and "cannot resolve" in errors[0]

    def test_decorated_and_bold_lane_values_resolve(self):
        decorated = _lane_summary(
            lane="high-risk (hard gate: hooks/*)",
            verify=REAL_LANE_VERIFY,
            rollback="- Revert the PR: `git revert abc1234`",
        )
        assert vs.check_lane_evidence(decorated) == []

        bold = _lane_summary(lane="normal", verify=REAL_LANE_VERIFY)
        bold = (
            bold.replace("Lane: normal", "**Lane:** normal")
            .replace("Confidence: high", "**Confidence:** high")
            .replace("Reason: ", "**Reason:** ")
        )
        assert vs.check_lane_evidence(bold) == []

    def test_reason_with_piped_regex_is_not_a_placeholder(self):
        reason = "Risk raised because `(^|/)hooks/` matches the new test paths"
        assert vs.check_lane_evidence(_lane_summary(reason=reason)) == []

    def test_template_only_rollback_is_rejected(self):
        template_only = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            rollback="- `git revert <sha>`",
        )
        errors = vs.check_lane_evidence(template_only)
        assert errors and "Rollback" in errors[0] and "template" in errors[0]

        with_real_step = template_only.replace(
            "- `git revert <sha>`",
            "- `git revert <sha>`\n- Redeploy: `bash scripts/deploy-harness.sh`",
        )
        assert vs.check_lane_evidence(with_real_step) == []


class TestLaneMode:
    def test_slug_and_direct_path_targets_pass(self, tmp_path):
        path = write_summary(tmp_path, "lane-slug", _lane_summary())
        specs_root = tmp_path / "specs"
        assert vs.main(["--lane", "lane-slug"], specs_root=specs_root) == 0
        assert vs.main(["--lane", str(path)], specs_root=specs_root) == 0

    def test_multiple_targets_fail_if_any_target_fails(self, tmp_path):
        good = write_summary(tmp_path, "good", _lane_summary())
        bad = write_summary(tmp_path, "bad", _lane_summary(lane="normal"))
        assert vs.main(["--lane", str(good), str(bad)]) == 1

    def test_lane_mode_never_executes_verify_commands(self, tmp_path):
        marker = tmp_path / "must-not-exist"
        command = f"touch {marker}"
        write_summary(
            tmp_path,
            "structural-only",
            _lane_summary(lane="normal", verify=f"| proof | `{command}` | 0 | |"),
        )
        assert (
            vs.main(["--lane", "structural-only"], specs_root=tmp_path / "specs") == 0
        )
        assert not marker.exists()

    def test_lane_with_check_is_bad_invocation(self, tmp_path):
        write_summary(tmp_path, "lane-slug", _lane_summary())
        assert (
            vs.main(["--lane", "--check", "lane-slug"], specs_root=tmp_path / "specs")
            == 2
        )
