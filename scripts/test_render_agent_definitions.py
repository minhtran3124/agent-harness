import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("render_agent_definitions.py")
SPEC = importlib.util.spec_from_file_location("render_agent_definitions", SCRIPT)
assert SPEC and SPEC.loader
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)
ROOT = SCRIPT.parents[1]

LEGACY_CLAUDE = {
    "implementer": {"model": "claude-sonnet-5-5", "effort": "medium", "tools": None},
    "reviewer": {
        "model": "claude-opus-5-5",
        "effort": "medium",
        "tools": ["Glob", "Grep", "Read", "Bash"],
    },
    "task-reviewer": {
        "model": "claude-opus-5-5",
        "effort": "medium",
        "tools": ["Glob", "Grep", "Read"],
    },
    "test-runner": {
        "model": "claude-haiku-5-5",
        "tools": [
            "Glob",
            "Grep",
            "Read",
            "WebFetch",
            "WebSearch",
            "Bash",
        ],
    },
    "researcher": {
        "model": "claude-haiku-5-5",
        "tools": ["Glob", "Grep", "Read", "Bash", "WebFetch", "WebSearch"],
    },
    "advisor": {
        "model": "claude-opus-5-5",
        "effort": "high",
        "tools": ["Glob", "Grep", "Read"],
    },
    "intent-reviewer": {
        "model": "claude-sonnet-5-5",
        "effort": "medium",
        "tools": ["Glob", "Grep", "Read", "Bash"],
    },
}

# Substance that must survive any rewording of a role document. `rendered_body ==
# source_body` cannot catch a deletion here — both sides move together — so these are
# asserted against the rendered artifact directly. Tokens are chosen to be wording-
# tolerant but deletion-intolerant: they name the *claim*, not a sentence.
LOAD_BEARING_SUBSTANCE = {
    "reviewer": {
        "description": [
            # Independence is enforced by the harness, not by asking the model nicely.
            "structurally read-only",
            "not by instruction",
        ],
        "body": [
            # The negative scope: the shell channel is NOT structurally guarded.
            "Acknowledged limitation",
            "never fix",
            "structural, not a promise",
        ],
    },
    "task-reviewer": {
        "description": ["cannot write, edit, spawn agents"],
        "body": [],
    },
}


def clone_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "agents").mkdir(parents=True)
    for path in (ROOT / "agents").iterdir():
        if path.suffix in {".md", ".json"}:
            (root / "agents" / path.name).write_bytes(path.read_bytes())
    return root


def test_contracts_and_runtime_bindings_are_total():
    contracts, bindings = renderer.validate(ROOT)
    required = set(contracts["required_capabilities"])
    for runtime in ("claude",):
        assert set(bindings["runtimes"][runtime]["roles"]) == set(contracts["roles"])
        for binding in bindings["runtimes"][runtime]["roles"].values():
            assert set(binding["capabilities"]) == required


def test_semantic_sources_have_no_vendor_policy_fields():
    for role in LEGACY_CLAUDE:
        frontmatter, _ = renderer.split_frontmatter(ROOT / f"agents/{role}.md")
        keys = {line.split(":", 1)[0] for line in frontmatter if ":" in line}
        assert not (keys & renderer.FORBIDDEN_SOURCE_FIELDS)


def test_claude_render_preserves_legacy_model_tools_and_role_body(tmp_path):
    out = tmp_path / "agents"
    renderer.render_claude(ROOT, out)
    for role, expected in LEGACY_CLAUDE.items():
        text = (out / f"{role}.md").read_text()
        _, source_body = renderer.split_frontmatter(ROOT / f"agents/{role}.md")
        _, rendered_body = renderer.split_frontmatter(
            out / f"{role}.md", allow_runtime_fields=True
        )
        assert rendered_body == source_body
        assert f"model: {expected['model']}" in text
        if "effort" in expected:
            assert f"\neffort: {expected['effort']}\n" in text
        else:
            assert "\neffort:" not in text
        if expected["tools"] is None:
            assert "\ntools:" not in text
        else:
            assert f"\ntools: {', '.join(expected['tools'])}\n" in text


