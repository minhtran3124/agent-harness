#!/usr/bin/env python3
"""Validate and render the deterministic Codex hybrid adapter into a temporary root."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import check_codex_packaging
import render_agent_definitions


PAYLOAD_DIR = ".codex/.agent-harness/payload"


class AdapterError(ValueError):
    """Raised when adapter inputs are incomplete or unsafe."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AdapterError(f"{path} must contain a JSON object")
    return value


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AdapterError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise AdapterError(f"{label} must stay inside the adapter")
    return value


def _plugin_command(source_command: str) -> str:
    relative = _safe_relative(source_command, "hook command")
    if not relative.startswith("hooks/"):
        raise AdapterError(f"hook command is outside hooks/: {relative}")
    return f'bash "$PLUGIN_ROOT/{relative}"'


def expected_codex_hooks(settings: dict[str, Any]) -> dict[str, Any]:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        raise AdapterError("settings.json must contain a hooks object")
    known_events = (
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "SessionStart",
        "SessionEnd",
    )
    unknown_events = sorted(set(hooks) - set(known_events))
    if unknown_events:
        raise AdapterError(
            f"settings.json contains unmapped hook events: {unknown_events}"
        )
    if "PreToolUse" not in hooks:
        raise AdapterError("settings.json missing canonical PreToolUse bindings")
    expected: dict[str, list[dict[str, Any]]] = {}
    for event in known_events:
        if event not in hooks:
            continue
        groups = hooks[event]
        if not isinstance(groups, list) or not groups:
            raise AdapterError(f"settings.json missing canonical {event} bindings")
        rendered_groups = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise AdapterError(f"settings.json {event} contains an invalid group")
            rendered_group: dict[str, Any] = {}
            matcher = group.get("matcher")
            if matcher is not None:
                if matcher == "Write|Edit":
                    matcher = "apply_patch|Edit|Write"
                rendered_group["matcher"] = matcher
            handlers = []
            for handler in group["hooks"]:
                if not isinstance(handler, dict) or handler.get("type") != "command":
                    raise AdapterError(
                        f"settings.json {event} contains an unsupported handler"
                    )
                rendered_handler = {
                    "type": "command",
                    "command": _plugin_command(handler.get("command")),
                }
                if "statusMessage" in handler:
                    rendered_handler["statusMessage"] = handler["statusMessage"]
                if event in {"SessionStart", "UserPromptSubmit"}:
                    rendered_handler["additionalContextLimit"] = 2500
                if event == "SessionEnd":
                    rendered_handler["timeout"] = 1
                handlers.append(rendered_handler)
            rendered_group["hooks"] = handlers
            rendered_groups.append(rendered_group)
        expected[event] = rendered_groups
    return {
        "description": "Generated registrations for the shared Agent Harness hook bodies.",
        "hooks": expected,
    }


def _validate_schema(schema: dict[str, Any]) -> None:
    if (
        schema.get("type") != "object"
        or schema.get("additionalProperties") is not False
    ):
        raise AdapterError("adapter schema must be a closed object schema")
    required = schema.get("required")
    expected = {
        "schema_version",
        "runtime",
        "packaging_decision",
        "skills",
        "hooks",
        "agents",
        "payload",
    }
    if not isinstance(required, list) or set(required) != expected:
        raise AdapterError("adapter schema required inventory is incomplete")


