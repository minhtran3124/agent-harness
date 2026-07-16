"""Tests for the PLAN.md format validator.

Run:

    python -m pytest scripts/test_check_plan_format.py -q
"""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_plan_format", Path(__file__).resolve().parent / "check_plan_format.py"
)
assert _SPEC and _SPEC.loader, "could not load check_plan_format.py"
cpf = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cpf)


FRONTMATTER = """\
---
slug: demo
status: active
owner: Test
created: 2026-05-23
---

# Demo
"""


def task(
    tid="1.1",
    wave="1",
    files="app/a.py",
    action="Do the thing.",
    verify="pytest tests/a.py -x",
    done="Tests pass.",
):
    """Build one fenced-xml task block, omitting a tag when its value is None."""
    wave_attr = f' wave="{wave}"' if wave is not None else ""
    lines = [f'<task id="{tid}"{wave_attr}>']
    if files is not None:
        lines.append(f"  <files>{files}</files>")
    if action is not None:
        lines.append(f"  <action>{action}</action>")
    if verify is not None:
        lines.append(f"  <verify>{verify}</verify>")
    if done is not None:
        lines.append(f"  <done>{done}</done>")
    lines.append("</task>")
    block = "\n".join(lines)
    return f"```xml\n{block}\n```\n"


def plan(*task_blocks, frontmatter=FRONTMATTER):
    return frontmatter + "\n## 4. Tasks\n\n" + "\n".join(task_blocks)


# --------------------------------------------------------------------------- #
# parse_frontmatter
# --------------------------------------------------------------------------- #
class TestParseFrontmatter:
    def test_extracts_keys(self):
        fm = cpf.parse_frontmatter(FRONTMATTER)
        assert fm["slug"] == "demo"
        assert fm["status"] == "active"

    def test_no_frontmatter_returns_empty(self):
        assert cpf.parse_frontmatter("# No frontmatter\n") == {}

    def test_unclosed_frontmatter_returns_empty(self):
        assert cpf.parse_frontmatter("---\nslug: x\n# never closed\n") == {}


# --------------------------------------------------------------------------- #
# extract_tasks
# --------------------------------------------------------------------------- #
class TestExtractTasks:
    def test_finds_task_inside_fenced_block(self):
        tasks = cpf.extract_tasks(plan(task()))
        assert len(tasks) == 1
        assert tasks[0]["id"] == "1.1"
        assert tasks[0]["wave"] == "1"
        assert tasks[0]["files"] == ["app/a.py"]

    def test_splits_comma_separated_files(self):
        tasks = cpf.extract_tasks(plan(task(files="app/a.py, app/b.py")))
        assert tasks[0]["files"] == ["app/a.py", "app/b.py"]

    def test_multiple_tasks(self):
        text = plan(task(tid="1.1"), task(tid="2.1", files="app/b.py"))
        assert len(cpf.extract_tasks(text)) == 2


# --------------------------------------------------------------------------- #
# check_plan — happy path
# --------------------------------------------------------------------------- #
class TestValidPlan:
    def test_clean_plan_has_no_errors(self):
        text = plan(
            task(tid="1.1", wave="1", files="app/a.py"),
            task(tid="1.2", wave="1", files="app/b.py"),
        )
        assert cpf.check_plan(text) == []

    def test_real_repo_plan_passes(self):
        # Dogfood: an actual committed PLAN.md must validate clean.
        p = Path(__file__).resolve().parents[1] / "specs/artifact-policy/PLAN.md"
        if not p.is_file():
            pytest.skip("sample PLAN.md not present")
        assert cpf.check_plan(p.read_text(encoding="utf-8")) == []

    def test_chained_verify_is_single_command(self):
        text = plan(task(verify="alembic upgrade head && pytest tests/a.py -x"))
        assert cpf.check_plan(text) == []


# --------------------------------------------------------------------------- #
# check_plan — frontmatter violations
# --------------------------------------------------------------------------- #
class TestFrontmatterViolations:
    def test_missing_frontmatter(self):
        errors = cpf.check_plan(plan(task(), frontmatter=""))
        assert any("frontmatter" in e for e in errors)

    def test_missing_slug(self):
        fm = "---\nstatus: active\n---\n"
        errors = cpf.check_plan(plan(task(), frontmatter=fm))
        assert any("missing `slug`" in e for e in errors)

    def test_missing_status(self):
        fm = "---\nslug: demo\n---\n"
        errors = cpf.check_plan(plan(task(), frontmatter=fm))
        assert any("missing `status`" in e for e in errors)

    def test_invalid_status_value(self):
        fm = "---\nslug: demo\nstatus: wip\n---\n"
        errors = cpf.check_plan(plan(task(), frontmatter=fm))
        assert any("not in" in e for e in errors)