def test_rendered_roles_retain_load_bearing_substance(tmp_path):
    """Guard the claims a role document exists to make.

    `test_claude_render_preserves_legacy_model_tools_and_role_body` compares the
    rendered body against the *current* source, so deleting a sentence from both keeps
    it green. These tokens pin the substance itself — notably the reviewer's
    acknowledged limitation, which states that the inspection shell is NOT covered by
    the structural guarantee. Losing it silently upgrades a contract-tier promise to a
    structural one.
    """
    out = tmp_path / "agents"
    renderer.render_claude(ROOT, out)
    for role, sections in LOAD_BEARING_SUBSTANCE.items():
        text = (out / f"{role}.md").read_text()
        frontmatter, body = renderer.split_frontmatter(
            out / f"{role}.md", allow_runtime_fields=True
        )
        description = "\n".join(
            line for line in frontmatter if line.startswith("description:")
        )
        assert description, role
        for token in sections["description"]:
            assert token in description, (role, "description", token)
        for token in sections["body"]:
            assert token in body, (role, "body", token)
        assert text  # rendered file is non-empty


def test_reviewer_profiles_are_read_only_no_nesting_no_mcp_and_fresh_bounded():
    contracts, _ = renderer.validate(ROOT)
    for role in renderer.REVIEW_ROLES:
        contract = contracts["roles"][role]
        assert contract["filesystem"] == "read-only"
        assert contract["nested_delegation"] is False
        assert contract["mcp"] == "none"
        assert contract["context_policy"] == "fresh-bounded"


def test_missing_runtime_role_is_rejected(tmp_path):
    root = clone_root(tmp_path)
    path = root / "agents/runtime-bindings.json"
    data = json.loads(path.read_text())
    del data["runtimes"]["claude"]["roles"]["reviewer"]
    path.write_text(json.dumps(data))
    with pytest.raises(renderer.ContractError, match="role set"):
        renderer.validate(root)


def test_missing_capability_mapping_is_rejected(tmp_path):
    root = clone_root(tmp_path)
    path = root / "agents/runtime-bindings.json"
    data = json.loads(path.read_text())
    del data["runtimes"]["claude"]["roles"]["reviewer"]["capabilities"]["mcp"]
    path.write_text(json.dumps(data))
    with pytest.raises(renderer.ContractError, match="capability mapping"):
        renderer.validate(root)


@pytest.mark.parametrize("role", ["reviewer", "task-reviewer", "test-runner", "researcher", "advisor", "intent-reviewer"])
def test_mcp_tool_on_mcp_none_role_is_rejected(tmp_path, role):
    root = clone_root(tmp_path)
    path = root / "agents/runtime-bindings.json"
    data = json.loads(path.read_text())
    data["runtimes"]["claude"]["roles"][role]["tools"].append("mcp__docs__query")
    path.write_text(json.dumps(data))
    with pytest.raises(renderer.ContractError, match="mcp none"):
        renderer.validate(root)


@pytest.mark.parametrize(
    "tools", [[], ["Read", 5], ["Read", None], ["Read, mcp__docs__query"], [" Read"]]
)
def test_malformed_tools_list_on_mcp_none_role_is_rejected(tmp_path, tools):
    root = clone_root(tmp_path)
    path = root / "agents/runtime-bindings.json"
    data = json.loads(path.read_text())
    data["runtimes"]["claude"]["roles"]["test-runner"]["tools"] = tools
    path.write_text(json.dumps(data))
    with pytest.raises(renderer.ContractError, match="mcp none"):
        renderer.validate(root)


def test_missing_tools_list_on_mcp_none_role_is_rejected(tmp_path):
    root = clone_root(tmp_path)
    path = root / "agents/runtime-bindings.json"
    data = json.loads(path.read_text())
    del data["runtimes"]["claude"]["roles"]["test-runner"]["tools"]
    path.write_text(json.dumps(data))
    with pytest.raises(renderer.ContractError, match="mcp none"):
        renderer.validate(root)


def test_vendor_field_in_semantic_source_is_rejected(tmp_path):
    root = clone_root(tmp_path)
    path = root / "agents/reviewer.md"
    path.write_text(path.read_text().replace("---\n", "---\nmodel: vendor-x\n", 1))
    with pytest.raises(renderer.ContractError, match="runtime policy field"):
        renderer.validate(root)


