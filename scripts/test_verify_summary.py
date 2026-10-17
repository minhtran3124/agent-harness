"""Tests for verify_summary.py.

Run:

    python -m pytest scripts/test_verify_summary.py -x -q
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest


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


def write_plan(summary_path: Path, content: str) -> Path:
    """Write a sibling PLAN.md next to a SUMMARY.md and return its path."""
    p = summary_path.parent / "PLAN.md"
    p.write_text(content, encoding="utf-8")
    return p


class TestRuntimeMetadata:
    def test_legacy_absence_and_valid_durable_pair_are_accepted(self, tmp_path):
        path = write_summary(tmp_path, "legacy", make_summary(""))
        assert vs._check_runtime_metadata(path.read_text(), path) == []
        text = path.read_text().replace(
            "Input-type: maintenance",
            "Input-type: maintenance\nRuntime-mode: advisory\n"
            "Runtime-evidence-id: codex-mode-0123456789abcdef",
        )
        assert vs._check_runtime_metadata(text, path) == []

    def test_partial_or_malformed_pair_is_rejected(self):
        partial = SUMMARY_HEADER + "Runtime-mode: enforced\n"
        assert "supplied together" in vs._check_runtime_metadata(partial, None)[0]
        malformed = (
            SUMMARY_HEADER
            + "Runtime-mode: enforced\nRuntime-evidence-id: private-path\n"
        )
        assert (
            "invalid Runtime-evidence-id"
            in vs._check_runtime_metadata(malformed, None)[0]
        )

    def test_check_is_format_only_and_never_reads_local_state(self, tmp_path):
        # Deliberate traceability boundary: the local record is gitignored and
        # agent-writable, so the gate must not pretend to corroborate it — a
        # well-formed pair passes even when a contradicting record exists.
        path = write_summary(tmp_path, "local", make_summary(""))
        text = path.read_text().replace(
            "Input-type: maintenance",
            "Input-type: maintenance\nRuntime-mode: enforced\n"
            "Runtime-evidence-id: codex-mode-0123456789abcdef",
        )
        state = tmp_path / ".harness-state/codex-runtime.json"
        state.parent.mkdir()
        state.write_text('{"mode": "advisory"}')
        assert vs._check_runtime_metadata(text, path) == []
        state.write_text("not json")
        assert vs._check_runtime_metadata(text, path) == []


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
    not_verified=None,
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
    if not_verified is not None:
        parts += ["", "### Not auto-verified", "", not_verified]
    if rollback is not None:
        parts += ["", "### Rollback", "", rollback]
    return "\n".join(parts) + "\n"


# A filled-in `### Not auto-verified` body, for high-risk fixtures whose subject is
# some OTHER evidence requirement (rollback, lane parsing) and which must not trip
# the negative-scope check as a side effect.
REAL_NOT_VERIFIED = "- Emitted JSON shape is unasserted — reached traceability only."


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

    def test_normal_accepts_supported_verify_heading_levels(self):
        canonical = _lane_summary(lane="normal", verify=REAL_LANE_VERIFY)
        for heading in ("# Verify", "## Verify"):
            text = canonical.replace("### Verify", heading)
            assert vs.check_lane_evidence(text) == []

    def test_high_risk_requires_a_real_rollback(self):
        complete = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            rollback="- `alembic downgrade -1`",
            not_verified=REAL_NOT_VERIFIED,
        )
        assert vs.check_lane_evidence(complete) == []

        missing = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            not_verified=REAL_NOT_VERIFIED,
        )
        assert any("Rollback" in e for e in vs.check_lane_evidence(missing))

        comment_only = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            rollback="<!-- only a comment -->",
            not_verified=REAL_NOT_VERIFIED,
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
            not_verified=REAL_NOT_VERIFIED,
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

    def test_missing_not_auto_verified_warns_but_does_not_block_by_default(
        self, monkeypatch
    ):
        """WARN-FIRST rollout: advisory only until REQUIRE_NOT_AUTO_VERIFIED=1.

        52 of 53 pre-existing high-risk specs predate the section, so the default
        must not tax a typo fix to a legacy spec.
        """
        monkeypatch.delenv("REQUIRE_NOT_AUTO_VERIFIED", raising=False)
        missing = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            rollback="- `alembic downgrade -1`",
        )
        assert vs.check_lane_evidence(missing) == []
        assert any(
            "Not auto-verified" in w and var == "REQUIRE_NOT_AUTO_VERIFIED"
            for w, var in vs.check_lane_warnings(missing)
        )

    def test_missing_not_auto_verified_blocks_when_opted_in(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_NOT_AUTO_VERIFIED", "1")
        missing = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            rollback="- `alembic downgrade -1`",
        )
        assert any(
            "Not auto-verified" in e and "missing" in e
            for e in vs.check_lane_evidence(missing)
        )
        # Never reported twice: once it is an error it must not also be a warning.
        assert vs.check_lane_warnings(missing) == []

    def test_satisfied_section_produces_neither_error_nor_warning(self, monkeypatch):
        for value in ("1", ""):
            if value:
                monkeypatch.setenv("REQUIRE_NOT_AUTO_VERIFIED", value)
            else:
                monkeypatch.delenv("REQUIRE_NOT_AUTO_VERIFIED", raising=False)
            complete = _lane_summary(
                lane="high-risk",
                verify=REAL_LANE_VERIFY,
                rollback="- `alembic downgrade -1`",
                not_verified=REAL_NOT_VERIFIED,
            )
            assert vs.check_lane_evidence(complete) == []
            assert vs.check_lane_warnings(complete) == []

    def test_comment_only_and_template_bullet_are_not_real_answers(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_NOT_AUTO_VERIFIED", "1")
        for body, word in (
            ("<!-- only a comment -->", "empty"),
            (
                "- <claim> — reached <traceability | provenance>; "
                "not re-run because <reason>",
                "template",
            ),
        ):
            text = _lane_summary(
                lane="high-risk",
                verify=REAL_LANE_VERIFY,
                rollback="- `alembic downgrade -1`",
                not_verified=body,
            )
            errors = vs.check_lane_evidence(text)
            assert any("Not auto-verified" in e and word in e for e in errors), body

    def test_explicit_none_is_accepted(self):
        """`- none` is a legitimate answer: every claim is covered by a Verify row.

        This is the gate's deliberate loophole, documented rather than closed --
        it enforces that the question was ANSWERED, not that the answer is true.
        """
        none_answer = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            rollback="- `alembic downgrade -1`",
            not_verified="- none",
        )
        assert vs.check_lane_evidence(none_answer) == []

    def test_lower_lanes_do_not_require_the_section(self):
        """tiny/normal are unaffected -- this keeps the 80-spec back catalogue valid."""
        assert vs.check_lane_evidence(_lane_summary(lane="tiny")) == []
        assert (
            vs.check_lane_evidence(
                _lane_summary(lane="normal", verify=REAL_LANE_VERIFY)
            )
            == []
        )

    def test_template_only_rollback_is_rejected(self):
        template_only = _lane_summary(
            lane="high-risk",
            verify=REAL_LANE_VERIFY,
            rollback="- `git revert <sha>`",
            not_verified=REAL_NOT_VERIFIED,
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


# ---------------------------------------------------------------------------
# SC-table parsing + coverage enforcement
# ---------------------------------------------------------------------------


SC_PLAN_ONE = """\
# demo — plan

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
| --- | --- | --- | --- |
| SC-1 | first behavior | `test 1 = 1` | exit 0 |
"""

SC_PLAN_TWO = """\
# demo — plan

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
| --- | --- | --- | --- |
| SC-1 | first behavior | `test 1 = 1` | exit 0 |
| SC-2 | second behavior | `test 1 = 2` | exit 1 |
"""


class TestParseScTable:
    def test_maps_id_to_expected_exit(self):
        table = vs.parse_sc_table(SC_PLAN_TWO)
        assert table == {"SC-1": "0", "SC-2": "1"}

    def test_fenced_table_is_ignored(self):
        fenced = (
            "# demo\n\n## 3. Success Criteria\n\n"
            "```\n"
            "| ID | Behavior | Check | Expected |\n"
            "| --- | --- | --- | --- |\n"
            "| SC-1 | example | `x` | exit 0 |\n"
            "```\n"
        )
        assert vs.parse_sc_table(fenced) == {}

    def test_bad_expected_grammar_is_error(self):
        plan = SC_PLAN_ONE.replace("| exit 0 |", "| zero |")
        table = vs.parse_sc_table(plan)
        assert table["SC-1"].startswith("ERROR")


class TestScCoverage:
    def _write(self, tmp_path, slug, verify, plan):
        text = _lane_summary(lane="normal", verify=verify)
        path = write_summary(tmp_path, slug, text)
        write_plan(path, plan)
        return text, path

    def test_sc_coverage_complete_passes_lane(self, tmp_path):
        verify = (
            "| c1 | `test 1 = 1` | 0 | ok | SC-1 |\n"
            "| c2 | `test 1 = 2` | 1 | ok | SC-2 |"
        )
        text, path = self._write(tmp_path, "cov-ok", verify, SC_PLAN_TWO)
        assert vs.check_lane_evidence(text, summary_path=path) == []

    def test_sc_coverage_missing_fails_lane(self, tmp_path):
        verify = "| c1 | `test 1 = 1` | 0 | ok | SC-1 |"
        text, path = self._write(tmp_path, "cov-miss", verify, SC_PLAN_TWO)
        errors = vs.check_lane_evidence(text, summary_path=path)
        assert any("SC-2" in e for e in errors)

    def test_sc_coverage_wrong_claimed_exit_fails_lane(self, tmp_path):
        # SC-2 expects exit 1, but the covering row claims exit 0 → not covered.
        verify = (
            "| c1 | `test 1 = 1` | 0 | | SC-1 |\n| c2 | `test 1 = 2` | 0 | | SC-2 |"
        )
        text, path = self._write(tmp_path, "cov-wrong", verify, SC_PLAN_TWO)
        errors = vs.check_lane_evidence(text, summary_path=path)
        assert any("SC-2" in e for e in errors)

    def test_sc_unknown_criterion_fails(self, tmp_path):
        verify = (
            "| c1 | `test 1 = 1` | 0 | | SC-1 |\n| c2 | `test 1 = 2` | 1 | | SC-9 |"
        )
        text, path = self._write(tmp_path, "cov-unknown", verify, SC_PLAN_TWO)
        errors = vs.check_lane_evidence(text, summary_path=path)
        assert any("SC-9" in e and "unknown" in e.lower() for e in errors)

    def test_sc_duplicate_id_fails(self, tmp_path):
        dup_plan = SC_PLAN_ONE + "| SC-1 | dup behavior | `test 1 = 1` | exit 0 |\n"
        assert vs.parse_sc_table(dup_plan)["SC-1"].startswith("ERROR")
        verify = "| c1 | `test 1 = 1` | 0 | | SC-1 |"
        text, path = self._write(tmp_path, "cov-dup", verify, dup_plan)
        errors = vs.check_lane_evidence(text, summary_path=path)
        assert any("duplicate" in e.lower() for e in errors)

    def test_backward_compat_4col_no_plan(self, tmp_path):
        text = _lane_summary(lane="normal", verify=REAL_LANE_VERIFY)
        path = write_summary(tmp_path, "bc-4col", text)
        # No sibling PLAN.md written — fail-open, no new checks.
        assert vs.check_lane_evidence(text, summary_path=path) == []

    def test_backward_compat_plan_without_sc_table(self, tmp_path):
        text = _lane_summary(lane="normal", verify=REAL_LANE_VERIFY)
        path = write_summary(tmp_path, "bc-nosc", text)
        write_plan(path, "# demo\n\n## 1. Motivation\n\nNo SC table here.\n")
        assert vs.check_lane_evidence(text, summary_path=path) == []

    def test_plan_dir_override_enforces_sc_coverage(self, tmp_path):
        # Reproduces the commit-gate scenario: the SUMMARY content is read from a
        # detached copy (mktemp) whose parent has NO sibling PLAN.md. Without the
        # plan_dir override SC coverage silently fail-opens; with it, the real spec
        # dir's PLAN.md is consulted and the missing SC-2 is caught.
        verify = "| c1 | `test 1 = 1` | 0 | ok | SC-1 |"
        text, real_path = self._write(tmp_path, "cov-plandir", verify, SC_PLAN_TWO)

        detached = tmp_path / "mktemp-copy"  # a path whose parent has no PLAN.md
        detached.write_text(text, encoding="utf-8")

        # Bug reproduction: parent has no PLAN.md → fail-open (no SC error).
        assert vs.check_lane_evidence(text, summary_path=detached) == []
        # Override: SC coverage is enforced against the real spec dir's PLAN.md.
        errors = vs.check_lane_evidence(
            text, summary_path=detached, plan_dir=real_path.parent
        )
        assert any("SC-2" in e for e in errors)

    def test_plan_dir_override_via_lane_cli(self, tmp_path):
        # The --lane CLI path threads --plan-dir through to SC coverage.
        verify = "| c1 | `test 1 = 1` | 0 | ok | SC-1 |"
        _text, real_path = self._write(tmp_path, "cli-plandir", verify, SC_PLAN_TWO)
        detached = tmp_path / "mktemp-copy2"
        detached.write_text(_text, encoding="utf-8")
        # Without --plan-dir: fail-open → exit 0.
        assert vs.main(["--lane", str(detached)], specs_root=tmp_path / "specs") == 0
        # With --plan-dir pointing at the real spec dir: SC-2 uncovered → exit 1.
        assert (
            vs.main(
                ["--lane", str(detached), "--plan-dir", str(real_path.parent)],
                specs_root=tmp_path / "specs",
            )
            == 1
        )

    def test_plan_dir_override_via_check_mode(self, tmp_path):
        # --plan-dir must also be honored in single-target/check mode, not only --lane.
        # SUMMARY slug dir has NO PLAN.md, so the parent-based lookup fail-opens; the
        # real SC table lives in a separate dir pointed at by --plan-dir. The row's
        # Criterion (SC-2, expected exit 1) with a command that exits 0 is caught ONLY
        # when plan_dir is consulted.
        verify = "| c1 | `test 1 = 1` | 0 | | SC-2 |"
        text = _lane_summary(lane="normal", verify=verify)
        write_summary(tmp_path, "chk-plandir", text)  # no sibling PLAN.md written
        real = tmp_path / "real-spec"
        real.mkdir()
        (real / "PLAN.md").write_text(SC_PLAN_TWO, encoding="utf-8")
        specs_root = tmp_path / "specs"
        # Without --plan-dir: no sibling PLAN → sc_map empty → claimed==actual → exit 0.
        assert (
            vs.main(
                ["chk-plandir", "--check", "--timeout", "10"], specs_root=specs_root
            )
            == 0
        )
        # With --plan-dir: SC-2 expects exit 1 but the command exits 0 → mismatch → exit 1.
        assert (
            vs.main(
                ["chk-plandir", "--check", "--plan-dir", str(real), "--timeout", "10"],
                specs_root=specs_root,
            )
            == 1
        )

    def test_sc_coverage_missing_fails_check_mode(self, tmp_path):
        # PR #157 review (P1): `--check <slug>` is the documented ship gate and what
        # ci-strict-gate.sh runs, but it only validated Criterion-mapped rows — a PLAN
        # with SC-1 and SC-2 whose SUMMARY proved only SC-1 exited 0.
        verify = "| c1 | `test 1 = 1` | 0 | | SC-1 |"
        text = _lane_summary(lane="normal", verify=verify)
        path = write_summary(tmp_path, "chk-cov", text)
        write_plan(path, SC_PLAN_TWO)
        assert (
            vs.main(
                ["chk-cov", "--check", "--timeout", "10"], specs_root=tmp_path / "specs"
            )
            == 1
        )

    def test_sc_coverage_missing_fails_check_mode_with_no_real_rows(self, tmp_path):
        # Same gate, placeholder-only Verify table: the early "no checks ran" return
        # must not short-circuit past SC coverage.
        text = _lane_summary(lane="normal", verify="| p | `<command>` | 0 | | |")
        path = write_summary(tmp_path, "chk-cov-empty", text)
        write_plan(path, SC_PLAN_TWO)
        assert (
            vs.main(
                ["chk-cov-empty", "--check", "--timeout", "10"],
                specs_root=tmp_path / "specs",
            )
            == 1
        )

    def test_criterion_check_mode_actual_exit(self, tmp_path):
        # Well-formed: each criterion row actually exits its SC's expected code.
        verify = (
            "| c1 | `test 1 = 1` | 0 | | SC-1 |\n| c2 | `test 1 = 2` | 1 | | SC-2 |"
        )
        text = _lane_summary(lane="normal", verify=verify)
        write_summary(tmp_path, "cm-ok", text)
        write_plan((tmp_path / "specs" / "cm-ok" / "SUMMARY.md"), SC_PLAN_TWO)
        assert (
            vs.main(
                ["cm-ok", "--check", "--timeout", "10"], specs_root=tmp_path / "specs"
            )
            == 0
        )

        # Row's claimed exit matches its actual exit, so the claimed-vs-actual
        # check passes — but the criterion points at SC-2 (expected exit 1) while
        # the command actually exits 0. Only the SC comparison catches this.
        verify_bad = "| c1 | `test 1 = 1` | 0 | | SC-2 |"
        text_bad = _lane_summary(lane="normal", verify=verify_bad)
        write_summary(tmp_path, "cm-bad", text_bad)
        write_plan((tmp_path / "specs" / "cm-bad" / "SUMMARY.md"), SC_PLAN_TWO)
        assert (
            vs.main(
                ["cm-bad", "--check", "--timeout", "10"], specs_root=tmp_path / "specs"
            )
            == 1
        )

    def test_rewrite_table_preserves_criterion_column(self, tmp_path):
        verify = "| c1 | `test 1 = 1` | 0 | note | SC-1 |"
        text = _lane_summary(lane="normal", verify=verify)
        path = write_summary(tmp_path, "rw-slug", text)
        write_plan(path, SC_PLAN_ONE)
        rc = vs.main(["rw-slug", "--timeout", "10"], specs_root=tmp_path / "specs")
        assert rc == 0
        out = path.read_text(encoding="utf-8")
        line = next(ln for ln in out.splitlines() if ln.startswith("| c1"))
        assert "SC-1" in line  # trailing Criterion column preserved
        assert "| 0 |" in line  # actual exit written back
        assert "Verified:" in out


# ---------------------------------------------------------------------------
# Red/green check for bug-fix runs (Input-type: bug fix)
# ---------------------------------------------------------------------------

_RED_TEST = "pytest -q tests/test_bug.py"
_RED_ROW = (
    f"| red | `python3 scripts/run_at_commit.py abc1234 -- {_RED_TEST}` | 1 | fails |"
)
_GREEN_ROW = f"| green | `{_RED_TEST}` | 0 | passes |"


def _bug_fix_summary(verify: str, input_type: str = "bug fix") -> str:
    """A normal-lane SUMMARY with the given Input-type and Verify body."""
    return _lane_summary(lane="normal", verify=verify).replace(
        "Flags: none", f"Flags: none\nInput-type: {input_type}"
    )


def _red_green_messages(text: str) -> list[str]:
    """Every red/green message from both lane functions."""
    warnings = [message for message, _ in vs.check_lane_warnings(text)]
    return [
        m
        for m in vs.check_lane_evidence(text) + warnings
        if "red/green" in m or m.startswith("bug fix:")
    ]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


# A base commit holds the source file; the red commit adds only its test (D10: the red
# test files are the paths the red commit changed).
_FIX_SRC = "scripts/x.py"
_FIX_TEST = "scripts/test_x.py"
_FIX_TEST_CMD = f"python3 -m pytest -q {_FIX_TEST}::test_y"


@pytest.fixture
def fix_repo(tmp_path, monkeypatch):
    """A throwaway git repo whose HEAD is the red commit; cwd is set to its root."""
    monkeypatch.delenv("REQUIRE_RED_TEST", raising=False)
    monkeypatch.delenv("REQUIRE_NOT_AUTO_VERIFIED", raising=False)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / _FIX_SRC).write_text("def f():\n    return 1\n")
    _git(root, "add", "--", _FIX_SRC)
    _git(root, "commit", "-q", "-m", "base")
    (root / _FIX_TEST).write_text("def test_y():\n    assert False\n")
    _git(root, "add", "--", _FIX_TEST)
    _git(root, "commit", "-q", "-m", "red")
    monkeypatch.chdir(root)
    return root


def _red_sha(repo: Path) -> str:
    return _git(repo, "rev-parse", "--short=12", "HEAD")


def _fix_summary(sha: str, test: str = _FIX_TEST_CMD) -> str:
    """A bug-fix SUMMARY with one red/green pair on `test`, red at `sha`."""
    red = f"| red | `python3 scripts/run_at_commit.py {sha} -- {test}` | 1 | fails |"
    green = f"| green | `{test}` | 0 | passes |"
    return _bug_fix_summary(f"{REAL_LANE_VERIFY}\n{red}\n{green}")


def _commit_change(repo: Path, rel: str, content: str = "changed\n") -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    _git(repo, "add", "--", rel)
    _git(repo, "commit", "-q", "-m", f"change {rel}")


def _lane_run(tmp_path: Path, text: str) -> int:
    """Run `--lane` on a SUMMARY written outside the repo (by file path)."""
    out_dir = tmp_path / "summary-copy"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "SUMMARY.md"
    path.write_text(text, encoding="utf-8")
    return vs.main(["--lane", str(path)])


# Expected messages, from the design's Error behavior section.
def _no_change_msg(sha: str) -> str:
    return (
        f"bug fix: no code change after red commit {sha} outside specs/ "
        "and the red test files"
    )


def _cannot_check_msg(sha: str, cause: str) -> str:
    return f"bug fix: cannot check the fix diff for red commit {sha} -- {cause}"


class TestRedGreen:
    def test_red_green_valid_pair_has_no_warning(
        self, fix_repo, monkeypatch, tmp_path, capsys
    ):
        monkeypatch.delenv("REQUIRE_RED_TEST", raising=False)
        sha = _red_sha(fix_repo)
        _commit_change(fix_repo, _FIX_SRC)
        text = _fix_summary(sha)
        assert vs._red_green_issue(text) is None
        assert _red_green_messages(text) == []
        write_summary(tmp_path, "bug", text)
        assert vs.main(["--lane", "bug"], specs_root=tmp_path / "specs") == 0
        assert "red/green" not in capsys.readouterr().out

    def test_red_green_missing_red_row_warns(self, monkeypatch, tmp_path, capsys):
        monkeypatch.delenv("REQUIRE_RED_TEST", raising=False)
        text = _bug_fix_summary(f"{REAL_LANE_VERIFY}\n{_GREEN_ROW}")
        assert vs.check_lane_evidence(text) == []
        warnings = vs.check_lane_warnings(text)
        assert len(warnings) == 1 and warnings[0][1] == "REQUIRE_RED_TEST"
        write_summary(tmp_path, "bug", text)
        assert vs.main(["--lane", "bug"], specs_root=tmp_path / "specs") == 0
        lines = [ln for ln in capsys.readouterr().out.splitlines() if "red/green" in ln]
        assert len(lines) == 1
        assert lines[0].startswith("    ! ")
        assert lines[0].endswith("(warn-only; set REQUIRE_RED_TEST=1 to enforce)")

    def test_red_green_blocks_when_opted_in(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("REQUIRE_RED_TEST", "1")
        text = _bug_fix_summary(f"{REAL_LANE_VERIFY}\n{_GREEN_ROW}")
        assert vs.check_lane_warnings(text) == []
        write_summary(tmp_path, "bug", text)
        assert vs.main(["--lane", "bug"], specs_root=tmp_path / "specs") == 1
        out = capsys.readouterr().out
        assert "    - bug fix: red/green" in out
        assert "    ! bug fix: red/green" not in out

    def test_red_green_opt_in_values_parsed_like_not_auto_verified(self, monkeypatch):
        text = _bug_fix_summary(f"{REAL_LANE_VERIFY}\n{_GREEN_ROW}")
        for value in ("0", "false", ""):
            monkeypatch.setenv("REQUIRE_RED_TEST", value)
            assert vs.check_lane_evidence(text) == []
            assert len(vs.check_lane_warnings(text)) == 1

    def test_red_green_warning_independent_of_not_auto_verified(self, monkeypatch):
        monkeypatch.delenv("REQUIRE_RED_TEST", raising=False)
        monkeypatch.setenv("REQUIRE_NOT_AUTO_VERIFIED", "1")
        text = _bug_fix_summary(f"{REAL_LANE_VERIFY}\n{_GREEN_ROW}")
        warnings = vs.check_lane_warnings(text)
        assert [var for _, var in warnings] == ["REQUIRE_RED_TEST"]

    def test_red_green_not_auto_verified_output_unchanged(
        self, monkeypatch, tmp_path, capsys
    ):
        monkeypatch.delenv("REQUIRE_NOT_AUTO_VERIFIED", raising=False)
        text = _lane_summary(
            lane="high-risk", verify=REAL_LANE_VERIFY, rollback="- `alembic downgrade -1`"
        )
        write_summary(tmp_path, "nav", text)
        assert vs.main(["--lane", "nav"], specs_root=tmp_path / "specs") == 0
        out = capsys.readouterr().out
        assert (
            "    ! lane `high-risk`: `### Not auto-verified` section missing -- state "
            "the negative scope (what this change claims that no gate checks), or "
            "`- none` (warn-only; set REQUIRE_NOT_AUTO_VERIFIED=1 to enforce)\n"
        ) in out

    def test_red_green_exemption_with_reason_is_accepted(self):
        text = _bug_fix_summary(
            f"{REAL_LANE_VERIFY}\n\nRed test exempt: race only reproduces under load"
        )
        assert vs._red_green_issue(text) is None

    def test_red_green_exemption_with_empty_reason_is_rejected(self):
        for line in ("Red test exempt:", "Red test exempt:   "):
            text = _bug_fix_summary(f"{REAL_LANE_VERIFY}\n\n{line}")
            issue = vs._red_green_issue(text)
            assert issue and "empty reason" in issue

    def test_red_green_green_command_differs_is_rejected(self):
        green = "| green | `pytest -q tests/test_other.py` | 0 | passes |"
        issue = vs._red_green_issue(_bug_fix_summary(f"{_RED_ROW}\n{green}"))
        assert issue and "green" in issue

    def test_red_green_green_command_whitespace_is_normalized(self):
        green = "| green | `pytest   -q  tests/test_bug.py` | 0 | passes |"
        assert vs._red_green_issue(_bug_fix_summary(f"{_RED_ROW}\n{green}")) is None

    def test_red_green_green_nonzero_exit_is_rejected(self):
        green = f"| green | `{_RED_TEST}` | 1 | passes |"
        assert vs._red_green_issue(_bug_fix_summary(f"{_RED_ROW}\n{green}"))

    def test_red_green_red_exit_range(self):
        for claimed, ok in (
            ("0", False),
            ("124", False),
            ("125", False),
            ("126", False),
            ("127", False),
            ("128", False),
            ("139", False),
            ("1", True),
            ("123", True),
        ):
            red = _RED_ROW.replace("| 1 | fails |", f"| {claimed} | fails |")
            issue = vs._red_green_issue(_bug_fix_summary(f"{red}\n{_GREEN_ROW}"))
            assert (issue is None) is ok, claimed

    def test_red_green_red_command_shape(self):
        for command, ok in (
            (f"scripts/run_at_commit.py abc1234 -- {_RED_TEST}", True),
            (f".claude/scripts/run_at_commit.py {'a' * 40} -- {_RED_TEST}", True),
            (f"python3 scripts/run_at_commit.py abc123 -- {_RED_TEST}", False),
            (f"python3 scripts/run_at_commit.py {'a' * 41} -- {_RED_TEST}", False),
            (f"python3 scripts/run_at_commit.py abc123z -- {_RED_TEST}", False),
            (f"python3 scripts/run_at_commit.py abc1234 {_RED_TEST}", False),
            ("python3 scripts/run_at_commit.py abc1234 --", False),
            (f"python3 scripts/other.py abc1234 -- {_RED_TEST}", False),
        ):
            red = f"| red | `{command}` | 1 | fails |"
            issue = vs._red_green_issue(_bug_fix_summary(f"{red}\n{_GREEN_ROW}"))
            assert (issue is None) is ok, command

    def test_red_green_check_cell_is_trimmed_and_case_folded(self):
        red = _RED_ROW.replace("| red |", "|  RED  |")
        green = _GREEN_ROW.replace("| green |", "| Green |")
        assert vs._red_green_issue(_bug_fix_summary(f"{red}\n{green}")) is None

    def test_red_green_mixed_case_input_type_applies(self):
        text = _bug_fix_summary(REAL_LANE_VERIFY, input_type="  Bug Fix ")
        assert vs._red_green_issue(text)

    def test_red_green_bug_fix_input_type_spellings_warn(self, monkeypatch):
        monkeypatch.delenv("REQUIRE_RED_TEST", raising=False)
        for input_type in ("bug-fix", "bugfix", "bug fix (harness)", "Bug-Fix"):
            text = _bug_fix_summary(f"{REAL_LANE_VERIFY}\n{_GREEN_ROW}", input_type=input_type)
            assert vs._red_green_issue(text) is not None, input_type
            warnings = [m for m, _ in vs.check_lane_warnings(text) if "red/green" in m]
            assert len(warnings) == 1, input_type

    def test_red_green_bug_fix_input_type_spellings_block_when_opted_in(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("REQUIRE_RED_TEST", "1")
        spellings = ("bug-fix", "bugfix", "bug fix (harness)", "Bug-Fix")
        for n, input_type in enumerate(spellings):
            text = _bug_fix_summary(f"{REAL_LANE_VERIFY}\n{_GREEN_ROW}", input_type=input_type)
            write_summary(tmp_path, f"bug{n}", text)
            assert vs.main(["--lane", f"bug{n}"], specs_root=tmp_path / "specs") == 1, input_type

    def test_red_green_other_input_type_has_no_message(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_RED_TEST", "1")
        for input_type in (
            "maintenance",
            "bug fixes",
            "bugfixes",
            "bug-fixes",
            "bug fix-up",
            "bugs fix",
            "harness fix",
        ):
            text = _bug_fix_summary(REAL_LANE_VERIFY, input_type=input_type)
            assert vs._red_green_issue(text) is None
            assert _red_green_messages(text) == []
        no_header = _lane_summary(lane="normal", verify=REAL_LANE_VERIFY)
        assert vs._red_green_issue(no_header) is None

    def test_red_green_no_message_for_existing_non_bug_fix_summaries(self, monkeypatch):
        specs = Path(__file__).resolve().parent.parent / "specs"
        paths = sorted(specs.glob("*/SUMMARY.md"))
        assert paths, "no specs/*/SUMMARY.md found"
        for value in ("", "1"):
            monkeypatch.setenv("REQUIRE_RED_TEST", value)
            for path in paths:
                text = path.read_text(encoding="utf-8")
                input_type = (vs._header_value(text, "Input-type") or "").strip().lower()
                if vs._BUG_FIX_INPUT_RE.match(input_type):
                    continue
                assert _red_green_messages(text) == [], path


# ---------------------------------------------------------------------------
# Fix-diff check: a bug fix must change code after the red commit
# ---------------------------------------------------------------------------


def test_fix_diff_noop(fix_repo, tmp_path, monkeypatch, capsys):
    sha = _red_sha(fix_repo)
    text = _fix_summary(sha)

    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    assert _lane_run(tmp_path, text) == 1
    assert f"    - {_no_change_msg(sha)}\n" in capsys.readouterr().out

    monkeypatch.delenv("REQUIRE_RED_TEST")
    assert _lane_run(tmp_path, text) == 0
    lines = [ln.strip() for ln in capsys.readouterr().out.splitlines()]
    advisories = [ln for ln in lines if ln.startswith("!") and "no code change" in ln]
    assert advisories == [
        f"! {_no_change_msg(sha)} (warn-only; set REQUIRE_RED_TEST=1 to enforce)"
    ]


def test_fix_diff_real_fix(fix_repo, tmp_path, monkeypatch, capsys):
    sha = _red_sha(fix_repo)
    _commit_change(fix_repo, _FIX_SRC, "def f():\n    return 2\n")
    text = _fix_summary(sha)
    for value in ("1", ""):
        monkeypatch.setenv("REQUIRE_RED_TEST", value)
        assert _lane_run(tmp_path, text) == 0, value
        out = capsys.readouterr().out
        assert "no code change" not in out and "cannot check" not in out, value


def test_fix_diff_test_only(fix_repo, tmp_path, monkeypatch, capsys):
    sha = _red_sha(fix_repo)
    _commit_change(fix_repo, _FIX_TEST, "def test_y():\n    assert True\n")
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    assert _lane_run(tmp_path, _fix_summary(sha)) == 1
    assert f"    - {_no_change_msg(sha)}\n" in capsys.readouterr().out


def test_fix_diff_specs_only(fix_repo, tmp_path, monkeypatch, capsys):
    sha = _red_sha(fix_repo)
    _commit_change(fix_repo, "specs/bug/SUMMARY.md")
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    assert _lane_run(tmp_path, _fix_summary(sha)) == 1
    assert f"    - {_no_change_msg(sha)}\n" in capsys.readouterr().out


def test_fix_diff_red_commit_edits_source(fix_repo, tmp_path, monkeypatch, capsys):
    """D10: a path the red commit changed is a red test file, even a source file."""
    (fix_repo / _FIX_SRC).write_text("def f():\n    return 3\n")
    (fix_repo / _FIX_TEST).write_text("def test_y():\n    assert f() == 2\n")
    _git(fix_repo, "add", "--", _FIX_SRC, _FIX_TEST)
    _git(fix_repo, "commit", "-q", "-m", "red edits source and test")
    sha = _red_sha(fix_repo)
    _commit_change(fix_repo, _FIX_SRC, "def f():\n    return 2\n")
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    assert _lane_run(tmp_path, _fix_summary(sha)) == 1
    assert f"    - {_no_change_msg(sha)}\n" in capsys.readouterr().out


def test_fix_diff_directory_token(fix_repo, tmp_path, monkeypatch, capsys):
    """A directory in the red command still excludes the red test file (D10)."""
    sha = _red_sha(fix_repo)
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    _commit_change(fix_repo, _FIX_TEST, "def test_y():\n    assert True\n")
    text = _fix_summary(sha, "pytest scripts/")
    assert _lane_run(tmp_path, text) == 1
    assert f"    - {_no_change_msg(sha)}\n" in capsys.readouterr().out
    # A source change in the same directory counts as the fix.
    _commit_change(fix_repo, _FIX_SRC, "def f():\n    return 2\n")
    assert _lane_run(tmp_path, text) == 0
    assert "bug fix:" not in capsys.readouterr().out


def test_fix_diff_command_names_fixed_file(fix_repo, tmp_path, monkeypatch, capsys):
    """A red command that runs the file under repair does not hide the fix (D10)."""
    sha = _red_sha(fix_repo)
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    _commit_change(fix_repo, _FIX_SRC, "def f():\n    return 2\n")
    text = _fix_summary(sha, f"python3 -m doctest {_FIX_SRC}")
    assert _lane_run(tmp_path, text) == 0
    assert "bug fix:" not in capsys.readouterr().out


def test_fix_diff_absolute_test_path(fix_repo, tmp_path, monkeypatch, capsys):
    """An absolute test path in the red command still excludes the red test file (D10)."""
    sha = _red_sha(fix_repo)
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    _commit_change(fix_repo, _FIX_TEST, "def test_y():\n    assert True\n")
    text = _fix_summary(sha, f"python3 -m pytest -q {fix_repo / _FIX_TEST}")
    assert _lane_run(tmp_path, text) == 1
    assert f"    - {_no_change_msg(sha)}\n" in capsys.readouterr().out


def test_fix_diff_staged_fix(fix_repo, tmp_path, monkeypatch, capsys):
    sha = _red_sha(fix_repo)
    text = _fix_summary(sha)
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    # An unstaged fix is not in the index, so it does not count.
    (fix_repo / _FIX_SRC).write_text("def f():\n    return 2\n")
    assert _lane_run(tmp_path, text) == 1
    assert f"    - {_no_change_msg(sha)}\n" in capsys.readouterr().out
    # The same fix, staged but not committed, counts.
    _git(fix_repo, "add", "--", _FIX_SRC)
    assert _lane_run(tmp_path, text) == 0
    assert "bug fix:" not in capsys.readouterr().out


def test_fix_diff_unknown_sha(fix_repo, tmp_path, monkeypatch, capsys):
    text = _fix_summary("deadbee")
    expected = _cannot_check_msg("deadbee", "the commit does not resolve here")
    assert vs._red_fix_diff_issue(text) == expected
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    assert _lane_run(tmp_path, text) == 1
    assert f"    - {expected}\n" in capsys.readouterr().out


def test_fix_diff_not_a_repo(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("REQUIRE_NOT_AUTO_VERIFIED", raising=False)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    expected = _cannot_check_msg(
        "abc1234", "the current directory is not in a git repository"
    )
    # `_lane_run` passes an absolute path, so the SUMMARY reads from any cwd.
    assert _lane_run(tmp_path, _fix_summary("abc1234")) == 1
    assert f"    - {expected}\n" in capsys.readouterr().out
    assert vs._red_fix_diff_issue(_fix_summary("abc1234")) == expected


def test_fix_diff_git_missing(fix_repo, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    expected = _cannot_check_msg("abc1234", "git is not available")
    # `_lane_run` passes an absolute path, so reading it needs no PATH lookup.
    assert _lane_run(tmp_path, _fix_summary("abc1234")) == 1
    assert f"    - {expected}\n" in capsys.readouterr().out
    assert vs._red_fix_diff_issue(_fix_summary("abc1234")) == expected


def test_fix_diff_exempt_and_non_bug_fix(fix_repo, tmp_path, monkeypatch):
    def no_git(*args, **kwargs):
        raise AssertionError(f"git was called: {args}")

    monkeypatch.setattr(vs.subprocess, "check_output", no_git)
    sha = _red_sha(fix_repo)  # the fixture's own git calls go through subprocess.run
    exempt = _fix_summary(sha) + "\nRed test exempt: race only reproduces under load\n"
    non_bug_fix = _fix_summary(sha).replace(
        "Input-type: bug fix", "Input-type: maintenance"
    )
    for text in (exempt, non_bug_fix):
        assert vs._red_pairs(text) == []
        assert vs._red_fix_diff_issue(text) is None
        for value in ("1", ""):
            monkeypatch.setenv("REQUIRE_RED_TEST", value)
            assert _lane_run(tmp_path, text) == 0


def test_fix_diff_commit_gate_shape(fix_repo, tmp_path, monkeypatch, capsys):
    """commit-gate.sh runs `--lane` on a temp copy outside the repo, cwd in the repo."""
    sha = _red_sha(fix_repo)
    _commit_change(fix_repo, _FIX_SRC, "def f():\n    return 2\n")
    copy_dir = tmp_path / "gate-tmp"
    copy_dir.mkdir()
    copy = copy_dir / "SUMMARY.md"
    copy.write_text(_fix_summary(sha), encoding="utf-8")
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    assert vs.main(["--lane", str(copy)]) == 0
    assert "bug fix:" not in capsys.readouterr().out


def test_fix_diff_gh302(monkeypatch):
    root = Path(__file__).resolve().parent.parent
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "ee6da93^{commit}"],
        cwd=root,
        capture_output=True,
    )
    if resolved.returncode != 0:
        pytest.skip("ee6da93 does not resolve here (shallow clone or tarball)")
    monkeypatch.chdir(root)
    monkeypatch.delenv("REQUIRE_NOT_AUTO_VERIFIED", raising=False)
    monkeypatch.setenv("REQUIRE_RED_TEST", "1")
    summary = root / "specs/gh-302-red-green-input-type/SUMMARY.md"
    assert vs.main(["--lane", str(summary)]) == 0


# The red row's command shape is copied into two prose files that tell agents how to write it.
# Anchor both copies to the checker, so a format change here cannot leave the prose behind.
_RED_ROW_TEMPLATE = "python3 scripts/run_at_commit.py <red sha> -- <test command>"
_RED_ROW_PROSE = (
    "skills/subagent-driven-development/implementer-prompt.md",
    "rules/auto-correct-scope.md",
)


def test_red_green_prose_command_shape_is_accepted_by_the_check(monkeypatch):
    monkeypatch.delenv("REQUIRE_RED_TEST", raising=False)
    root = Path(__file__).resolve().parent.parent
    for rel in _RED_ROW_PROSE:
        prose = " ".join((root / rel).read_text(encoding="utf-8").split())
        assert _RED_ROW_TEMPLATE in prose, rel
    red = _RED_ROW_TEMPLATE.replace("<red sha>", "abc1234").replace("<test command>", _RED_TEST)
    text = _bug_fix_summary(f"| red | `{red}` | 1 | fails |\n{_GREEN_ROW}")
    assert vs._red_green_issue(text) is None


def test_red_green_input_type_reaches_the_implementer():
    root = Path(__file__).resolve().parent.parent
    sdd = root / "skills/subagent-driven-development"
    assert "Input type: [INPUT_TYPE]" in (sdd / "implementer-prompt.md").read_text(encoding="utf-8")
    assert "`[INPUT_TYPE]` from SUMMARY" in (sdd / "SKILL.md").read_text(encoding="utf-8")
