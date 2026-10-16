import importlib.util
import subprocess
import sys
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


# This test reads the live plan of spec gh-312-test-seams. If Task 1.1's `Seams:` line
# changes or the spec moves, update this test.
LIVE_PLAN = SCRIPT.parents[3] / "specs" / "gh-312-test-seams" / "PLAN.md"


def test_brief_carries_plan_contract_marker_and_task_seams(tmp_path):
    plan_text = LIVE_PLAN.read_text()
    task_section = plan_text.split("### Task 1.1 ", 1)[1].split("\n### ", 1)[0]
    seams_line = next(
        line for line in task_section.splitlines() if line.startswith("- **Seams:**")
    )
    output = tmp_path / "brief.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--plan",
            str(LIVE_PLAN),
            "--task",
            "1.1",
            "--output",
            str(output),
        ],
        check=True,
        cwd=LIVE_PLAN.parents[2],
    )
    brief_lines = output.read_text().splitlines()
    assert "- Plan-contract: 2" in brief_lines
    assert seams_line in brief_lines