def test_unsupported_claude_effort_is_rejected(tmp_path):
    root = clone_root(tmp_path)
    path = root / "agents/runtime-bindings.json"
    data = json.loads(path.read_text())
    data["runtimes"]["claude"]["roles"]["reviewer"]["effort"] = "ultra"
    path.write_text(json.dumps(data))
    with pytest.raises(renderer.ContractError, match="unsupported effort"):
        renderer.validate(root)


def test_effort_in_semantic_source_is_rejected(tmp_path):
    root = clone_root(tmp_path)
    path = root / "agents/reviewer.md"
    path.write_text(path.read_text().replace("---\n", "---\neffort: high\n", 1))
    with pytest.raises(renderer.ContractError, match="runtime policy field"):
        renderer.validate(root)


def run_main(monkeypatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["render_agent_definitions.py", *map(str, args)])
    return renderer.main()


def write_skill(root: Path, name: str, extra: str = "") -> None:
    path = root / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"---\nname: {name}\ndescription: x\n{extra}---\n\n# {name}\n")


def test_defaults_out_snapshot_matches_claude_bindings_and_source_skills(
    tmp_path, monkeypatch
):
    out = tmp_path / "defaults.json"
    assert run_main(monkeypatch, "--root", ROOT, "--defaults-out", out) == 0
    text = out.read_text()
    snapshot = json.loads(text)
    expected_agents = {
        role: {k: v for k, v in spec.items() if k in ("model", "effort")}
        for role, spec in LEGACY_CLAUDE.items()
    }
    assert snapshot["schema_version"] == 1
    assert snapshot["agents"] == expected_agents
    source_skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    assert {"xia2", "feature-intake", "intent-review"} <= source_skills
    assert snapshot["skills"] == {name: {} for name in source_skills}
    assert set(snapshot) == {"schema_version", "agents", "skills"}
    assert text == json.dumps(snapshot, indent=2, sort_keys=True) + "\n"


def test_defaults_out_skills_skip_archive_and_carry_frontmatter_values(
    tmp_path, monkeypatch
):
    root = clone_root(tmp_path)
    write_skill(root, "plain")
    write_skill(root, "tuned", "model: claude-sonnet-5-5\neffort: high\n")
    write_skill(root, "_archive")
    (root / "skills/_archive/old").mkdir()
    (root / "skills/_archive/old/SKILL.md").write_text("---\nname: old\n---\n")
    out = tmp_path / "defaults.json"
    assert run_main(monkeypatch, "--root", root, "--defaults-out", out) == 0
    assert json.loads(out.read_text())["skills"] == {
        "plain": {},
        "tuned": {"model": "claude-sonnet-5-5", "effort": "high"},
    }


def test_defaults_out_with_output_dir_keeps_render_bytes(tmp_path, monkeypatch):
    baseline = tmp_path / "baseline"
    assert run_main(monkeypatch, "--root", ROOT, "--output-dir", baseline) == 0
    rendered = tmp_path / "rendered"
    out = tmp_path / "defaults.json"
    assert (
        run_main(
            monkeypatch,
            "--root",
            ROOT,
            "--output-dir",
            rendered,
            "--defaults-out",
            out,
        )
        == 0
    )
    names = sorted(path.name for path in baseline.iterdir())
    assert names == sorted(path.name for path in rendered.iterdir())
    for name in names:
        assert (rendered / name).read_bytes() == (baseline / name).read_bytes()
    assert json.loads(out.read_text())["agents"]["test-runner"] == {
        "model": "claude-haiku-5-5"
    }


def test_defaults_out_rejects_check(tmp_path, monkeypatch):
    out = tmp_path / "defaults.json"
    assert (
        run_main(monkeypatch, "--root", ROOT, "--defaults-out", out, "--check") == 1
    )
    assert not out.exists()


def test_incomplete_unsupported_exception_is_rejected(tmp_path):
    root = clone_root(tmp_path)
    path = root / "agents/runtime-bindings.json"
    data = json.loads(path.read_text())
    value = data["runtimes"]["claude"]["roles"]["test-runner"]["capabilities"]
    value["mcp"] = {"status": "unsupported-exception"}
    path.write_text(json.dumps(data))
    with pytest.raises(renderer.ContractError, match="incomplete unsupported"):
        renderer.validate(root)
