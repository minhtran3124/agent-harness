import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import evaluator_result as er

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluator_result.py")


def valid_result() -> dict:
    return {
        "evaluator": "verify-summary",
        "status": "pass",
        "score": None,
        "evidence": [{"source": "stdout", "message": "ok"}],
        "exit": 0,
    }


def test_public_names_match_the_brief():
    assert tuple(er.REQUIRED_KEYS) == (
        "evaluator",
        "status",
        "score",
        "evidence",
        "exit",
    )
    assert set(er.STATUSES) == {"pass", "fail", "error", "skipped"}


def test_schema_file_is_json_and_declares_required_keys():
    with open(er.SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["required"] == list(er.REQUIRED_KEYS)
    assert schema["properties"]["status"]["enum"] == list(er.STATUSES)


def test_valid_object_passes():
    assert er.validate(valid_result()) == []


def test_score_null_passes_and_number_passes():
    assert er.validate(valid_result()) == []  # score is null in the fixture
    scored = valid_result()
    scored["score"] = 0.75
    assert er.validate(scored) == []


def test_optional_keys_pass_when_well_typed():
    obj = valid_result()
    obj["argv"] = ["--lane", "demo"]
    obj["duration_ms"] = 12
    assert er.validate(obj) == []


def test_missing_status_fails_naming_the_key():
    obj = valid_result()
    del obj["status"]
    errors = er.validate(obj)
    assert len(errors) == 1
    assert "status" in errors[0]


def test_bad_enum_fails():
    obj = valid_result()
    obj["status"] = "ok"
    errors = er.validate(obj)
    assert len(errors) == 1
    assert "status" in errors[0] and "ok" in errors[0]


def test_evidence_item_missing_message_fails():
    obj = valid_result()
    obj["evidence"] = [{"source": "stdout"}]
    errors = er.validate(obj)
    assert len(errors) == 1
    assert "evidence[0]" in errors[0] and "message" in errors[0]


@pytest.mark.parametrize(
    "key, bad",
    [
        ("evaluator", 1),
        ("score", "high"),
        ("score", True),  # bool is not a number here
        ("evidence", "stdout"),
        ("evidence", ["stdout"]),
        ("exit", "0"),
        ("exit", False),  # bool is not an int here
        ("argv", "--lane"),
        ("argv", [1]),
        ("duration_ms", 1.5),
    ],
)
def test_wrong_types_fail_naming_the_key(key, bad):
    obj = valid_result()
    obj[key] = bad
    errors = er.validate(obj)
    assert len(errors) == 1
    assert key in errors[0]


def test_non_object_fails():
    assert len(er.validate(["not", "an", "object"])) == 1


def test_one_message_per_violation():
    obj = valid_result()
    del obj["status"]
    obj["exit"] = "0"
    assert len(er.validate(obj)) == 2


def test_self_check_exits_0_and_prints_required_keys():
    proc = subprocess.run(
        [sys.executable, SCRIPT, "--self-check"], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == list(er.REQUIRED_KEYS)


def test_validate_cli_exit_codes(tmp_path, capsys):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(valid_result()))
    assert er.main(["--validate", str(good)]) == 0

    bad = tmp_path / "bad.json"
    obj = valid_result()
    obj["status"] = "ok"
    bad.write_text(json.dumps(obj))
    assert er.main(["--validate", str(bad)]) == 1
    assert "status" in capsys.readouterr().out

    not_json = tmp_path / "not.json"
    not_json.write_text("{")
    assert er.main(["--validate", str(not_json)]) == 2
    assert er.main(["--validate", str(tmp_path / "absent.json")]) == 2


def test_no_flag_is_bad_invocation():
    with pytest.raises(SystemExit) as exc_info:
        er.main([])
    assert exc_info.value.code == 2
