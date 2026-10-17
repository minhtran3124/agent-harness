import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("apply_model_config.py")
SPEC = importlib.util.spec_from_file_location("apply_model_config", SCRIPT)
assert SPEC and SPEC.loader
applier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(applier)
ROOT = SCRIPT.parents[1]

# Fixture files mirror the deployed shapes: reviewer has `tools`, coding has none,
# a skill has `allowed-tools` and no model/effort.
CODING = (
    "---\n"
    "name: coding\n"
    'description: "Write code."\n'
    "model: claude-opus-5-5\n"
    "effort: medium\n"
    "color: orange\n"
    "---\n"
    "\n"
    "# Coding\n"
    "model: not frontmatter\n"
)
REVIEWER = (
    "---\n"
    "name: reviewer\n"
    'description: "Review."\n'
    "tools: Glob, Grep, Read, Bash\n"
    "model: claude-opus-5-5\n"
    "effort: medium\n"
    "---\n"
    "\n"
    "# Reviewer\n"
)
TASK_REVIEWER = REVIEWER.replace("name: reviewer", "name: task-reviewer")
TEST_RUNNER = (
    "---\n"
    "name: test-runner\n"
    'description: "Run tests."\n'
    "tools: Glob, Grep, Read, Bash\n"
    "model: claude-haiku-5-5\n"
    "---\n"
    "\n"
    "# Test runner\n"
)
SKILL = (
    "---\n"
    "name: correctness-review\n"
    'description: "Hunt for bugs."\n'
    "allowed-tools: Read, Grep\n"
    "---\n"
    "\n"
    "# Review\n"
)
CONSUMER_SKILL = (
    '---\nname: my-skill\ndescription: "Mine."\nmodel: sonnet\n---\n\n# Mine\n'
)
SNAPSHOT = {
    "schema_version": 1,
    "agents": {
        "coding": {"model": "claude-opus-5-5", "effort": "medium"},
        "reviewer": {"model": "claude-opus-5-5", "effort": "medium"},
        "task-reviewer": {"model": "claude-opus-5-5", "effort": "medium"},
        "test-runner": {"model": "claude-haiku-5-5"},
    },
    "skills": {"correctness-review": {}, "xia2": {}},
}
ENV_VARS = (
    "CLAUDE_CODE_EFFORT_LEVEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL_FORCE",
)


