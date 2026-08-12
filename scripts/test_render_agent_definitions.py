import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("render_agent_definitions.py")
SPEC = importlib.util.spec_from_file_location("render_agent_definitions", SCRIPT)
assert SPEC and SPEC.loader
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)
ROOT = SCRIPT.parents[1]

LEGACY_CLAUDE = {
    "coding": {"model": "claude-opus-4-8", "tools": None},
    "reviewer": {
        "model": "claude-opus-5",
        "tools": ["Glob", "Grep", "Read", "Bash"],
    },
    "task-reviewer": {
        "model": "claude-opus-5",
        "tools": ["Glob", "Grep", "Read"],
    },
    "test-runner": {
        "model": "claude-haiku-4-5-20251001",
        "tools": [
            "Glob",
            "Grep",
            "Read",
            "WebFetch",
            "WebSearch",
            "Bash",
            "mcp__context7__resolve-library-id",
            "mcp__context7__query-docs",
        ],
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
            # Model-class isolation, including the scorer's distinct model.
            "distinct",
            "ensemble-diversity",
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


def test_contracts_and_both_runtime_bindings_are_total():
    contracts, bindings = renderer.validate(ROOT)
    required = set(contracts["required_capabilities"])
    for runtime in ("claude", "codex"):
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
        if expected["tools"] is None:
            assert "\ntools:" not in text
        else:
            assert f"tools: {', '.join(expected['tools'])}" in text


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


def test_codex_render_emits_strict_profiles_and_explicit_policy(tmp_path):
    out = tmp_path / "agents"
    written = renderer.render_codex(ROOT, out)
    assert [path.name for path in written] == [
        "coding.toml",
        "reviewer.toml",
        "task-reviewer.toml",
        "test-runner.toml",
    ]

    required_capabilities = (
        "filesystem",
        "shell",
        "network",
        "mcp",
        "nested_delegation",
        "context_policy",
        "model_class",
        "output_contract",
    )
    for path in written:
        profile = renderer.parse_codex_profile(path.read_text())
        assert profile["name"] == path.stem.replace("-", "_")
        assert profile["model"] in renderer.CODEX_MODELS
        assert profile["model_reasoning_effort"] in renderer.CODEX_EFFORTS
        assert profile["sandbox_mode"] in renderer.CODEX_SANDBOXES
        for capability in required_capabilities:
            assert f"- {capability}:" in profile["developer_instructions"]

    reviewer = renderer.parse_codex_profile((out / "reviewer.toml").read_text())
    assert reviewer["sandbox_mode"] == "read-only"
    assert reviewer["mcp_servers"] == {}
    assert reviewer["agents"]["enabled"] is False

    test_runner = renderer.parse_codex_profile(
        (out / "test-runner.toml").read_text()
    )
    assert test_runner["mcp_servers"]["context7"]["enabled"] is True
    assert test_runner["agents"]["enabled"] is False


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
    del data["runtimes"]["codex"]["roles"]["reviewer"]
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


def test_vendor_field_in_semantic_source_is_rejected(tmp_path):
    root = clone_root(tmp_path)
    path = root / "agents/reviewer.md"
    path.write_text(path.read_text().replace("---\n", "---\nmodel: vendor-x\n", 1))
    with pytest.raises(renderer.ContractError, match="runtime policy field"):
        renderer.validate(root)


def test_incomplete_unsupported_exception_is_rejected(tmp_path):
    root = clone_root(tmp_path)
    path = root / "agents/runtime-bindings.json"
    data = json.loads(path.read_text())
    value = data["runtimes"]["codex"]["roles"]["test-runner"]["capabilities"]
    value["mcp"] = {"status": "unsupported-exception"}
    path.write_text(json.dumps(data))
    with pytest.raises(renderer.ContractError, match="incomplete unsupported"):
        renderer.validate(root)
