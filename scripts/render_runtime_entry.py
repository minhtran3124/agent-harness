#!/usr/bin/env python3
"""Render checked Claude/Codex skill invocations and model labels."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

RUNTIMES = {"claude", "codex"}
EXPECTED_STAGES = {
    "correctness_finder",
    "correctness_scorer",
    "implementer",
    "intent_reviewer",
    "task_reviewer",
}
SKILL_RE = re.compile(r"^[a-z][a-z0-9-]*$")
ROLE_RE = re.compile(r"^[a-z][a-z0-9-]*$")


class BindingError(ValueError):
    """Raised when a runtime-entry binding is incomplete or unsafe."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BindingError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BindingError(f"{path} must contain an object")
    return value


def validate(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = _load_json(root / "adapters/runtime-entry-bindings.json")
    agents = _load_json(root / "agents/runtime-bindings.json")
    if binding.get("schema_version") != 1:
        raise BindingError("runtime-entry schema_version must be 1")
    if set(binding) != {"schema_version", "model_stages", "runtimes"}:
        raise BindingError("runtime-entry binding contains unknown top-level fields")
    runtimes = binding.get("runtimes")
    if not isinstance(runtimes, dict) or set(runtimes) != RUNTIMES:
        raise BindingError("runtime-entry binding must declare claude and codex")
    prefixes: set[str] = set()
    for runtime in sorted(RUNTIMES):
        spec = runtimes[runtime]
        if not isinstance(spec, dict):
            raise BindingError(f"{runtime}: binding must be an object")
        if set(spec) != {"cli", "skill_prefix"}:
            raise BindingError(f"{runtime}: binding contains unknown fields")
        prefix = spec.get("skill_prefix")
        if not isinstance(prefix, str) or prefix not in {"/", "$"}:
            raise BindingError(f"{runtime}: unsupported skill prefix")
        prefixes.add(prefix)
        cli = spec.get("cli")
        if not isinstance(cli, dict) or set(cli) != {"executable", "arguments"}:
            raise BindingError(f"{runtime}: CLI binding is incomplete")
        executable = cli.get("executable")
        arguments = cli.get("arguments")
        if not isinstance(executable, str) or not executable:
            raise BindingError(f"{runtime}: CLI executable must be non-empty")
        if (
            not isinstance(arguments, list)
            or not arguments
            or any(not isinstance(value, str) for value in arguments)
            or arguments.count("{prompt}") != 1
            or any(
                "{prompt}" in value and value != "{prompt}" for value in arguments
            )
        ):
            raise BindingError(f"{runtime}: CLI arguments need one prompt placeholder")
    if len(prefixes) != len(RUNTIMES):
        raise BindingError("runtime skill prefixes must remain distinct")

    stages = binding.get("model_stages")
    if not isinstance(stages, dict) or set(stages) != EXPECTED_STAGES:
        raise BindingError("model stages must exactly match the runtime-entry contract")
    if any(not isinstance(role, str) or not ROLE_RE.fullmatch(role) for role in stages.values()):
        raise BindingError("model stages must reference kebab-case agent roles")
    agent_runtimes = agents.get("runtimes")
    if not isinstance(agent_runtimes, dict) or set(agent_runtimes) != RUNTIMES:
        raise BindingError("agent runtime bindings must declare claude and codex")
    for runtime in sorted(RUNTIMES):
        roles = agent_runtimes[runtime].get("roles")
        if not isinstance(roles, dict):
            raise BindingError(f"{runtime}: agent roles are missing")
        for stage, role in stages.items():
            role_binding = roles.get(role)
            if not isinstance(role_binding, dict) or not isinstance(
                role_binding.get("model"), str
            ) or not role_binding["model"]:
                raise BindingError(f"{runtime}/{stage}: model role {role!r} is unresolved")
    for runtime in sorted(RUNTIMES):
        if model_label(binding, agents, runtime, "correctness_finder") == model_label(
            binding, agents, runtime, "correctness_scorer"
        ):
            raise BindingError(f"{runtime}: correctness scorer must differ from finders")
        if model_label(binding, agents, runtime, "implementer") == model_label(
            binding, agents, runtime, "intent_reviewer"
        ):
            raise BindingError(f"{runtime}: intent reviewer must differ from implementer")
    return binding, agents


def skill_invocation(binding: dict[str, Any], runtime: str, skill: str) -> str:
    if runtime not in RUNTIMES:
        raise BindingError(f"unknown runtime: {runtime}")
    if not SKILL_RE.fullmatch(skill):
        raise BindingError("skill name must be kebab-case")
    return binding["runtimes"][runtime]["skill_prefix"] + skill


def cli_command(
    binding: dict[str, Any], runtime: str, skill: str, prompt: str = ""
) -> str:
    invocation = skill_invocation(binding, runtime, skill)
    complete_prompt = invocation + (f" {prompt}" if prompt else "")
    cli = binding["runtimes"][runtime]["cli"]
    arguments = [
        complete_prompt if value == "{prompt}" else value for value in cli["arguments"]
    ]
    return shlex.join([cli["executable"], *arguments])


def model_label(
    binding: dict[str, Any], agents: dict[str, Any], runtime: str, stage: str
) -> str:
    if runtime not in RUNTIMES:
        raise BindingError(f"unknown runtime: {runtime}")
    role = binding["model_stages"].get(stage)
    if role is None:
        raise BindingError(f"unknown model stage: {stage}")
    return agents["runtimes"][runtime]["roles"][role]["model"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--runtime", choices=sorted(RUNTIMES))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--skill")
    group.add_argument("--model-stage", choices=sorted(EXPECTED_STAGES))
    parser.add_argument("--prompt", default="")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        binding, agents = validate(args.root.resolve())
        if args.check:
            if args.runtime or args.skill or args.model_stage or args.prompt:
                raise BindingError("--check cannot be combined with render options")
            print("runtime-entry: bindings passed")
            return 0
        if args.runtime is None:
            raise BindingError("--runtime is required when rendering")
        if args.skill:
            print(cli_command(binding, args.runtime, args.skill, args.prompt))
            return 0
        if args.model_stage:
            print(model_label(binding, agents, args.runtime, args.model_stage))
            return 0
        raise BindingError("select --skill or --model-stage")
    except BindingError as exc:
        print(f"runtime-entry: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
