import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("render_codex_adapter.py")
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("render_codex_adapter", SCRIPT)
assert SPEC and SPEC.loader
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)
ROOT = SCRIPT.parents[1]


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def clone_render_root(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    for directory in ("adapters", "agents", "hooks", "skills"):
        shutil.copytree(ROOT / directory, root / directory)
    (root / "specs/codex-support/evidence/codex-0.147.0").mkdir(parents=True)
    for name in (
        "capability-matrix.json",
        "packaging-decision.md",
    ):
        source = ROOT / "specs/codex-support" / name
        destination = root / "specs/codex-support" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    for source in (ROOT / "specs/codex-support/evidence/codex-0.147.0").glob(
        "packaging-*.json"
    ):
        shutil.copy2(
            source,
            root / "specs/codex-support/evidence/codex-0.147.0" / source.name,
        )
    for name in ("settings.json", "harness-manifest.json"):
        shutil.copy2(ROOT / name, root / name)
    return root


def test_render_is_byte_stable_and_inventory_complete(tmp_path):
    output = tmp_path / "rendered"
    first = renderer.render(ROOT, output)
    first_digest = tree_digest(output)
    second = renderer.render(ROOT, output)
    assert tree_digest(output) == first_digest
    assert second == first

    manifest = json.loads((ROOT / "harness-manifest.json").read_text())
    assert first["skills"] == sorted(manifest["skills"])
    assert first["agents"] == sorted(f"{name}.toml" for name in manifest["agents"])
    assert "hooks/hooks.json" in first["hooks"]
    assert {f"hooks/{row['name']}" for row in manifest["hooks"]} <= set(first["hooks"])
    rendered_paths = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file()
    }
    assert not any(
        "__pycache__" in path or path.endswith(".pyc") for path in rendered_paths
    )
    assert not any(path.endswith(".DS_Store") for path in rendered_paths)


def test_rendered_json_and_toml_are_strict_and_policy_complete(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    plugin = json.loads((output / "plugin/.codex-plugin/plugin.json").read_text())
    hooks = json.loads((output / "plugin/hooks/hooks.json").read_text())
    inventory = json.loads((output / "render-manifest.json").read_text())
    assert plugin["name"] == "agent-harness"
    assert inventory["packaging_decision"] == "hybrid"
    assert hooks == renderer.expected_codex_hooks(
        json.loads((ROOT / "settings.json").read_text())
    )

    for path in sorted((output / "project/.codex/agents").glob("*.toml")):
        profile = renderer.render_agent_definitions.parse_codex_profile(
            path.read_text()
        )
        assert {
            "name",
            "description",
            "developer_instructions",
            "model",
            "model_reasoning_effort",
            "sandbox_mode",
        } <= set(profile)
        instructions = profile["developer_instructions"]
        for capability in (
            "filesystem",
            "shell",
            "network",
            "mcp",
            "nested_delegation",
            "context_policy",
            "model_class",
            "output_contract",
        ):
            assert f"- {capability}:" in instructions
    reviewer = renderer.render_agent_definitions.parse_codex_profile(
        (output / "project/.codex/agents/reviewer.toml").read_text()
    )
    assert reviewer["sandbox_mode"] == "read-only"
    assert reviewer["agents"]["enabled"] is False
    assert reviewer["mcp_servers"] == {}
    test_runner = renderer.render_agent_definitions.parse_codex_profile(
        (output / "project/.codex/agents/test-runner.toml").read_text()
    )
    assert test_runner["mcp_servers"]["context7"]["enabled"] is True


def test_hook_adapter_contains_registrations_not_semantic_bodies():
    hooks = (ROOT / "adapters/codex/plugin/hooks/hooks.json").read_text()
    assert "$PLUGIN_ROOT" in hooks
    assert "apply_patch|Edit|Write" in hooks
    assert "set -u" not in hooks
    assert "git diff" not in hooks


def test_claude_rendering_is_unchanged_by_codex_render(tmp_path):
    before = tmp_path / "claude-before"
    after = tmp_path / "claude-after"
    renderer.render_agent_definitions.render_claude(ROOT, before)
    renderer.render(ROOT, tmp_path / "codex")
    renderer.render_agent_definitions.render_claude(ROOT, after)
    assert tree_digest(before) == tree_digest(after)


def test_output_inside_source_repository_is_rejected():
    with pytest.raises(renderer.AdapterError, match="outside the source repository"):
        renderer.render(ROOT, ROOT / "generated-codex-adapter")


def test_unobserved_runtime_evidence_blocks_render(tmp_path):
    root = clone_render_root(tmp_path)
    evidence = (
        root
        / "specs/codex-support/evidence/codex-0.147.0/packaging-hybrid-runtime.json"
    )
    payload = json.loads(evidence.read_text())
    payload["result"]["checks"]["project_agent_dispatched"] = False
    payload["result"].update(
        status="unknown", passed=False, runtime_execution_observed=False
    )
    evidence.write_text(json.dumps(payload))
    with pytest.raises(
        renderer.AdapterError, match="packaging decision is not renderable"
    ):
        renderer.render(root, tmp_path / "output")


def test_incomplete_codex_policy_mapping_blocks_render(tmp_path):
    root = clone_render_root(tmp_path)
    bindings = root / "agents/runtime-bindings.json"
    payload = json.loads(bindings.read_text())
    del payload["runtimes"]["codex"]["roles"]["reviewer"]["sandbox_mode"]
    bindings.write_text(json.dumps(payload))
    with pytest.raises(
        renderer.render_agent_definitions.ContractError,
        match="missing profile fields",
    ):
        renderer.render(root, tmp_path / "output")


def test_unmapped_mcp_policy_blocks_render(tmp_path):
    root = clone_render_root(tmp_path)
    contracts = root / "agents/agent-contracts.json"
    payload = json.loads(contracts.read_text())
    payload["roles"]["coding"]["mcp"] = "everything"
    contracts.write_text(json.dumps(payload))
    with pytest.raises(
        renderer.render_agent_definitions.ContractError,
        match="unmapped mcp policy",
    ):
        renderer.render(root, tmp_path / "output")


def test_unknown_settings_hook_event_blocks_render(tmp_path):
    root = clone_render_root(tmp_path)
    settings = root / "settings.json"
    payload = json.loads(settings.read_text())
    payload["hooks"]["PreCompact"] = [
        {"hooks": [{"type": "command", "command": "hooks/state-breadcrumb.sh"}]}
    ]
    settings.write_text(json.dumps(payload))
    with pytest.raises(renderer.AdapterError, match="unmapped hook events"):
        renderer.render(root, tmp_path / "output")


def test_manifest_inventory_drift_blocks_render(tmp_path):
    root = clone_render_root(tmp_path)
    manifest = root / "harness-manifest.json"
    payload = json.loads(manifest.read_text())
    payload["skills"].remove("xia2")
    manifest.write_text(json.dumps(payload))
    with pytest.raises(renderer.AdapterError, match="skills do not exactly match"):
        renderer.render(root, tmp_path / "output")
