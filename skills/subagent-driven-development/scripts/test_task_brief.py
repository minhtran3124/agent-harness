import importlib.util
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("task_brief.py")
SPEC = importlib.util.spec_from_file_location("task_brief", SCRIPT)
assert SPEC and SPEC.loader
task_brief = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(task_brief)


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _make_plan_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "T")
    _git(repo, "config", "user.email", "t@example.invalid")
    plan_dir = repo / "specs" / "demo"
    plan_dir.mkdir(parents=True)
    (plan_dir / "PLAN.md").write_text(
        "## Global Constraints\n\n- Do not break anything.\n\n## 4. Tasks\n",
        encoding="utf-8",
    )
    (repo / "f.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo, plan_dir / "PLAN.md"


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


def test_delta_description_brief_carries_the_plans_global_constraints(tmp_path):
    repo, plan = _make_plan_repo(tmp_path)
    output = tmp_path / "brief.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--plan",
            str(plan),
            "--delta-description",
            "simplify-stage cleanup delta",
            "--output",
            str(output),
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    content = output.read_text(encoding="utf-8")
    assert "Do not break anything." in content
    assert "simplify-stage cleanup delta" in content


def test_delta_description_reflects_a_changed_plan_not_a_hardcoded_string(tmp_path):
    repo, plan = _make_plan_repo(tmp_path)
    plan.write_text(
        "## Global Constraints\n\n- A different constraint entirely.\n\n## 4. Tasks\n",
        encoding="utf-8",
    )
    output = tmp_path / "brief.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--plan",
            str(plan),
            "--delta-description",
            "x",
            "--output",
            str(output),
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    content = output.read_text(encoding="utf-8")
    assert "A different constraint entirely." in content
    assert "Do not break anything." not in content


def test_task_and_delta_description_are_mutually_exclusive(tmp_path):
    repo, plan = _make_plan_repo(tmp_path)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--plan", str(plan)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "exactly one of --task or --delta-description" in completed.stderr

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--plan",
            str(plan),
            "--task",
            "1.1",
            "--delta-description",
            "x",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "exactly one of --task or --delta-description" in completed.stderr
