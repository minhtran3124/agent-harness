from pathlib import Path

from check_plan_contract import errors


def test_legacy_is_accepted():
    assert errors("# old\n\n### Task 1.1 — old\n") == []


def test_produces_must_name_a_backticked_artifact():
    text = """## Global Constraints

- x

## 3. Success Criteria

| ID | x | x | x |
|---|---|---|---|
| SC-1 | x | x | exit 0 |

## 4. Tasks

### Task 1.1 — x

- **Criteria:** SC-1
- **Interfaces:** Consumes: input. Produces: some prose without a tracked artifact.
"""
    assert any("Produces must name a backticked artifact" in item for item in errors(text))


def test_backticked_produces_is_accepted_with_prose_consumes():
    text = """## Global Constraints

- x

## 3. Success Criteria

| ID | x | x | x |
|---|---|---|---|
| SC-1 | x | x | exit 0 |

## 4. Tasks

### Task 1.1 — x

- **Criteria:** SC-1
- **Interfaces:** Consumes existing prose inputs; produces `out.py`.
"""
    assert errors(text) == []


def test_fenced_example_task_is_ignored():
    text = """## Global Constraints

- x

## 3. Success Criteria

| ID | x | x | x |
|---|---|---|---|
| SC-1 | x | x | exit 0 |

## 4. Tasks

Illustration of the task shape (not a real task):

```
### Task 9.9 — example only
- **Files:** demo
```

### Task 1.1 — real

- **Criteria:** SC-1
- **Interfaces:** Consumes: input. Produces: `out.py`
"""
    problems = errors(text)
    assert not any("Task 9.9" in item for item in problems), problems


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


def test_artifact_name_does_not_satisfy_required_produces_verb():
    text = """## Global Constraints

- x

## 3. Success Criteria

| ID | x | x | x |
|---|---|---|---|
| SC-1 | x | x | exit 0 |

## 4. Tasks

### Task 1.1 — consumer

- **Criteria:** SC-1
- **Interfaces:** Consumes: `produces.py`
"""
    assert any("must name what it consumes and produces" in item for item in errors(text))


# --- Seam rule (gh-312): design.md "Error behavior" table, D1, D7, D12, D13, D16 ---

SEAM_OK = "- **Seams:** `errors()` return list — catches: a wrong reject; misses: `main()`"


def marked_plan(seams=SEAM_OK, marker="- Plan-contract: 2", tail=""):
    """A plan that passes today's checks; `seams` is the line after Interfaces (None = no line)."""
    seam_line = "" if seams is None else seams + "\n"
    return f"""## Global Constraints

- x
{marker}

## 3. Success Criteria

| ID | x | x | x |
|---|---|---|---|
| SC-1 | x | x | exit 0 |

## 4. Tasks

### Task 1.1 — x

- **Criteria:** SC-1
- **Interfaces:** Consumes: input. Produces: `out.py`
{seam_line}{tail}"""


def test_marker_plan_with_valid_seam_passes():
    assert errors(marked_plan()) == []


def test_marker_plan_with_two_seams_on_one_line_passes():
    seams = "- **Seams:** a — catches: x; misses: y | b — catches: z; misses: w"
    assert errors(marked_plan(seams)) == []


def test_marker_plan_star_bullet_seam_passes():
    assert errors(marked_plan("* **Seams:** a — catches: x; misses: y")) == []


def test_marker_plan_task_without_seams_is_rejected():
    assert errors(marked_plan(None)) == ["PLAN.md: Task 1.1 missing Seams"]


def test_marker_plan_task_with_two_seams_bullets_is_rejected():
    two = SEAM_OK + "\n" + SEAM_OK
    problems = errors(marked_plan(two))
    assert len(problems) == 1 and "Task 1.1" in problems[0] and "Seams" in problems[0], problems


def test_seams_none_with_reason_passes():
    assert errors(marked_plan("- **Seams:** none — prose-only change")) == []
    assert errors(marked_plan("- **Seams:** none - prose-only change")) == []


