#!/usr/bin/env python3
"""Validate neutral agent contracts and render runtime-specific definitions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FORBIDDEN_SOURCE_FIELDS = {"model", "tools", "memory"}
REVIEW_ROLES = {"reviewer", "task-reviewer"}


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
    if not isinstance(runtimes, dict) or set(runtimes) != {"claude", "codex"}:
        raise ContractError("runtime bindings must declare exactly claude and codex")

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", default=Path(__file__).resolve().parents[1], type=Path
    )
    parser.add_argument("--runtime", choices=("claude", "codex"), default="claude")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        validate(args.root)
        if not args.check:
            if args.runtime == "codex":
                raise ContractError(
                    "Codex profile emission is owned by Phase 5; use --check"
                )
            if args.output_dir is None:
                raise ContractError("--output-dir is required when rendering")
            render_claude(args.root, args.output_dir)
    except ContractError as exc:
        print(f"agent-bindings: {exc}", file=sys.stderr)
        return 1
    print(f"agent-bindings: {args.runtime} contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
