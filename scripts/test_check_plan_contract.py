from pathlib import Path

from check_plan_contract import errors


def test_legacy_is_accepted():
    assert errors("# old\n\n### Task 1.1 — old\n") == []


def test_new_contract_requires_task_fields():
    text = "## Global Constraints\n\n- x\n\n## 3. Success Criteria\n\n| ID | x | x | x |\n|---|---|---|---|\n| SC-1 | x | x | exit 0 |\n\n## 4. Tasks\n\n### Task 1.1 — x\n\n- **Files:** x\n"
    assert any("missing Criteria" in item for item in errors(text))


def test_dotted_consumed_artifact_requires_a_producer():
    text = """## Global Constraints

- x

## 3. Success Criteria

| ID | x | x | x |
|---|---|---|---|
| SC-1 | x | x | exit 0 |

## 4. Tasks

### Task 1.0 — source

- **Criteria:** SC-1
- **Interfaces:** Consumes: input. Produces: `in.py`

### Task 1.1 — x

- **Criteria:** SC-1
- **Interfaces:** Consumes: `missing_module.py`. Produces: `output.json`.
"""
    assert any("missing_module.py with no producer" in item for item in errors(text))


def test_colonless_produces_clause_keeps_both_artifacts_separate():
    text = """## Global Constraints

- x

## 3. Success Criteria

| ID | x | x | x |
|---|---|---|---|
| SC-1 | x | x | exit 0 |

## 4. Tasks

### Task 1.0 — source

- **Criteria:** SC-1
- **Interfaces:** Consumes: input. Produces: `in.py`

### Task 1.1 — x

- **Criteria:** SC-1
- **Interfaces:** Consumes: `in.py`, produces `helper.py`
"""
    assert errors(text) == []


def test_artifact_name_containing_produces_is_not_an_interface_separator():
    text = """## Global Constraints

- x

## 3. Success Criteria

| ID | x | x | x |
|---|---|---|---|
| SC-1 | x | x | exit 0 |

## 4. Tasks

### Task 1.0 — source

- **Criteria:** SC-1
- **Interfaces:** Consumes: input. Produces: `produces.py`

### Task 1.1 — consumer

- **Criteria:** SC-1
- **Interfaces:** Consumes: `produces.py`. Produces: `out.py`
"""
    assert errors(text) == []
