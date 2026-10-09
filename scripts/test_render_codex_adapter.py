import hashlib
import importlib.util
import json
import re
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
DEPLOY = "scripts/deploy-harness.sh"
PREFIX = ".codex/.agent-harness/payload/"


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
    for directory in ("rules", "runtime", "templates"):
        shutil.copytree(
            ROOT / directory,
            root / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    (root / "scripts").mkdir()
    shutil.copy2(ROOT / DEPLOY, root / DEPLOY)
    deploy_text = (ROOT / DEPLOY).read_text()
    for name in renderer.parse_bash_array(deploy_text, "CONSUMER_SCRIPTS"):
        shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
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
        {"hooks": [{"type": "command", "command": "hooks/session-knowledge.sh"}]}
    ]
    settings.write_text(json.dumps(payload))
    with pytest.raises(renderer.AdapterError, match="unmapped hook events"):
        renderer.render(root, tmp_path / "output")


def _session_start_group():
    return {
        "hooks": [{"type": "command", "command": "hooks/session-knowledge.sh"}]
    }


def _pre_tool_use_groups():
    return [
        {
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": "hooks/commit-gate.sh"}],
        },
        {
            "matcher": "Write|Edit",
            "hooks": [
                {"type": "command", "command": "hooks/branch-isolation-guard.sh"}
            ],
        },
    ]


def test_settings_with_only_pre_tool_use_and_session_start_render():
    rendered = renderer.expected_codex_hooks(
        {
            "hooks": {
                "PreToolUse": _pre_tool_use_groups(),
                "SessionStart": [_session_start_group()],
            }
        }
    )
    assert set(rendered["hooks"]) == {"PreToolUse", "SessionStart"}
    assert rendered["hooks"]["PreToolUse"][1]["matcher"] == "apply_patch|Edit|Write"
    session = rendered["hooks"]["SessionStart"][0]["hooks"][0]
    assert session["additionalContextLimit"] == 2500


def test_settings_missing_pre_tool_use_blocks_render():
    with pytest.raises(renderer.AdapterError, match="PreToolUse"):
        renderer.expected_codex_hooks(
            {"hooks": {"SessionStart": [_session_start_group()]}}
        )


def test_unknown_settings_hook_event_blocks_expected_hooks():
    with pytest.raises(renderer.AdapterError, match="unmapped hook events"):
        renderer.expected_codex_hooks(
            {
                "hooks": {
                    "PreToolUse": _pre_tool_use_groups(),
                    "PreCompact": [_session_start_group()],
                }
            }
        )


def test_manifest_inventory_drift_blocks_render(tmp_path):
    root = clone_render_root(tmp_path)
    manifest = root / "harness-manifest.json"
    payload = json.loads(manifest.read_text())
    payload["skills"].remove("xia2")
    manifest.write_text(json.dumps(payload))
    with pytest.raises(renderer.AdapterError, match="skills do not exactly match"):
        renderer.render(root, tmp_path / "output")


# --- payload: closure, consumer subset, rewrite, inventory (gh-253) ---


def _payload(output: Path) -> Path:
    return output / "project/.codex/.agent-harness/payload"


def _rendered_markdown(output: Path) -> list[Path]:
    payload = _payload(output)
    return sorted(
        [*(output / "plugin/skills").rglob("*.md")]
        + [*(payload / "rules").rglob("*.md")]
        + [*(payload / "templates").rglob("*.md")]
    )


def _array_entries(text: str, name: str) -> list[str]:
    body = text.split(f"{name}=(\n", 1)[1].split("\n)", 1)[0]
    return re.findall(r'^\s*"([^"]+)"\s*$', body, re.MULTILINE)


def _payload_eligible_in_source(root: Path) -> set[str]:
    """Payload-backed targets derived from the source tree, independent of the renderer."""
    deploy = (root / DEPLOY).read_text()
    eligible = {f"rules/{p.name}" for p in (root / "rules").glob("*.md")}
    eligible |= {
        f"runtime/{p.name}"
        for p in (root / "runtime").glob("*.py")
        if not p.name.startswith("test_")
    }
    eligible |= {
        p.relative_to(root).as_posix()
        for p in (root / "templates").rglob("*")
        if p.is_file()
    }
    eligible |= {f"scripts/{n}" for n in _array_entries(deploy, "CONSUMER_SCRIPTS")}
    eligible |= set(_array_entries(deploy, "CONSUMER_DATA"))
    for skill in json.loads((root / "harness-manifest.json").read_text())["skills"]:
        for p in (root / "skills" / skill).rglob("*"):
            if (
                p.is_file()
                and (
                    p.suffix != ".md"
                    or p.relative_to(root / "skills" / skill).parts[0] == "prompts"
                )
                and not p.name.startswith("test_")
                and "__pycache__" not in p.parts
            ):
                eligible.add(p.relative_to(root).as_posix())
    return eligible


