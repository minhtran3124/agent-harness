from pathlib import Path

from check_plan_contract import errors


def test_legacy_is_accepted():
    assert errors("# old\n\n### Task 1.1 — old\n") == []


def test_new_contract_requires_task_fields():
    text = "## Global Constraints\n\n- x\n\n## 3. Success Criteria\n\n| ID | x | x | x |\n|---|---|---|---|\n| SC-1 | x | x | exit 0 |\n\n## 4. Tasks\n\n### Task 1.1 — x\n\n- **Files:** x\n"
    assert any("missing Criteria" in item for item in errors(text))