@pytest.fixture
def tree(tmp_path, monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    claude = tmp_path / ".claude"
    files = {
        "agents/coding.md": CODING,
        "agents/reviewer.md": REVIEWER,
        "agents/task-reviewer.md": TASK_REVIEWER,
        "agents/test-runner.md": TEST_RUNNER,
        "skills/correctness-review/SKILL.md": SKILL,
        "skills/xia2/SKILL.md": SKILL.replace("correctness-review", "xia2"),
        "skills/my-skill/SKILL.md": CONSUMER_SKILL,
    }
    for rel, text in files.items():
        path = claude / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    (claude / "harness-models.defaults.json").write_text(json.dumps(SNAPSHOT))
    return tmp_path


def user_file(root, data):
    path = root / "harness-models.json"
    path.write_text(data if isinstance(data, str) else json.dumps(data))


def run(root, *mode, stdin=None, monkeypatch=None):
    if stdin is not None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    return applier.main([*mode, "--project-root", str(root)])


def digests(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def hook_input(source):
    return json.dumps({"hook_event_name": "SessionStart", "source": source})


def read(root, rel):
    return (root / ".claude" / rel).read_text()


# SC-2
def test_agent_override_changes_one_line(tree, capsys):
    user_file(tree, {"agents": {"coding": {"effort": "high"}}})
    assert run(tree, "--apply") == 0
    assert read(tree, "agents/coding.md") == CODING.replace(
        "effort: medium\n", "effort: high\n"
    )
    out = capsys.readouterr().out
    assert "1 file(s) written" in out
    assert "next invocation" in out and "next session" in out


def test_agent_override_on_real_deployed_coding(tmp_path, capsys):
    real = ROOT / ".claude/agents/coding.md"
    if not real.is_file():
        pytest.skip("no deployed .claude/agents/coding.md")
    claude = tmp_path / ".claude"
    (claude / "agents").mkdir(parents=True)
    shutil.copy(real, claude / "agents/coding.md")
    before = real.read_text().splitlines()
    (claude / "harness-models.defaults.json").write_text(
        json.dumps({"agents": {"coding": {"model": "claude-opus-5-5"}}, "skills": {}})
    )
    user_file(tmp_path, {"agents": {"coding": {"effort": "high"}}})
    assert run(tmp_path, "--apply") == 0
    after = (claude / "agents/coding.md").read_text().splitlines()
    changed = [(a, b) for a, b in zip(before, after) if a != b]
    assert len(before) == len(after)
    assert changed == [("effort: medium", "effort: high")]


# SC-3
INVALID_CASES = {
    "json": ("{not json", 1),
    "top_key": ({"agent": {}}, 1),
    "role": ({"agents": {"planner": {"effort": "high"}}}, 1),
    "skill": ({"skills": {"nope": {"effort": "high"}}}, 1),
    "entry_not_object": ({"agents": {"coding": "high"}}, 1),
    "entry_key": ({"agents": {"coding": {"efort": "high"}}}, 1),
    "non_string": ({"agents": {"coding": {"effort": 3}}}, 1),
    "null": ({"agents": {"coding": {"model": None}}}, 1),
    "model": ({"agents": {"coding": {"model": "gpt-5"}}}, 1),
    "effort": ({"agents": {"coding": {"effort": "ultra"}}}, 1),
    "schema_version": ({"schema_version": 2}, 1),
    "schema_version_bool": ({"schema_version": True}, 1),
    "two_errors": ({"agents": {"coding": {"effort": "ultra", "model": "x"}}}, 2),
}


@pytest.mark.parametrize("mode", ["--check", "--apply"])
@pytest.mark.parametrize("case", sorted(INVALID_CASES))
def test_invalid_file_exits_1_and_writes_nothing(tree, capsys, mode, case):
    data, error_count = INVALID_CASES[case]
    user_file(tree, data)
    before = digests(tree)
    assert run(tree, mode) == 1
    lines = capsys.readouterr().out.splitlines()
    assert len([line for line in lines if line.startswith("error: ")]) == error_count
    assert digests(tree) == before


def test_invalid_file_show_prints_errors_and_exits_1(tree, capsys):
    user_file(tree, {"agents": {"coding": {"effort": "ultra"}}})
    assert run(tree, "--show") == 1
    assert "error: " in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["--show", "--check", "--apply"])
@pytest.mark.parametrize("snapshot", ["missing", "unreadable"])
def test_invalid_snapshot_exits_1(tree, capsys, mode, snapshot):
    path = tree / ".claude/harness-models.defaults.json"
    if snapshot == "missing":
        path.unlink()
    else:
        path.write_text("{broken")
    before = digests(tree)
    assert run(tree, mode) == 1
    assert "error: " in capsys.readouterr().out
    assert digests(tree) == before


def test_invalid_file_hook_exits_0_with_warning(tree, capsys, monkeypatch):
    user_file(tree, {"agents": {"coding": {"effort": "ultra"}}})
    before = digests(tree)
    assert (
        run(tree, "--hook", stdin=hook_input("startup"), monkeypatch=monkeypatch) == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert (
        "last applied values stay" in payload["hookSpecificOutput"]["additionalContext"]
    )
    assert digests(tree) == before


# SC-4
@pytest.mark.parametrize("role", ["reviewer", "task-reviewer"])
def test_floor_rejects_low_review_effort(tree, capsys, role):
    user_file(tree, {"agents": {role: {"effort": "low"}}})
    assert run(tree, "--check") == 1
    assert role in capsys.readouterr().out


def test_floor_allows_medium_and_low_for_other_roles(tree):
    user_file(
        tree,
        {"agents": {"reviewer": {"effort": "medium"}, "coding": {"effort": "low"}}},
    )
    assert run(tree, "--check") == 0


# SC-5
def test_idempotent_second_apply_writes_nothing(tree, capsys):
    user_file(
        tree,
        {
            "agents": {"coding": {"effort": "high"}, "test-runner": {"effort": "low"}},
            "skills": {"xia2": {"model": "inherit"}},
        },
    )
    assert run(tree, "--apply") == 0
    assert "3 file(s) written" in capsys.readouterr().out
    before = digests(tree)
    assert run(tree, "--apply") == 0
    assert "0 file(s) written" in capsys.readouterr().out
    assert digests(tree) == before


# SC-6
def test_show_rows_and_source(tree, capsys):
    user_file(
        tree,
        {
            "agents": {"coding": {"effort": "high"}},
            "skills": {"xia2": {"effort": "max"}},
        },
    )
    before = digests(tree)
    assert run(tree) == 0  # --show is the default
    lines = capsys.readouterr().out.splitlines()
    rows = [line.split() for line in lines[1:]]
    assert rows == [
        ["agents/coding.md", "claude-opus-5-5", "high", "harness-models.json"],
        ["agents/reviewer.md", "claude-opus-5-5", "medium", "default"],
        ["agents/task-reviewer.md", "claude-opus-5-5", "medium", "default"],
        ["agents/test-runner.md", "claude-haiku-5-5", "-", "default"],
        ["skills/xia2/SKILL.md", "-", "max", "harness-models.json"],
    ]
    assert lines[0].split() == ["target", "model", "effort", "source"]
    assert digests(tree) == before


def test_show_warns_per_set_env_var(tree, capsys, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_EFFORT_LEVEL", "high")
    monkeypatch.setenv("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "1")
    assert run(tree, "--show") == 0
    warnings = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("warning: ")
    ]
    assert len(warnings) == 2
    assert "CLAUDE_CODE_EFFORT_LEVEL" in warnings[0]
    assert "CLAUDE_CODE_SUBAGENT_MODEL_FORCE" in warnings[1]


# SC-7
def test_main_session_boundary_settings_unchanged(tree, monkeypatch):
    settings = {
        tree / ".claude/settings.json": '{"model": "opus", "effortLevel": "low"}\n',
        tree / ".claude/settings.local.json": '{"model": "haiku"}\n',
        tree / "settings.json": '{"hooks": {}}\n',
        tree / "settings.local.json": "{}\n",
    }
    for path, text in settings.items():
        path.write_text(text)
    user_file(
        tree,
        {
            "agents": {"coding": {"model": "sonnet"}},
            "skills": {"xia2": {"effort": "high"}},
        },
    )
    assert run(tree, "--apply") == 0
    user_file(tree, {"agents": {"coding": {"model": "haiku"}}})
    assert (
        run(tree, "--hook", stdin=hook_input("startup"), monkeypatch=monkeypatch) == 0
    )
    assert "model: haiku\n" in read(tree, "agents/coding.md")
    for path, text in settings.items():
        assert path.read_text() == text


# SC-8
def test_skill_line_insert_and_remove_restores_bytes(tree, capsys):
    original = (tree / ".claude/skills/correctness-review/SKILL.md").read_bytes()
    user_file(tree, {"skills": {"correctness-review": {"effort": "high"}}})
    assert run(tree, "--apply") == 0
    assert read(tree, "skills/correctness-review/SKILL.md") == SKILL.replace(
        'description: "Hunt for bugs."\n',
        'description: "Hunt for bugs."\neffort: high\n',
    )
    user_file(tree, {})
    assert run(tree, "--apply") == 0
    assert (
        tree / ".claude/skills/correctness-review/SKILL.md"
    ).read_bytes() == original


def test_skill_line_on_real_deployed_skill(tmp_path):
    real = ROOT / ".claude/skills/correctness-review/SKILL.md"
    if not real.is_file():
        pytest.skip("no deployed correctness-review skill")
    target = tmp_path / ".claude/skills/correctness-review/SKILL.md"
    target.parent.mkdir(parents=True)
    shutil.copy(real, target)
    (tmp_path / ".claude/harness-models.defaults.json").write_text(
        json.dumps({"agents": {}, "skills": {"correctness-review": {}}})
    )
    user_file(
        tmp_path,
        {"skills": {"correctness-review": {"model": "inherit", "effort": "high"}}},
    )
    assert applier.main(["--apply", "--project-root", str(tmp_path)]) == 0
    lines = target.read_text().splitlines()
    end = lines.index("---", 1)
    frontmatter = lines[1:end]
    desc = next(
        i for i, line in enumerate(frontmatter) if line.startswith("description:")
    )
    assert frontmatter[desc + 1 : desc + 3] == ["model: inherit", "effort: high"]
    user_file(tmp_path, {})
    assert applier.main(["--apply", "--project-root", str(tmp_path)]) == 0
    assert target.read_bytes() == real.read_bytes()


# SC-9
def test_consumer_skill_untouched_and_rejected(tree, capsys, monkeypatch):
    consumer = tree / ".claude/skills/my-skill/SKILL.md"
    original = consumer.read_bytes()
    user_file(tree, {"skills": {"xia2": {"effort": "high"}}})
    assert run(tree, "--apply") == 0
    assert run(tree, "--hook", stdin=hook_input("clear"), monkeypatch=monkeypatch) == 0
    assert consumer.read_bytes() == original
    user_file(tree, {"skills": {"my-skill": {"effort": "high"}}})
    capsys.readouterr()
    assert run(tree, "--check") == 1
    assert "my-skill" in capsys.readouterr().out
    assert consumer.read_bytes() == original


# SC-10
REAL_WRITE = applier.write_atomic


def failing_on(n, monkeypatch):
    real = applier.write_atomic
    calls = []

    def fake(path, text):
        calls.append(path)
        if len(calls) == n:
            raise OSError("disk full")
        real(path, text)

    monkeypatch.setattr(applier, "write_atomic", fake)


PARTIAL = {
    "agents": {
        "coding": {"effort": "high"},
        "reviewer": {"effort": "high"},
        "test-runner": {"effort": "low"},
    }
}


def test_partial_write_apply_reports_and_exits_1(tree, capsys, monkeypatch):
    user_file(tree, PARTIAL)
    failing_on(2, monkeypatch)
    assert run(tree, "--apply") == 1
    out = capsys.readouterr().out
    assert "wrote agents/coding.md" in out
    assert "failed agents/reviewer.md" in out
    assert "effort: high\n" in read(tree, "agents/coding.md")
    assert read(tree, "agents/reviewer.md") == REVIEWER
    assert read(tree, "agents/test-runner.md") == TEST_RUNNER
    monkeypatch.undo()
    assert run(tree, "--apply") == 0
    assert "2 file(s) written" in capsys.readouterr().out
    assert "effort: high\n" in read(tree, "agents/reviewer.md")
    assert "effort: low\n" in read(tree, "agents/test-runner.md")


def test_partial_write_hook_warns_and_converges(tree, capsys, monkeypatch):
    user_file(tree, PARTIAL)
    failing_on(2, monkeypatch)
    assert (
        run(tree, "--hook", stdin=hook_input("startup"), monkeypatch=monkeypatch) == 0
    )
    context = json.loads(capsys.readouterr().out)["hookSpecificOutput"][
        "additionalContext"
    ]
    assert "partial" in context and "/harness-models apply" in context
    monkeypatch.setattr(applier, "write_atomic", REAL_WRITE)
    assert (
        run(tree, "--hook", stdin=hook_input("startup"), monkeypatch=monkeypatch) == 0
    )
    assert "2 file" in capsys.readouterr().out
    assert run(tree, "--apply") == 0
    assert "0 file(s) written" in capsys.readouterr().out


# Hook mode
@pytest.mark.parametrize("source", ["resume", "compact", "fork", None])
def test_hook_other_sources_are_silent(tree, capsys, monkeypatch, source):
    user_file(tree, {"agents": {"coding": {"effort": "high"}}})
    before = digests(tree)
    stdin = hook_input(source) if source else "not json"
    assert run(tree, "--hook", stdin=stdin, monkeypatch=monkeypatch) == 0
    assert capsys.readouterr().out == ""
    assert digests(tree) == before


def test_hook_event_name_and_reload_skills(tree, capsys, monkeypatch):
    user_file(tree, {"agents": {"coding": {"effort": "high"}}})
    assert (
        run(tree, "--hook", stdin=hook_input("startup"), monkeypatch=monkeypatch) == 0
    )
    output = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert output["hookEventName"] == "SessionStart"
    assert "1 file" in output["additionalContext"]
    assert "reloadSkills" not in output
    user_file(tree, {"skills": {"xia2": {"effort": "high"}}})
    assert run(tree, "--hook", stdin=hook_input("clear"), monkeypatch=monkeypatch) == 0
    output = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert output["reloadSkills"] is True
    assert (
        run(tree, "--hook", stdin=hook_input("startup"), monkeypatch=monkeypatch) == 0
    )
    assert capsys.readouterr().out == ""


def test_hook_missing_snapshot_is_silent(tree, capsys, monkeypatch):
    (tree / ".claude/harness-models.defaults.json").unlink()
    user_file(tree, {"agents": {"coding": {"effort": "ultra"}}})
    assert (
        run(tree, "--hook", stdin=hook_input("startup"), monkeypatch=monkeypatch) == 0
    )
    assert capsys.readouterr().out == ""


def test_missing_target_is_reported_and_skipped(tree, capsys, monkeypatch):
    (tree / ".claude/agents/test-runner.md").unlink()
    user_file(tree, {"agents": {"coding": {"effort": "high"}}})
    assert run(tree, "--apply") == 0
    assert "missing target agents/test-runner.md" in capsys.readouterr().out
    user_file(tree, {"agents": {"coding": {"effort": "max"}}})
    assert (
        run(tree, "--hook", stdin=hook_input("startup"), monkeypatch=monkeypatch) == 0
    )
    assert "missing target" not in capsys.readouterr().out


def test_no_user_file_applies_defaults_only(tree, capsys):
    before = digests(tree)
    assert run(tree, "--apply") == 0
    assert "0 file(s) written" in capsys.readouterr().out
    assert digests(tree) == before


def test_cli_entry_point_with_explicit_paths(tree):
    defaults = tree / "snap.json"
    defaults.write_text(json.dumps(SNAPSHOT))
    user_file(tree, {"agents": {"coding": {"effort": "high"}}})
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--check",
            "--project-root",
            str(tree),
            "--claude-dir",
            str(tree / ".claude"),
            "--defaults",
            str(defaults),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