def test_seams_none_with_empty_reason_is_rejected():
    for line in ("- **Seams:** none", "- **Seams:** none —", "- **Seams:** none -   "):
        problems = errors(marked_plan(line))
        assert len(problems) == 1 and "Task 1.1" in problems[0], (line, problems)


def test_seam_named_nonempty_is_a_seam_not_the_none_form():
    assert errors(marked_plan("- **Seams:** nonempty list — catches: x; misses: y")) == []


def test_seam_without_catches_is_rejected():
    problems = errors(marked_plan("- **Seams:** a — misses: y"))
    assert len(problems) == 1 and "catches" in problems[0], problems


def test_seam_without_misses_is_rejected():
    problems = errors(marked_plan("- **Seams:** a — catches: x"))
    assert len(problems) == 1 and "misses" in problems[0], problems


def test_second_seam_without_misses_is_rejected():
    problems = errors(marked_plan("- **Seams:** a — catches: x; misses: y | b — catches: z"))
    assert len(problems) == 1 and "misses" in problems[0], problems


def test_empty_catches_before_semicolon_is_rejected():
    problems = errors(marked_plan("- **Seams:** a — catches: ; misses: y"))
    assert len(problems) == 1 and "catches" in problems[0], problems


def test_empty_catches_directly_before_misses_is_rejected():
    problems = errors(marked_plan("- **Seams:** a — catches: misses: y"))
    assert len(problems) == 1 and "catches" in problems[0], problems


def test_empty_misses_before_next_seam_is_rejected():
    problems = errors(marked_plan("- **Seams:** a — catches: x; misses: | b — catches: z; misses: w"))
    assert len(problems) == 1 and "misses" in problems[0], problems


def test_empty_misses_at_end_of_line_is_rejected():
    problems = errors(marked_plan("- **Seams:** a — catches: x; misses:   "))
    assert len(problems) == 1 and "misses" in problems[0], problems


def test_only_first_line_of_seams_bullet_is_read():
    seams = "- **Seams:** a — catches: x\n  misses: y on a continuation line"
    problems = errors(marked_plan(seams))
    assert len(problems) == 1 and "misses" in problems[0], problems


def test_unknown_plan_contract_version_is_rejected():
    problems = errors(marked_plan(marker="- Plan-contract: 3"))
    assert any("unknown Plan-contract version" in item for item in problems), problems


def test_seams_not_directly_after_interfaces_is_rejected():
    text = marked_plan(None, tail="- **Verify:** `true`\n" + SEAM_OK + "\n")
    problems = errors(text)
    assert len(problems) == 1 and "Task 1.1" in problems[0] and "Interfaces" in problems[0], problems


def test_seams_before_interfaces_is_rejected():
    text = marked_plan(None).replace("- **Criteria:**", SEAM_OK + "\n- **Criteria:**")
    problems = errors(text)
    assert len(problems) == 1 and "Interfaces" in problems[0], problems


def test_no_marker_keeps_todays_result():
    assert errors(marked_plan(None, marker="")) == []


def test_fenced_marker_is_not_a_marker():
    fenced = "\n```\n- Plan-contract: 2\n```\n"
    assert errors(marked_plan(None, marker=fenced)) == []
    assert errors(marked_plan(None, marker="\n```\n- Plan-contract: 9\n```\n")) == []


def test_bare_line_marker_is_not_a_marker():
    assert errors(marked_plan(None, marker="Plan-contract: 2")) == []
    assert errors(marked_plan(None, marker="Plan-contract: 9")) == []


def test_marker_in_another_section_is_not_a_marker():
    text = marked_plan(None, marker="").replace(
        "## 3. Success Criteria", "## 2. Notes\n\n- Plan-contract: 2\n\n## 3. Success Criteria"
    )
    assert errors(text) == []


def test_corpus_every_committed_plan_passes():
    root = Path(__file__).resolve().parent.parent
    plans = sorted(root.glob("specs/*/PLAN.md"))
    assert plans
    for plan in plans:
        assert errors(plan.read_text(encoding="utf-8"), str(plan)) == [], plan
