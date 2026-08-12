import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("check_runtime_neutral_sources.py")
SPEC = importlib.util.spec_from_file_location(
    "check_runtime_neutral_sources", MODULE_PATH
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
validate = MODULE.validate


def write_fixture(tmp_path, *, text="Invoke /demo.\n", findings=None):
    (tmp_path / "skills/demo").mkdir(parents=True)
    (tmp_path / "skills/demo/SKILL.md").write_text(text)
    (tmp_path / "specs/codex-support").mkdir(parents=True)
    payload = {
        "schema_version": 1,
        "scan_roots": ["skills"],
        "skill_names": ["demo"],
        "findings": findings
        if findings is not None
        else [
            {
                "path": "skills/demo/SKILL.md",
                "category": "slash-skill-invocation",
                "classification": "shared-source-violation",
                "count": 1,
                "owner": "phase-3",
                "exit_condition": "Replace invocation prose.",
            }
        ],
    }
    (tmp_path / MODULE.INVENTORY).write_text(json.dumps(payload))


def test_declared_finding_passes(tmp_path):
    write_fixture(tmp_path)
    assert validate(tmp_path) == []


def test_unowned_new_finding_reports_line_and_category(tmp_path):
    write_fixture(tmp_path, findings=[])
    errors = validate(tmp_path)
    assert any("observed 1" in error for error in errors)
    assert any("SKILL.md:1 [slash-skill-invocation]" in error for error in errors)


def test_stale_inventory_entry_is_rejected(tmp_path):
    write_fixture(tmp_path, text="Invoke the demo skill.\n")
    assert any("declared 1, observed 0" in error for error in validate(tmp_path))


def test_escaped_invocation_is_not_a_finding(tmp_path):
    write_fixture(tmp_path, text=r"Document \/demo literally." + "\n", findings=[])
    assert validate(tmp_path) == []


def test_repository_path_is_not_invocation(tmp_path):
    write_fixture(tmp_path, text="Read skills/demo/SKILL.md.\n", findings=[])
    assert validate(tmp_path) == []


def test_deployed_rule_path_is_detected(tmp_path):
    finding = {
        "path": "skills/demo/SKILL.md",
        "category": "deployed-rule-path",
        "classification": "shared-source-violation",
        "count": 1,
        "owner": "phase-3",
        "exit_condition": "Use rules/demo.md.",
    }
    write_fixture(tmp_path, text="Read .claude/rules/demo.md.\n", findings=[finding])
    assert validate(tmp_path) == []


def test_deployed_skill_path_is_detected(tmp_path):
    finding = {
        "path": "skills/demo/SKILL.md",
        "category": "deployed-skill-path",
        "classification": "shared-source-violation",
        "count": 1,
        "owner": "phase-3",
        "exit_condition": "Use a repository-root skill path.",
    }
    write_fixture(
        tmp_path, text="Run .claude/skills/demo/tool.py.\n", findings=[finding]
    )
    assert validate(tmp_path) == []


def test_vendor_policy_is_only_frontmatter_in_agents(tmp_path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents/reviewer.md").write_text(
        "---\nmodel: vendor-model\ntools: Read\n---\nMention model: in prose.\n"
    )
    (tmp_path / "specs/codex-support").mkdir(parents=True)
    findings = [
        {
            "path": "agents/reviewer.md",
            "category": "vendor-agent-policy",
            "classification": "shared-source-violation",
            "count": 2,
            "owner": "phase-3",
            "exit_condition": "Move fields to runtime bindings.",
        }
    ]
    (tmp_path / MODULE.INVENTORY).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "scan_roots": ["agents"],
                "skill_names": ["demo"],
                "findings": findings,
            }
        )
    )
    assert validate(tmp_path) == []


def test_vendor_model_label_in_shared_prose_is_detected(tmp_path):
    finding = {
        "path": "skills/demo/SKILL.md",
        "category": "vendor-agent-policy",
        "classification": "shared-source-violation",
        "count": 1,
        "owner": "phase-5",
        "exit_condition": "Resolve the label through the runtime binding.",
    }
    write_fixture(
        tmp_path,
        text="Use claude-opus-example for this shared stage.\n",
        findings=[finding],
    )
    assert validate(tmp_path) == []


def test_exception_requires_owner_and_exit_condition(tmp_path):
    finding = {
        "path": "skills/demo/SKILL.md",
        "category": "slash-skill-invocation",
        "classification": "runtime-entry-binding",
        "count": 1,
        "owner": "",
        "exit_condition": "",
    }
    write_fixture(tmp_path, findings=[finding])
    errors = validate(tmp_path)
    assert any("owner" in error for error in errors)
    assert any("exit_condition" in error for error in errors)


def test_duplicate_inventory_entry_is_rejected(tmp_path):
    finding = {
        "path": "skills/demo/SKILL.md",
        "category": "slash-skill-invocation",
        "classification": "test-fixture",
        "count": 1,
        "owner": "tests",
        "exit_condition": "Retain literal fixture coverage.",
    }
    write_fixture(tmp_path, findings=[finding, finding])
    assert any("duplicate" in error for error in validate(tmp_path))
