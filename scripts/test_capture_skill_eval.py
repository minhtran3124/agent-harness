from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("capture_skill_eval.py")
SPEC = importlib.util.spec_from_file_location("capture_skill_eval", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_extracts_final_result_from_claude_array():
    result, usage = MODULE.extract_result([
        {"type": "system"},
        {"type": "result", "result": "observed", "usage": {"input_tokens": 3}},
    ])
    assert result == "observed"
    assert usage == {"input_tokens": 3}


def test_rejects_missing_or_empty_final_result():
    try:
        MODULE.extract_result([{"type": "result", "result": ""}])
    except ValueError as exc:
        assert "no text" in str(exc)
    else:
        raise AssertionError("empty result must fail")


def test_uses_direct_claude_executable_by_default():
    assert MODULE.main.__name__ == "main"
