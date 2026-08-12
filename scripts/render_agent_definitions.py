#!/usr/bin/env python3
"""Validate neutral agent contracts and render runtime-specific definitions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FORBIDDEN_SOURCE_FIELDS = {"model", "tools", "memory"}
REVIEW_ROLES = {"reviewer", "task-reviewer"}
CODEX_REQUIRED_FIELDS = {"model", "model_reasoning_effort", "sandbox_mode"}
CODEX_MODELS = {"gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"}
CODEX_EFFORTS = {"low", "medium", "high", "xhigh", "max", "ultra"}
CODEX_SANDBOXES = {"read-only", "workspace-write", "danger-full-access"}
CODEX_MCP_POLICIES = {"none", "context7-read-only", "runtime-controlled"}


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

            if runtime == "codex":
                missing_fields = CODEX_REQUIRED_FIELDS - set(binding)
                if missing_fields:
                    raise ContractError(
                        f"codex/{role}: missing profile fields: {sorted(missing_fields)}"
                    )
                if binding["model"] not in CODEX_MODELS:
                    raise ContractError(f"codex/{role}: unsupported model binding")
                if binding["model_reasoning_effort"] not in CODEX_EFFORTS:
                    raise ContractError(f"codex/{role}: unsupported reasoning effort")
                if binding["sandbox_mode"] not in CODEX_SANDBOXES:
                    raise ContractError(f"codex/{role}: unsupported sandbox mode")
                if any(isinstance(value, dict) for value in capabilities.values()):
                    raise ContractError(
                        f"codex/{role}: unsupported capability exception remains"
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


def _frontmatter_value(frontmatter: list[str], key: str, path: Path) -> str:
    prefix = f"{key}:"
    matches = [
        line[len(prefix) :].strip() for line in frontmatter if line.startswith(prefix)
    ]
    if len(matches) != 1 or not matches[0]:
        raise ContractError(f"{path}: expected one non-empty {key} field")
    value = matches[0]
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{path}: invalid quoted {key}") from exc
        if not isinstance(decoded, str):
            raise ContractError(f"{path}: {key} must be a string")
        return decoded
    return value


def _codex_policy(contract: dict, binding: dict) -> str:
    capabilities = binding["capabilities"]
    rows = [
        "Codex runtime policy (generated from agents/runtime-bindings.json):",
        *[
            f"- {name}: {capabilities[name]}"
            for name in (
                "filesystem",
                "shell",
                "network",
                "mcp",
                "nested_delegation",
                "context_policy",
                "model_class",
                "output_contract",
            )
        ],
        "",
        "The native sandbox/model settings below are authoritative. Treat the remaining policy",
        "lines as mandatory constraints; never widen them from inside the child session.",
    ]
    if contract["context_policy"] != "fresh-bounded":
        raise ContractError("Codex agents require fresh-bounded context")
    return "\n".join(rows)


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_codex_profile(text: str) -> dict:
    """Strictly parse the small TOML subset emitted for Codex agent profiles."""
    result: dict = {}
    current = result
    seen_keys: set[tuple[str, ...]] = set()
    section: tuple[str, ...] = ()
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = tuple(line[1:-1].split("."))
            if not section or any(
                not re.fullmatch(r"[a-z][a-z0-9_]*", part) for part in section
            ):
                raise ContractError(f"invalid Codex TOML table on line {line_number}")
            current = result
            for part in section:
                existing = current.setdefault(part, {})
                if not isinstance(existing, dict):
                    raise ContractError(
                        f"Codex TOML table conflicts with a value on line {line_number}"
                    )
                current = existing
            continue
        if "=" not in line:
            raise ContractError(f"invalid Codex TOML assignment on line {line_number}")
        key, raw_value = (part.strip() for part in line.split("=", 1))
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ContractError(f"invalid Codex TOML key on line {line_number}")
        key_path = (*section, key)
        if key_path in seen_keys or key in current:
            raise ContractError(f"duplicate Codex TOML key on line {line_number}")
        seen_keys.add(key_path)
        if raw_value == "true":
            value = True
        elif raw_value == "false":
            value = False
        elif raw_value == "{}":
            value = {}
        else:
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                raise ContractError(
                    f"invalid Codex TOML value on line {line_number}"
                ) from exc
            if not isinstance(value, str):
                raise ContractError(
                    f"unsupported Codex TOML value on line {line_number}"
                )
        current[key] = value
    return result


def render_codex(root: Path, output_dir: Path) -> list[Path]:
    contracts, bindings = validate(root)
    runtime_roles = bindings["runtimes"]["codex"]["roles"]
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for role in sorted(contracts["roles"]):
        source = root / f"agents/{role}.md"
        frontmatter, body = split_frontmatter(source)
        contract = contracts["roles"][role]
        binding = runtime_roles[role]
        name = _frontmatter_value(frontmatter, "name", source).replace("-", "_")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ContractError(f"{source}: invalid Codex agent name")
        description = _frontmatter_value(frontmatter, "description", source)
        instructions = _codex_policy(contract, binding) + "\n\n" + body
        lines = [
            f"name = {_toml_string(name)}",
            f"description = {_toml_string(description)}",
            f"model = {_toml_string(binding['model'])}",
            f"model_reasoning_effort = {_toml_string(binding['model_reasoning_effort'])}",
            f"sandbox_mode = {_toml_string(binding['sandbox_mode'])}",
        ]
        mcp_policy = contract["mcp"]
        if mcp_policy not in CODEX_MCP_POLICIES:
            raise ContractError(f"codex/{role}: unmapped mcp policy {mcp_policy!r}")
        if mcp_policy == "none":
            lines.append("mcp_servers = {}")
        lines.append(f"developer_instructions = {_toml_string(instructions)}")
        if contract["nested_delegation"] is False:
            lines.extend(["", "[agents]", "enabled = false"])
        if mcp_policy == "context7-read-only":
            lines.extend(["", "[mcp_servers.context7]", "enabled = true"])
        destination = output_dir / f"{role}.toml"
        rendered = "\n".join(lines) + "\n"
        parse_codex_profile(rendered)
        destination.write_text(rendered)
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
            if args.output_dir is None:
                raise ContractError("--output-dir is required when rendering")
            if args.runtime == "codex":
                render_codex(args.root, args.output_dir)
            else:
                render_claude(args.root, args.output_dir)
    except ContractError as exc:
        print(f"agent-bindings: {exc}", file=sys.stderr)
        return 1
    print(f"agent-bindings: {args.runtime} contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
