import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("task_brief.py")
SPEC = importlib.util.spec_from_file_location("task_brief", SCRIPT)
assert SPEC and SPEC.loader
task_brief = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(task_brief)


def test_task_id_match_is_exact():
    text = "### Task 1.10 — sibling\n\n- **Action:** wrong\n"
    assert task_brief.task_block(text, "1.1") is None


def test_task_id_accepts_colon_heading_separator():
    text = "### Task 1.1: supported\n\n- **Action:** right\n"
    assert task_brief.task_block(text, "1.1") is not None


def test_mapped_rows_do_not_match_sc_prefixes():
    text = """## 3. Success Criteria

| ID | x |
| --- | --- |
| SC-1 | one |
| SC-10 | ten |
"""
    assert task_brief.mapped_rows(text, ["SC-1"]) == ["| SC-1 | one |"]
