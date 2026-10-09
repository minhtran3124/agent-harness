"""Tests for scripts/check_open_questions.py — run via pytest (wired into run-tests.sh).

One case per row of the design's error-behavior table
(specs/gh-258-open-questions-register/design.md), plus the slug-matching edges, a duplicate
ID, an ignored progress note, and an undecodable register that must not crash the script.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parent / "check_open_questions.py"
REGISTER = "specs/parent/QUESTIONS.md"


def block(n: int = 1, **fields: str) -> str:
    values = {
        "raised-by": "design.md §D4",
        "closes-at": "phase-6",
        "decided-by": "measurement",
        "default-until-closed": "doctor reports advisory",
        "status": "open",
    }
    values.update(fields)
    lines = [f"## OQ-{n}", ""]
    lines += [f"- {key}: {value}" for key, value in values.items() if value is not None]
    return "\n".join(lines) + "\n\n"


def write(root: Path, text: str | bytes, rel: str = REGISTER) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text("# parent — Open questions\n\n" + text)


def run(root: Path, *args: str, strict: bool = False, cwd: Path | None = None):
    env = dict(os.environ)
    env.pop("REQUIRE_QUESTIONS_CLOSED", None)
    if strict:
        env["REQUIRE_QUESTIONS_CLOSED"] = "1"
    argv = [sys.executable, str(CHECKER), *args]
    if cwd is None:
        argv += ["--root", str(root)]
    return subprocess.run(argv, capture_output=True, text=True, env=env, cwd=cwd)


def test_no_register_is_silent(tmp_path):
    for strict in (False, True):
        result = run(tmp_path, "--slug", "phase-6", strict=strict)
        assert result.returncode == 0
        assert result.stderr == ""


@pytest.mark.parametrize("closes_at", ["phase-6", "phase-6#3.2"])
def test_open_question_closing_here_warns(tmp_path, closes_at):
    write(tmp_path, block(3, **{"closes-at": closes_at}))
    result = run(tmp_path, "--slug", "phase-6")
    assert result.returncode == 0
    assert REGISTER in result.stderr
    assert "OQ-3" in result.stderr
    assert "doctor reports advisory" in result.stderr
    assert run(tmp_path, "--slug", "phase-6", strict=True).returncode == 1


def test_closed_question_with_evidence_is_silent(tmp_path):
    write(tmp_path, block(status="closed", **{"closed-by": "PR #300 measured it"}))
    for strict in (False, True):
        result = run(tmp_path, "--slug", "phase-6", strict=strict)
        assert result.returncode == 0
        assert result.stderr == ""


@pytest.mark.parametrize("closes_at", ["phase-7", "phase-6-other", "phase-6-other#1.1"])
def test_open_question_for_another_slug_is_silent(tmp_path, closes_at):
    write(tmp_path, block(**{"closes-at": closes_at}))
    result = run(tmp_path, "--slug", "phase-6", strict=True)
    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.parametrize(
    "fields, defect",
    [
        ({"decided-by": "vote"}, "decided-by"),
        ({"status": "pending"}, "status"),
        ({"raised-by": None}, "raised-by"),
        ({"default-until-closed": ""}, "default-until-closed"),
        ({"closes-at": "phase 6"}, "closes-at"),
        ({"status": "closed"}, "closed-by"),
    ],
)
def test_malformed_block_is_reported_in_any_register(tmp_path, fields, defect):
    # The register names another slug: malformed blocks are reported regardless (D5).
    write(tmp_path, block(4, **{"closes-at": "phase-9", **fields}))
    result = run(tmp_path, "--slug", "phase-6")
    assert result.returncode == 0
    assert REGISTER in result.stderr
    assert "OQ-4" in result.stderr
    assert defect in result.stderr
    assert run(tmp_path, "--slug", "phase-6", strict=True).returncode == 1


def test_malformed_heading_reported_with_line(tmp_path):
    write(tmp_path, "## OQ-x\n\n- status: open\n")
    result = run(tmp_path, "--slug", "phase-6")
    assert result.returncode == 0
    assert REGISTER in result.stderr
    assert "line 3" in result.stderr


def test_duplicate_id_in_one_file_is_reported(tmp_path):
    closed = {"status": "closed", "closed-by": "done", "closes-at": "phase-9"}
    write(tmp_path, block(2, **closed) + block(2, **closed))
    result = run(tmp_path, "--slug", "phase-6")
    assert result.returncode == 0
    assert "OQ-2" in result.stderr
    assert "duplicate" in result.stderr
    assert run(tmp_path, "--slug", "phase-6", strict=True).returncode == 1


def test_progress_note_bullet_is_ignored(tmp_path):
    text = block(**{"closes-at": "phase-9"}) + "- 2026-10-09: still open after phase 5.\n"
    write(tmp_path, text)
    result = run(tmp_path, "--slug", "phase-6", strict=True)
    assert result.returncode == 0
    assert result.stderr == ""


def test_undecodable_register_is_reported_without_traceback(tmp_path):
    write(tmp_path, b"## OQ-1\n\n- status: open\xff\n")
    result = run(tmp_path, "--slug", "phase-6")
    assert result.returncode == 0
    assert REGISTER in result.stderr
    assert "Traceback" not in result.stderr
    strict = run(tmp_path, "--slug", "phase-6", strict=True)
    assert strict.returncode == 1
    assert "Traceback" not in strict.stderr


@pytest.mark.parametrize("heading", ["### OQ-1", "##OQ-1", "# OQ-1", "## oq-1"])
def test_near_miss_heading_is_reported(tmp_path, heading):
    text = block(**{"closes-at": "phase-9"}).replace("## OQ-1", heading, 1)
    write(tmp_path, text)
    result = run(tmp_path, "--slug", "phase-6")
    assert result.returncode == 0
    assert "heading is not '## OQ-<n>'" in result.stderr
    assert heading in result.stderr
    assert run(tmp_path, "--slug", "phase-6", strict=True).returncode == 1


def test_register_with_byte_order_mark_is_read(tmp_path):
    write(tmp_path, b"\xef\xbb\xbf" + block().encode("utf-8"))
    result = run(tmp_path, "--slug", "phase-6")
    assert result.returncode == 0
    assert "OQ-1: open question closes at phase-6" in result.stderr


def test_duplicate_field_is_reported(tmp_path):
    text = block(**{"closes-at": "phase-9"}) + "- status: closed\n- closed-by: PR #1\n"
    write(tmp_path, text)
    result = run(tmp_path, "--slug", "phase-6")
    assert result.returncode == 0
    assert "OQ-1: malformed: duplicate field status" in result.stderr
    assert run(tmp_path, "--slug", "phase-6", strict=True).returncode == 1


def test_duplicate_field_keeps_first_value_for_matching(tmp_path):
    write(tmp_path, block() + "- status: closed\n- closed-by: PR #1\n")
    result = run(tmp_path, "--slug", "phase-6")
    assert "OQ-1: open question closes at phase-6" in result.stderr


@pytest.mark.parametrize("name", ["check_open_questions.py", "test_check_open_questions.py"])
def test_postponed_annotations_for_python_3_8(name):
    # `str | None` and `tuple[...]` annotations need this import below Python 3.10.
    source = (CHECKER.parent / name).read_text(encoding="utf-8")
    assert "\nfrom __future__ import annotations\n" in source


def test_missing_slug_is_usage_error(tmp_path):
    result = run(tmp_path)
    assert result.returncode == 2
    assert "usage" in result.stderr


def test_root_defaults_to_current_directory(tmp_path):
    write(tmp_path, block())
    result = run(tmp_path, "--slug", "phase-6", cwd=tmp_path)
    assert result.returncode == 0
    assert "OQ-1" in result.stderr