def validate_sources(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    decision = root / "specs/codex-support/packaging-decision.md"
    errors = check_codex_packaging.validate_decision(decision, root=root)
    if errors:
        raise AdapterError("packaging decision is not renderable: " + "; ".join(errors))
    decision_text = decision.read_text()
    if (
        "decision: hybrid" not in decision_text
        or "runtime_execution: observed" not in decision_text
    ):
        raise AdapterError("hybrid runtime execution must be selected and observed")

    manifest = load_json(root / "harness-manifest.json")
    schema = load_json(root / "adapters/codex/schema.json")
    _validate_schema(schema)
    plugin_manifest = load_json(
        root / "adapters/codex/plugin/.codex-plugin/plugin.json"
    )
    expected_manifest = {
        "description": "Agent Harness skills and lifecycle hooks for Codex",
        "hooks": "./hooks/hooks.json",
        "name": "agent-harness",
        "skills": "./skills/",
        "version": "0.1.0-alpha.1",
    }
    if plugin_manifest != expected_manifest:
        raise AdapterError(
            "Codex plugin manifest differs from the pinned adapter contract"
        )

    source_hooks = load_json(root / "adapters/codex/plugin/hooks/hooks.json")
    expected_hooks = expected_codex_hooks(load_json(root / "settings.json"))
    if source_hooks != expected_hooks:
        raise AdapterError(
            "Codex hooks do not match the canonical settings event/tool matrix"
        )

    skills = manifest.get("skills")
    agents = manifest.get("agents")
    hook_rows = manifest.get("hooks")
    if not isinstance(skills, list) or len(skills) != len(set(skills)):
        raise AdapterError("manifest skills inventory is invalid")
    if not isinstance(agents, list) or len(agents) != len(set(agents)):
        raise AdapterError("manifest agents inventory is invalid")
    if not isinstance(hook_rows, list) or not hook_rows:
        raise AdapterError("manifest hooks inventory is invalid")
    disk_skills = sorted(
        path.name for path in (root / "skills").iterdir() if path.is_dir()
    )
    if sorted(skills) != disk_skills:
        raise AdapterError("manifest skills do not exactly match source directories")
    disk_agents = sorted(
        path.stem
        for path in (root / "agents").glob("*.md")
        if path.name not in {"PROJECT.md", "PROJECT.template.md", "README.md"}
    )
    if sorted(agents) != disk_agents:
        raise AdapterError("manifest agents do not exactly match semantic role sources")
    declared_hooks = {row.get("name") for row in hook_rows if isinstance(row, dict)}
    disk_hooks = {path.name for path in (root / "hooks").glob("*.sh")}
    if declared_hooks != disk_hooks:
        raise AdapterError("manifest hooks do not exactly match shared hook bodies")
    render_agent_definitions.validate(root)
    return manifest, source_hooks


def _assert_output_root(root: Path, output: Path) -> Path:
    resolved_root = root.resolve()
    resolved_output = output.resolve()
    if resolved_output == resolved_root or resolved_output.is_relative_to(
        resolved_root
    ):
        raise AdapterError(
            "output must be a temporary path outside the source repository"
        )
    if resolved_output == Path(resolved_output.anchor):
        raise AdapterError("output cannot be a filesystem root")
    return resolved_output


def _copy_tree(source: Path, destination: Path) -> None:
    for path in source.rglob("*"):
        if path.is_symlink():
            raise AdapterError(f"source symlink is not allowed: {path}")
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def _file_inventory(base: Path, relative_root: Path) -> list[str]:
    return sorted(
        path.relative_to(relative_root).as_posix()
        for path in base.rglob("*")
        if path.is_file()
    )


def parse_bash_array(text: str, name: str) -> list[str]:
    """Entries of a `NAME=(` array with one double-quoted entry per line; comments skipped."""
    lines = text.splitlines()
    try:
        start = lines.index(f"{name}=(")
    except ValueError:
        raise AdapterError(f"cannot parse {name}: array header is absent") from None
    entries = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped == ")":
            if not entries:
                raise AdapterError(f"cannot parse {name}: array has no entries")
            return entries
        if not stripped or stripped.startswith("#"):
            continue
        match = re.fullmatch(r'"([^"]+)"', stripped)
        if not match:
            raise AdapterError(f"cannot parse {name}: unexpected line {line!r}")
        entries.append(_safe_relative(match.group(1), f"{name} entry"))
    raise AdapterError(f"cannot parse {name}: closing ) is absent")


def consumer_subset(root: Path) -> dict[str, Path]:
    """Payload path -> source for deploy-harness.sh CONSUMER_SCRIPTS + CONSUMER_DATA."""
    text = (root / "scripts/deploy-harness.sh").read_text()
    subset = {
        f"scripts/{name}": root / "scripts" / name
        for name in parse_bash_array(text, "CONSUMER_SCRIPTS")
    }
    subset.update(
        {name: root / name for name in parse_bash_array(text, "CONSUMER_DATA")}
    )
    for target, source in subset.items():
        if not source.is_file():
            raise AdapterError(f"consumer subset names a missing file: {target}")
    return subset


def _payload_sources(root: Path, skills: list[str]) -> dict[str, Path]:
    def keep(path: Path) -> bool:
        return (
            path.is_file()
            and not path.name.startswith("test_")
            and path.suffix != ".pyc"
            and path.name != ".DS_Store"
            and "__pycache__" not in path.parts
        )

    sources: dict[str, Path] = {}
    for directory in ("rules", "runtime", "templates"):
        for path in (root / directory).rglob("*"):
            if keep(path):
                sources[path.relative_to(root).as_posix()] = path
    for skill in skills:
        for path in (root / "skills" / skill).rglob("*"):
            if keep(path) and path.suffix != ".md":
                sources[path.relative_to(root).as_posix()] = path
    sources.update(consumer_subset(root))
    for path in sources.values():
        if path.is_symlink():
            raise AdapterError(f"source symlink is not allowed: {path}")
    return sources


def rewrite_payload_paths(text: str, targets: set[str] | list[str]) -> str:
    """Prefix bare references to payload files; token-anchored, so idempotent."""
    alternation = "|".join(re.escape(t) for t in sorted(targets, key=len, reverse=True))
    pattern = re.compile(rf"(?<![\w./-])(?:{alternation})(?![\w-])")
    return pattern.sub(lambda match: f"{PAYLOAD_DIR}/{match.group(0)}", text)


def _rewrite_markdown(base: Path, targets: list[str]) -> None:
    for path in sorted(base.rglob("*.md")):
        text = path.read_text()
        rewritten = rewrite_payload_paths(text, targets)
        if rewritten != text:
            path.write_text(rewritten)


def render(root: Path, output: Path) -> dict[str, Any]:
    root = root.resolve()
    output = _assert_output_root(root, output)
    manifest, source_hooks = validate_sources(root)
    if output.exists() and not output.is_dir():
        raise AdapterError("output exists and is not a directory")
    output.mkdir(parents=True, exist_ok=True)
    plugin = output / "plugin"
    project = output / "project"
    for owned in (plugin, project):
        if owned.exists():
            shutil.rmtree(owned)
    rendered_manifest = output / "render-manifest.json"
    if rendered_manifest.exists():
        rendered_manifest.unlink()

    (plugin / ".codex-plugin").mkdir(parents=True)
    shutil.copy2(
        root / "adapters/codex/plugin/.codex-plugin/plugin.json",
        plugin / ".codex-plugin/plugin.json",
    )
    _copy_tree(root / "hooks", plugin / "hooks")
    (plugin / "hooks/hooks.json").write_text(
        json.dumps(source_hooks, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    (plugin / "skills").mkdir()
    for skill in sorted(manifest["skills"]):
        _copy_tree(root / "skills" / skill, plugin / "skills" / skill)

    agents_dir = project / ".codex/agents"
    render_agent_definitions.render_codex(root, agents_dir)
    instructions = project / ".codex/harness-instructions.md"
    instructions.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "adapters/codex/project/harness-instructions.md", instructions)

    payload = project / PAYLOAD_DIR
    sources = _payload_sources(root, sorted(manifest["skills"]))
    for relative, source in sorted(sources.items()):
        destination = payload / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    targets = sorted(sources)
    _rewrite_markdown(plugin / "skills", targets)
    _rewrite_markdown(payload / "rules", targets)
    _rewrite_markdown(payload / "templates", targets)

    result = {
        "schema_version": 1,
        "runtime": "codex",
        "packaging_decision": "hybrid",
        "skills": sorted(manifest["skills"]),
        "hooks": _file_inventory(plugin / "hooks", plugin),
        "agents": sorted(path.name for path in agents_dir.glob("*.toml")),
        "payload": _file_inventory(payload, payload),
    }
    rendered_manifest.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = render(args.root, args.output)
    except (AdapterError, render_agent_definitions.ContractError) as exc:
        print(f"codex-adapter: {exc}", file=sys.stderr)
        return 1
    print(
        f"codex-adapter: rendered {len(result['skills'])} skills, "
        f"{len(result['hooks'])} hook files, and {len(result['agents'])} agents"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