# --------------------------------------------------------------------------- #
# check_plan — task tag violations
# --------------------------------------------------------------------------- #
class TestTaskTagViolations:
    @pytest.mark.parametrize("tag", ["files", "action", "verify", "done"])
    def test_missing_required_tag(self, tag):
        errors = cpf.check_plan(plan(task(**{tag: None})))
        assert any(f"missing <{tag}>" in e for e in errors)

    @pytest.mark.parametrize("tag", ["files", "action", "verify", "done"])
    def test_empty_required_tag(self, tag):
        errors = cpf.check_plan(plan(task(**{tag: "   "})))
        assert any(f"empty <{tag}>" in e for e in errors)

    def test_no_tasks(self):
        errors = cpf.check_plan(FRONTMATTER + "\n## 4. Tasks\n\nNo tasks here.")
        assert any("no <task> blocks" in e for e in errors)


# --------------------------------------------------------------------------- #
# check_plan — verify must be a single command
# --------------------------------------------------------------------------- #
class TestVerifySingleCommand:
    def test_multiline_verify_rejected(self):
        # A multi-line <verify> body trips the single-command rule.
        block = (
            '```xml\n<task id="1.1" wave="1">\n'
            "  <files>app/a.py</files>\n"
            "  <action>x</action>\n"
            "  <verify>cd app\npytest tests/a.py</verify>\n"
            "  <done>ok</done>\n</task>\n```\n"
        )
        errors = cpf.check_plan(FRONTMATTER + "\n## 4. Tasks\n\n" + block)
        assert any("single shell command" in e for e in errors)


# --------------------------------------------------------------------------- #
# check_plan — same-wave file overlap
# --------------------------------------------------------------------------- #
class TestWaveFileOverlap:
    def test_overlap_in_same_wave_rejected(self):
        text = plan(
            task(tid="1.1", wave="1", files="app/shared.py"),
            task(tid="1.2", wave="1", files="app/shared.py, app/b.py"),
        )
        errors = cpf.check_plan(text)
        assert any("app/shared.py" in e and "wave 1" in e for e in errors)

    def test_same_file_different_waves_ok(self):
        text = plan(
            task(tid="1.1", wave="1", files="app/shared.py"),
            task(tid="2.1", wave="2", files="app/shared.py"),
        )
        assert cpf.check_plan(text) == []


# --------------------------------------------------------------------------- #
# main — exit codes
# --------------------------------------------------------------------------- #
class TestMain:
    def test_no_args_returns_2(self):
        assert cpf.main([]) == 2

    def test_valid_file_returns_0(self, tmp_path):
        p = tmp_path / "PLAN.md"
        p.write_text(plan(task()), encoding="utf-8")
        assert cpf.main([str(p)]) == 0

    def test_invalid_file_returns_1(self, tmp_path):
        p = tmp_path / "PLAN.md"
        p.write_text(plan(task(verify=None)), encoding="utf-8")
        assert cpf.main([str(p)]) == 1

    def test_missing_file_returns_1(self, tmp_path):
        assert cpf.main([str(tmp_path / "nope.md")]) == 1


# --------------------------------------------------------------------------- #
# story_size_warnings — advisory, never fails the lint
# --------------------------------------------------------------------------- #
class TestStorySizeWarnings:
    def test_small_task_no_warning(self):
        text = plan(task(files="app/a.py, app/b.py, app/c.py"))
        assert cpf.story_size_warnings(text) == []

    def test_oversized_task_warns(self):
        files = ", ".join(f"app/f{i}.py" for i in range(5))  # 5 > default 4
        warns = cpf.story_size_warnings(plan(task(files=files)))
        assert len(warns) == 1 and "consider splitting" in warns[0]

    def test_threshold_is_configurable(self):
        text = plan(task(files="app/a.py, app/b.py, app/c.py"))
        assert len(cpf.story_size_warnings(text, max_files=2)) == 1

    def test_warning_does_not_fail_exit_code(self, tmp_path):
        files = ", ".join(f"app/f{i}.py" for i in range(6))
        p = tmp_path / "PLAN.md"
        p.write_text(plan(task(files=files)), encoding="utf-8")
        assert cpf.main([str(p)]) == 0  # advisory only — still passes
