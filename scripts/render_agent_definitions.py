#!/usr/bin/env python3
"""Validate neutral agent contracts and render runtime-specific definitions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FORBIDDEN_SOURCE_FIELDS = {"model", "effort", "tools", "memory"}
REVIEW_ROLES = {"reviewer", "task-reviewer", "intent-reviewer", "advisor", "researcher"}
CLAUDE_EFFORTS = {"low", "medium", "high", "xhigh", "max"}


class ContractError(ValueError):
    """Raised when an agent contract or runtime binding is incomplete."""


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def split_frontmatter(
    path: Path, *, allow_runtime_fields: bool = False
) -> tuple[list[str], str]:
    text = path.read_text()
    lines = text.splitlines()
    if len(lines) < 3 or lines[0] != "---":
        raise ContractError(f"{path}: missing frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ContractError(f"{path}: unclosed frontmatter") from exc
    frontmatter = lines[1:end]
    keys = {line.split(":", 1)[0].strip() for line in frontmatter if ":" in line}
    forbidden = sorted(keys & FORBIDDEN_SOURCE_FIELDS)
    if forbidden and not allow_runtime_fields:
        raise ContractError(
            f"{path}: runtime policy field(s) remain in semantic source: {', '.join(forbidden)}"
        )
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return frontmatter, body


def validate(root: Path) -> tuple[dict, dict]:
    contracts = load_json(root / "agents/agent-contracts.json")
    bindings = load_json(root / "agents/runtime-bindings.json")
    required = contracts.get("required_capabilities")
    roles = contracts.get("roles")
    runtimes = bindings.get("runtimes")
    if (
        not isinstance(required, list)
        or not required
        or len(required) != len(set(required))
    ):
        raise ContractError("required_capabilities must be a non-empty unique list")
    if not isinstance(roles, dict) or not roles:
        raise ContractError("agent contracts must declare roles")
    if not isinstance(runtimes, dict) or set(runtimes) != {"claude"}:
        raise ContractError("runtime bindings must declare exactly claude")

    role_names = set(roles)
    for role, contract in roles.items():
        if not isinstance(contract, dict):
            raise ContractError(f"{role}: contract must be an object")
        missing = set(required) - set(contract)
        if missing:
            raise ContractError(
                f"{role}: missing contract capabilities: {sorted(missing)}"
            )
        source = contract.get("source")
        if source != f"agents/{role}.md":
            raise ContractError(f"{role}: source must be agents/{role}.md")
        split_frontmatter(root / source)

    for runtime, runtime_spec in runtimes.items():
        runtime_roles = (
            runtime_spec.get("roles") if isinstance(runtime_spec, dict) else None
        )
        if not isinstance(runtime_roles, dict) or set(runtime_roles) != role_names:
            raise ContractError(
                f"{runtime}: role set must exactly match agent contracts"
            )
        for role, binding in runtime_roles.items():
            capabilities = (
                binding.get("capabilities") if isinstance(binding, dict) else None
            )
            if not isinstance(capabilities, dict) or set(capabilities) != set(required):
                raise ContractError(
                    f"{runtime}/{role}: capability mapping must exactly match required_capabilities"
                )
            for capability, value in capabilities.items():
                if isinstance(value, dict):
                    if (
                        value.get("status") != "unsupported-exception"
                        or not value.get("owner")
                        or not value.get("exit_condition")
                    ):
                        raise ContractError(
                            f"{runtime}/{role}/{capability}: incomplete unsupported exception"
                        )
                elif not isinstance(value, (str, bool)):
                    raise ContractError(
                        f"{runtime}/{role}/{capability}: mapping must be explicit"
                    )

            if runtime == "claude" and "effort" in binding:
                if binding["effort"] not in CLAUDE_EFFORTS:
                    raise ContractError(f"claude/{role}: unsupported effort")

    for role in REVIEW_ROLES:
        contract = roles[role]
        if contract["filesystem"] != "read-only":
            raise ContractError(f"{role}: reviewer filesystem must be read-only")
        if contract["nested_delegation"] is not False:
            raise ContractError(f"{role}: reviewer nested delegation must be disabled")
        if contract["context_policy"] != "fresh-bounded":
            raise ContractError(f"{role}: reviewer context must be fresh-bounded")
        if contract["mcp"] != "none":
            raise ContractError(f"{role}: reviewer MCP policy must be none")

    # A Claude role with no (or an empty) tools list inherits every tool, MCP included,
    # so `mcp: none` needs a non-empty list of plain tool names with no mcp__ entries.
    # Plain names also keep a comma-joined entry from smuggling a tool into `tools:`.
    for role, contract in roles.items():
        if contract["mcp"] != "none":
            continue
        tools = runtimes["claude"]["roles"][role].get("tools")
        if (
            not isinstance(tools, list)
            or not tools
            or not all(
                isinstance(tool, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", tool)
                for tool in tools
            )
            or any(tool.startswith("mcp__") for tool in tools)
        ):
            raise ContractError(
                f"claude/{role}: mcp none requires an explicit tools list "
                "with no mcp__ tools"
            )
    return contracts, bindings


def render_claude(root: Path, output_dir: Path) -> list[Path]:
    contracts, bindings = validate(root)
    runtime_roles = bindings["runtimes"]["claude"]["roles"]
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for role in sorted(contracts["roles"]):
        frontmatter, body = split_frontmatter(root / f"agents/{role}.md")
        binding = runtime_roles[role]
        policy = []
        tools = binding.get("tools")
        if tools is not None:
            policy.append(f"tools: {', '.join(tools)}")
        policy.append(f"model: {binding['model']}")
        if "effort" in binding:
            policy.append(f"effort: {binding['effort']}")
        # Insert runtime policy where it was authored — directly after `description` —
        # so a rendered definition stays byte-stable against the pre-binding files and a
        # re-sync does not rewrite every consumer's agent for a key reordering.
        insert_at = next(
            (
                index + 1
                for index, line in enumerate(frontmatter)
                if line.split(":", 1)[0].strip() == "description"
            ),
            len(frontmatter),
        )
        rendered = [
            "---",
            *frontmatter[:insert_at],
            *policy,
            *frontmatter[insert_at:],
            "---",
            "",
            body,
        ]
        destination = output_dir / f"{role}.md"
        destination.write_text("\n".join(rendered).rstrip() + "\n")
        written.append(destination)
    return written


def defaults_snapshot(root: Path, bindings: dict) -> dict:
    """Resolve the harness model/effort defaults that deploy ships beside the agents."""
    agents = {}
    for role, binding in bindings["runtimes"]["claude"]["roles"].items():
        agents[role] = {key: binding[key] for key in ("model", "effort") if key in binding}
    skills = {}
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        if path.parent.name == "_archive":
            continue
        frontmatter, _ = split_frontmatter(path, allow_runtime_fields=True)
        skills[path.parent.name] = {
            key: line.split(":", 1)[1].strip().strip("\"'")
            for line in frontmatter
            for key in ("model", "effort")
            if line.startswith(f"{key}:")
        }
    return {"schema_version": 1, "agents": agents, "skills": skills}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", default=Path(__file__).resolve().parents[1], type=Path
    )
    parser.add_argument("--runtime", choices=("claude",), default="claude")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--defaults-out", type=Path)
    args = parser.parse_args()
    try:
        _, bindings = validate(args.root)
        if args.defaults_out is not None and args.check:
            raise ContractError("--defaults-out cannot be combined with --check")
        if args.defaults_out is not None and args.runtime != "claude":
            raise ContractError("--defaults-out requires --runtime claude")
        if not args.check:
            if args.output_dir is None and args.defaults_out is None:
                raise ContractError("--output-dir is required when rendering")
            if args.output_dir is not None:
                render_claude(args.root, args.output_dir)
            if args.defaults_out is not None:
                snapshot = defaults_snapshot(args.root, bindings)
                args.defaults_out.write_text(
                    json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
                )
    except ContractError as exc:
        print(f"agent-bindings: {exc}", file=sys.stderr)
        return 1
    print(f"agent-bindings: {args.runtime} contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