BARE_TOKEN = re.compile(
    r"(?<![\w./-])((?:rules|runtime|templates|scripts|skills)/[\w./-]+|harness-manifest\.json)"
)
PREFIXED_TOKEN = re.compile(re.escape(PREFIX) + r"([\w./-]+)")


def test_payload_closure_every_helper_reference_resolves(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    payload = _payload(output)
    eligible = _payload_eligible_in_source(ROOT)
    prefixed, bare_left = set(), set()
    for path in _rendered_markdown(output):
        text = path.read_text()
        for match in PREFIXED_TOKEN.finditer(text):
            prefixed.add(match.group(1).rstrip("."))
        for match in BARE_TOKEN.finditer(text):
            if match.group(1).rstrip(".") in eligible:
                bare_left.add((path.relative_to(output).as_posix(), match.group(1)))
    assert not bare_left
    missing = sorted(ref for ref in prefixed if not (payload / ref).is_file())
    assert not missing
    assert {
        "skills/visual-planner/render_plan.py",
        "skills/subagent-driven-development/scripts/task_brief.py",
        "skills/using-git-worktrees/scripts/detect-isolation.sh",
        "runtime/resume_decision.py",
        "scripts/verify_summary.py",
        "rules/research-depth.md",
        "templates/SUMMARY.template.md",
    } <= prefixed


def _agent_profiles(output: Path) -> dict[str, str]:
    """Decoded developer_instructions per rendered Codex agent profile."""
    agents = output / "project/.codex/agents"
    return {
        path.name: renderer.render_agent_definitions.parse_codex_profile(
            path.read_text(encoding="utf-8")
        )["developer_instructions"]
        for path in sorted(agents.glob("*.toml"))
    }


def test_agent_profile_cites_payload_copies_of_rules(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    profiles = _agent_profiles(output)
    assert f"{PREFIX}rules/auto-correct-scope.md" in profiles["coding.toml"]
    assert f"{PREFIX}rules/orchestration.md" in profiles["coding.toml"]
    assert f"{PREFIX}rules/behavior.md" in profiles["reviewer.toml"]


def test_agent_profile_closure_no_bare_eligible_path_and_prefixed_resolve(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    payload = _payload(output)
    eligible = _payload_eligible_in_source(ROOT)
    prefixed, bare_left = set(), set()
    for name, text in _agent_profiles(output).items():
        for match in PREFIXED_TOKEN.finditer(text):
            prefixed.add(match.group(1).rstrip("."))
        for match in BARE_TOKEN.finditer(text):
            if match.group(1).rstrip(".") in eligible:
                bare_left.add((name, match.group(1)))
    assert not bare_left
    assert prefixed
    missing = sorted(ref for ref in prefixed if not (payload / ref).is_file())
    assert not missing


def test_agent_profile_keeps_agents_paths_bare(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    joined = "\n".join(_agent_profiles(output).values())
    assert "agents/PROJECT.md" in joined
    assert "agents/runtime-bindings.json" in joined
    assert f"{PREFIX}agents/" not in joined


def test_agent_profile_render_is_byte_identical(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    renderer.render(ROOT, first)
    renderer.render(ROOT, second)
    agents = "project/.codex/agents"
    assert tree_digest(first / agents) == tree_digest(second / agents)


def test_payload_closure_payload_equals_source_eligible_set(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    payload = _payload(output)
    copied = {p.relative_to(payload).as_posix() for p in payload.rglob("*") if p.is_file()}
    assert copied == _payload_eligible_in_source(ROOT)
    assert {
        "skills/visual-planner/template.html",
        "skills/visual-planner/view_plan.py",
        "skills/visual-planner/build_roadmap.py",
        "skills/correctness-review/review-config.json",
        "skills/subagent-driven-development/scripts/review_package.py",
    } <= copied


def test_consumer_subset_matches_deploy_harness_arrays(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    payload = _payload(output)
    deploy = (ROOT / DEPLOY).read_text()
    scripts = {p.name for p in (payload / "scripts").iterdir()}
    assert scripts == set(_array_entries(deploy, "CONSUMER_SCRIPTS"))
    top_level = {p.name for p in payload.iterdir() if p.is_file()}
    assert top_level == set(_array_entries(deploy, "CONSUMER_DATA"))


def test_consumer_subset_removal_removes_payload_file(tmp_path):
    root = clone_render_root(tmp_path)
    deploy = root / DEPLOY
    text = deploy.read_text()
    assert '  "render_skill_prompt.py"\n' in text
    deploy.write_text(text.replace('  "render_skill_prompt.py"\n', "", 1))
    output = tmp_path / "rendered"
    renderer.render(root, output)
    scripts = _payload(output) / "scripts"
    assert not (scripts / "render_skill_prompt.py").exists()
    assert (scripts / "verify_summary.py").is_file()


@pytest.mark.parametrize("array", ["CONSUMER_SCRIPTS", "CONSUMER_DATA"])
def test_consumer_subset_bogus_entry_fails_render(tmp_path, array):
    root = clone_render_root(tmp_path)
    deploy = root / DEPLOY
    text = deploy.read_text()
    deploy.write_text(
        text.replace(f"{array}=(\n", f'{array}=(\n  "no_such_helper.py"\n', 1)
    )
    with pytest.raises(renderer.AdapterError, match="no_such_helper.py"):
        renderer.render(root, tmp_path / "output")


@pytest.mark.parametrize("case", ["no_header", "no_close", "no_entries"])
def test_consumer_subset_unparseable_array_fails_render(tmp_path, case):
    root = clone_render_root(tmp_path)
    deploy = root / DEPLOY
    text = deploy.read_text()
    head, rest = text.split("CONSUMER_SCRIPTS=(\n", 1)
    body, tail = rest.split("\n)", 1)
    if case == "no_header":
        text = head + "CONSUMER_SCRIPTZ=(\n" + rest
    elif case == "no_close":
        text = head + "CONSUMER_SCRIPTS=(\n" + body + tail
    else:
        text = head + "CONSUMER_SCRIPTS=(\n  # nothing left\n)" + tail
    deploy.write_text(text)
    with pytest.raises(renderer.AdapterError, match="CONSUMER_SCRIPTS"):
        renderer.render(root, tmp_path / "output")


def test_consumer_subset_parser_skips_comment_lines():
    text = 'X=(\n  # a comment\n  "a.py"\n\n  "b.py"\n)\n'
    assert renderer.parse_bash_array(text, "X") == ["a.py", "b.py"]


REWRITE_TARGETS = {
    "rules/x.md",
    "runtime/resume_decision.py",
    "scripts/verify_summary.py",
    "skills/visual-planner/render_plan.py",
    "harness-manifest.json",
}


def test_rewrite_prefixes_bare_payload_paths_and_is_idempotent():
    text = (
        "See rules/x.md and `scripts/verify_summary.py --lane s`.\n"
        "Read harness-manifest.json, run python3 skills/visual-planner/render_plan.py.\n"
    )
    once = renderer.rewrite_payload_paths(text, REWRITE_TARGETS)
    assert once == (
        f"See {PREFIX}rules/x.md and `{PREFIX}scripts/verify_summary.py --lane s`.\n"
        f"Read {PREFIX}harness-manifest.json, run python3 "
        f"{PREFIX}skills/visual-planner/render_plan.py.\n"
    )
    assert renderer.rewrite_payload_paths(once, REWRITE_TARGETS) == once


def test_rewrite_leaves_claude_prefixed_and_non_payload_paths_unchanged():
    text = (
        ".claude/rules/x.md\n"
        f"{PREFIX}rules/x.md\n"
        "scripts/test_x.py and scripts/deploy-harness.sh\n"
        "rules/x.mdx and src/rules/x.md\n"
    )
    assert renderer.rewrite_payload_paths(text, REWRITE_TARGETS) == text


def test_rewrite_dual_candidate_snippet_rewrites_only_bare_branch():
    text = (
        "if [ -f runtime/resume_decision.py ]; then python3 runtime/resume_decision.py; "
        "else python3 .claude/runtime/resume_decision.py; fi"
    )
    assert renderer.rewrite_payload_paths(text, REWRITE_TARGETS) == (
        f"if [ -f {PREFIX}runtime/resume_decision.py ]; then python3 "
        f"{PREFIX}runtime/resume_decision.py; "
        "else python3 .claude/runtime/resume_decision.py; fi"
    )


def test_rewrite_applies_to_rendered_frontmatter_and_payload_rules(tmp_path):
    before = tree_digest(ROOT / "skills"), tree_digest(ROOT / "rules")
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    assert (tree_digest(ROOT / "skills"), tree_digest(ROOT / "rules")) == before
    skill = (output / "plugin/skills/writing-plans/SKILL.md").read_text()
    frontmatter = skill.split("---", 2)[1]
    assert f"Bash(python3 {PREFIX}skills/visual-planner/render_plan.py *)" in frontmatter
    assert f"Bash(python3 {PREFIX}scripts/check_plan_contract.py *)" in frontmatter
    worktrees = (output / "plugin/skills/using-git-worktrees/SKILL.md").read_text()
    assert (
        f"Bash(bash {PREFIX}skills/using-git-worktrees/scripts/detect-isolation.sh*)"
        in worktrees.split("---", 2)[1]
    )
    rule = (_payload(output) / "rules/auto-correct-scope.md").read_text()
    assert f"`{PREFIX}skills/visual-planner/render_plan.py`" in rule
    resume = (output / "plugin/skills/subagent-driven-development/SKILL.md").read_text()
    assert "python3 .claude/runtime/resume_decision.py" in resume


def test_payload_inventory_is_required_by_schema_and_matches_tree(tmp_path):
    output = tmp_path / "rendered"
    result = renderer.render(ROOT, output)
    schema = json.loads((ROOT / "adapters/codex/schema.json").read_text())
    inventory = json.loads((output / "render-manifest.json").read_text())
    assert inventory == result
    assert "payload" in schema["required"]
    assert set(inventory) == set(schema["required"]) == set(schema["properties"])
    payload_schema = schema["properties"]["payload"]
    assert payload_schema["type"] == "array" and payload_schema["uniqueItems"] is True
    pattern = re.compile(payload_schema["items"]["pattern"])
    assert inventory["payload"] == sorted(set(inventory["payload"]))
    assert all(pattern.fullmatch(item) for item in inventory["payload"])
    payload = _payload(output)
    assert inventory["payload"] == sorted(
        p.relative_to(payload).as_posix() for p in payload.rglob("*") if p.is_file()
    )


def test_payload_inventory_missing_from_schema_fails_closed():
    schema = json.loads((ROOT / "adapters/codex/schema.json").read_text())
    renderer._validate_schema(schema)
    schema["required"].remove("payload")
    with pytest.raises(renderer.AdapterError, match="required inventory"):
        renderer._validate_schema(schema)


def test_payload_closure_helpers_resolve_the_consumer_root_not_the_payload(tmp_path):
    import subprocess

    renderer.render(ROOT, tmp_path / "codex")
    consumer = tmp_path / "consumer"
    payload = consumer / renderer.PAYLOAD_DIR
    shutil.copytree(tmp_path / "codex/project" / renderer.PAYLOAD_DIR, payload)
    (consumer / "specs/demo").mkdir(parents=True)
    (consumer / "specs/demo/SUMMARY.md").write_text(
        "# demo\n\nLane: tiny\nConfidence: high\nReason: a real filled reason\n"
    )
    (consumer / "docs/solutions").mkdir(parents=True)

    def run(*args):
        return subprocess.run(
            [sys.executable, *args], cwd=consumer, capture_output=True, text=True
        )

    # verify_summary.py: the slug resolves to <consumer>/specs, as rewritten skills invoke it.
    lane = run(f"{renderer.PAYLOAD_DIR}/scripts/verify_summary.py", "--lane", "demo")
    assert lane.returncode == 0, lane.stdout + lane.stderr

    # rebuild_solution_index.py: writes the consumer's INDEX, never one inside the payload.
    index = run(f"{renderer.PAYLOAD_DIR}/scripts/rebuild_solution_index.py")
    assert index.returncode == 0, index.stdout + index.stderr
    assert (consumer / "docs/solutions/INDEX.md").is_file()
    assert not (payload / "docs").exists()

    # render_skill_prompt.py: the bare angle-fragment template resolves against the payload.
    prompt = run(
        f"{renderer.PAYLOAD_DIR}/scripts/render_skill_prompt.py",
        "--fragment",
        f"{renderer.PAYLOAD_DIR}/skills/correctness-review/prompts/shared.md",
        "--fragment",
        "skills/correctness-review/prompts/angles/prior-art.md",
    )
    assert prompt.returncode == 0, prompt.stderr
    assert "correctness reviewer" in prompt.stdout
    assert "<!-- source: /" not in prompt.stdout  # provenance stays relative


def test_rewrite_with_no_targets_returns_text_unchanged():
    text = "Hello  world\n\n# Title (x) `rules/a.md`\n"
    assert renderer.rewrite_payload_paths(text, []) == text
    assert renderer.rewrite_payload_paths(text, set()) == text


BEGIN_MARKER = "<!-- agent-harness:begin -->"
END_MARKER = "<!-- agent-harness:end -->"


def _has_paths_frontmatter(path: Path) -> bool:
    """Mirror of tests/scripts/rule-loading-tiers.test.sh has_paths_frontmatter."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return False
    for line in lines[1:]:
        if line == "---":
            return False
        if line.startswith("paths:"):
            return True
    return False


def _block(output: Path) -> str:
    return (output / "agents-block.md").read_text(encoding="utf-8")


def test_agents_block_inventory_inlines_always_on_and_lists_path_scoped(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    block = _block(output)
    rules = sorted((ROOT / "rules").glob("*.md"))
    always_on = [p.name for p in rules if not _has_paths_frontmatter(p)]
    path_scoped = [p.name for p in rules if _has_paths_frontmatter(p)]
    assert always_on and path_scoped

    sources = re.findall(r"^Source: (\S+)$", block, re.MULTILINE)
    assert sources == [f"{PREFIX}rules/{name}" for name in always_on]
    payload_rules = _payload(output) / "rules"
    for name in always_on:
        text = (payload_rules / name).read_text(encoding="utf-8").rstrip()
        assert f"Source: {PREFIX}rules/{name}\n\n{text}" in block

    listed = re.findall(r"^- `(\S+)` — read when working on: (.+)$", block, re.MULTILINE)
    assert [path for path, _ in listed] == [
        f"{PREFIX}rules/{name}" for name in path_scoped
    ]
    for path, globs in listed:
        assert (output / "project" / path).is_file()
        assert globs == ", ".join(
            f"`{glob}`"
            for glob in renderer.path_scoped_rules(payload_rules)[Path(path).name]
        )
    assert renderer.path_scoped_rules(payload_rules)["terminology.md"] == [
        "specs/**/PLAN.md",
        "specs/**/research-brief.md",
        "specs/**/SUMMARY.md",
    ]
    assert renderer.always_on_rules(payload_rules) == always_on


def test_agents_block_budget_current_block_is_at_most_18_kib(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    block = renderer.render_agents_block(
        (ROOT / "adapters/codex/project/harness-instructions.md").read_text(
            encoding="utf-8"
        ),
        _payload(output) / "rules",
    )
    assert len(block.encode("utf-8")) <= 18 * 1024
    assert renderer.AGENTS_BLOCK_MAX_BYTES == 20 * 1024


def test_agents_block_budget_over_20_kib_fails_render(tmp_path):
    root = clone_render_root(tmp_path)
    (root / "rules/zz-oversized.md").write_text(
        "# Oversized\n\n" + "é" * (11 * 1024) + "\n", encoding="utf-8"
    )
    with pytest.raises(renderer.AdapterError, match="exceeds"):
        renderer.render(root, tmp_path / "rendered")


@pytest.mark.parametrize("marker", [BEGIN_MARKER, END_MARKER])
def test_agents_block_budget_marker_inside_rule_fails_render(tmp_path, marker):
    root = clone_render_root(tmp_path)
    with (root / "rules/behavior.md").open("a", encoding="utf-8") as handle:
        handle.write(f"\n{marker}\n")
    with pytest.raises(renderer.AdapterError, match="marker"):
        renderer.render(root, tmp_path / "rendered")


def test_agents_block_budget_marker_inside_preamble_fails_render(tmp_path):
    root = clone_render_root(tmp_path)
    preamble = root / "adapters/codex/project/harness-instructions.md"
    with preamble.open("a", encoding="utf-8") as handle:
        handle.write(f"\n{END_MARKER}\n")
    with pytest.raises(renderer.AdapterError, match="preamble"):
        renderer.render(root, tmp_path / "rendered")


def test_agents_block_budget_unclosed_rule_frontmatter_fails_render(tmp_path):
    root = clone_render_root(tmp_path)
    (root / "rules/zz-unclosed.md").write_text("---\n# Unclosed\n\nBody.\n", encoding="utf-8")
    with pytest.raises(renderer.AdapterError, match="zz-unclosed.md.*never closed"):
        renderer.render(root, tmp_path / "rendered")


@pytest.mark.parametrize("paths", ['paths: ["specs/**"]', 'paths:\n- "specs/**"'])
def test_agents_block_budget_paths_without_parsed_globs_fails_render(tmp_path, paths):
    root = clone_render_root(tmp_path)
    (root / "rules/zz-inline.md").write_text(f"---\n{paths}\n---\n\n# Inline\n", encoding="utf-8")
    with pytest.raises(renderer.AdapterError, match="zz-inline.md.*no globs"):
        renderer.render(root, tmp_path / "rendered")


def test_agents_block_budget_empty_always_on_set_fails_render(tmp_path):
    root = clone_render_root(tmp_path)
    for path in (root / "rules").glob("*.md"):
        if not _has_paths_frontmatter(path):
            text = path.read_text(encoding="utf-8")
            path.write_text('---\npaths:\n  - "x/**"\n---\n\n' + text, encoding="utf-8")
    with pytest.raises(renderer.AdapterError, match="always-on"):
        renderer.render(root, tmp_path / "rendered")


def test_agents_block_neutral_own_text_has_no_runtime_syntax(tmp_path):
    root = clone_render_root(tmp_path)
    for path in (root / "rules").glob("*.md"):
        path.unlink()
    (root / "rules/stub-always.md").write_text("# Stub\n\nPlain body.\n", encoding="utf-8")
    (root / "rules/stub-scoped.md").write_text(
        '---\npaths:\n  - "specs/**"\n---\n\n# Scoped\n', encoding="utf-8"
    )
    first = tmp_path / "first"
    second = tmp_path / "second"
    renderer.render(root, first)
    renderer.render(root, second)
    block = _block(first)
    assert (first / "agents-block.md").read_bytes() == (
        second / "agents-block.md"
    ).read_bytes()
    assert "Plain body." in block and "stub-scoped.md" in block
    assert not re.search(r"^\s*@", block, re.MULTILINE)
    assert not re.search(r"(?:^|\s)/[A-Za-z]", block, re.MULTILINE)
    assert not re.search(r"\$[A-Za-z]", block)
    assert "for codex" not in block.lower()


def test_agents_block_neutral_real_render_is_byte_identical(tmp_path):
    renderer.render(ROOT, tmp_path / "a")
    renderer.render(ROOT, tmp_path / "b")
    assert (tmp_path / "a/agents-block.md").read_bytes() == (
        tmp_path / "b/agents-block.md"
    ).read_bytes()


def test_agents_block_output_written_beside_manifest_with_one_newline(tmp_path):
    output = tmp_path / "rendered"
    renderer.render(ROOT, output)
    raw = (output / "agents-block.md").read_bytes()
    assert (output / "render-manifest.json").is_file()
    assert raw.startswith(BEGIN_MARKER.encode())
    assert raw.endswith(END_MARKER.encode() + b"\n")
    assert not raw.endswith(b"\n\n")
    text = raw.decode("utf-8")
    assert text.count(BEGIN_MARKER) == 1 and text.count(END_MARKER) == 1
    assert not (output / "project/.codex/harness-instructions.md").exists()
    assert not list((output / "project").rglob("agents-block.md"))
    block = renderer.render_agents_block(
        (ROOT / "adapters/codex/project/harness-instructions.md").read_text(
            encoding="utf-8"
        ),
        _payload(output) / "rules",
    )
    assert block + "\n" == text


def test_agents_block_output_stale_block_is_removed(tmp_path):
    output = tmp_path / "rendered"
    output.mkdir()
    stale = output / "agents-block.md"
    stale.write_text("stale\n", encoding="utf-8")
    renderer.render(ROOT, output)
    assert stale.read_text(encoding="utf-8").startswith(BEGIN_MARKER)

    stale.write_text("stale\n", encoding="utf-8")
    root = clone_render_root(tmp_path)
    for path in (root / "rules").glob("*.md"):
        path.unlink()
    with pytest.raises(renderer.AdapterError, match="always-on"):
        renderer.render(root, output)
    assert not stale.exists()
