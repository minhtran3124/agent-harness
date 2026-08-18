#!/usr/bin/env python3
"""Enforce that harness-manifest.json stays the single source of truth.

Checks (all mechanical, stdlib-only so CI needs no pyyaml):
  A. inventory presence scan (register-vs-scan): every manifest hook/skill/agent exists on disk
     and every disk component is in the manifest; each hook's `wired` flag matches settings.json.
  B. gate <-> enforcer: hard_gates.detectable slugs == risk-corroboration.sh's `add_cat` set
     (bidirectional — a detector must exist for every manifest gate and vice versa).
     Gate modes (block|warn) are manifest-owned and read by the hook at runtime — not mirrored.

Exit 0 = consistent. Exit 1 = drift (one "manifest: ... drift: ..." line per problem).
Run: python3 scripts/check_manifest.py [--root DIR]
"""

import argparse
import json
import re
import sys
from pathlib import Path


def check(root: Path) -> int:
    problems: list[
        str
    ] = []  # local, not module-global — check() is safe to call repeatedly

    def problem(kind: str, detail: str) -> None:
        problems.append(f"manifest: {kind} drift: {detail}")

    manifest_path = root / "harness-manifest.json"
    if not manifest_path.is_file():
        print(f"manifest: harness-manifest.json not found at {root}", file=sys.stderr)
        return 1
    try:
        m = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        print(f"manifest: harness-manifest.json is invalid JSON: {e}", file=sys.stderr)
        return 1

    # ── A. hooks: manifest <-> disk <-> settings.json wiring ──────────────────
    disk_hooks = {p.name for p in (root / "hooks").glob("*.sh")}
    man_hooks = {h["name"]: h.get("wired", False) for h in m.get("hooks", [])}
    for name in man_hooks.keys() - disk_hooks:
        problem("hooks", f"{name} in manifest but not on disk (hooks/)")
    for name in disk_hooks - man_hooks.keys():
        problem("hooks", f"{name} on disk but missing from manifest")

    settings = (
        (root / "settings.json").read_text()
        if (root / "settings.json").is_file()
        else ""
    )
    wired_on_disk = set(re.findall(r"hooks/([a-zA-Z0-9._-]+\.sh)", settings))
    for name, wired_flag in man_hooks.items():
        actually_wired = name in wired_on_disk
        if wired_flag != actually_wired:
            problem(
                "hooks.wired",
                f"{name} manifest wired={wired_flag} but settings.json registered={actually_wired}",
            )

    # ── A. skills: manifest <-> disk (skills/<name>/SKILL.md) ─────────────────
    disk_skills = {p.parent.name for p in (root / "skills").glob("*/SKILL.md")}
    man_skills = set(m.get("skills", []))
    for name in man_skills - disk_skills:
        problem("skills", f"{name} in manifest but no skills/{name}/SKILL.md")
    for name in disk_skills - man_skills:
        problem("skills", f"{name} on disk but missing from manifest")

    # ── A. agents: manifest <-> agents/<name>.md (exclude README/PROJECT*) ────
    disk_agents = {
        p.stem
        for p in (root / "agents").glob("*.md")
        if p.stem != "README" and not p.stem.startswith("PROJECT")
    }
    man_agents = set(m.get("agents", []))
    for name in man_agents - disk_agents:
        problem("agents", f"{name} in manifest but no agents/{name}.md")
    for name in disk_agents - man_agents:
        problem("agents", f"{name} on disk but missing from manifest")

    # ── A2. neutral agent contracts <-> runtime bindings ─────────────────────
    agent_binding_spec = m.get("agent_bindings")
    if not isinstance(agent_binding_spec, dict):
        problem("agent_bindings", "missing agent_bindings object")
    else:
        declared_runtimes = set(agent_binding_spec.get("runtimes", []))
        if declared_runtimes != {"claude", "codex"}:
            problem("agent_bindings", "runtimes must be exactly claude and codex")
        try:
            contracts = json.loads(
                (root / agent_binding_spec["contracts"]).read_text()
            )
            bindings = json.loads((root / agent_binding_spec["bindings"]).read_text())
        except (KeyError, OSError, json.JSONDecodeError) as exc:
            problem("agent_bindings", f"cannot load contracts/bindings: {exc}")
        else:
            contract_roles = set(contracts.get("roles", {}))
            required = set(contracts.get("required_capabilities", []))
            if contract_roles != man_agents:
                problem("agent_bindings", "contract roles must match manifest agents")
            if not required:
                problem("agent_bindings", "required_capabilities must not be empty")
            runtime_map = bindings.get("runtimes", {})
            if set(runtime_map) != declared_runtimes:
                problem("agent_bindings", "binding runtimes must match declared runtimes")
            for runtime, runtime_spec in runtime_map.items():
                roles = runtime_spec.get("roles", {})
                if set(roles) != contract_roles:
                    problem("agent_bindings", f"{runtime} roles must match contracts")
                    continue
                for role, binding in roles.items():
                    capabilities = binding.get("capabilities", {})
                    if set(capabilities) != required:
                        problem(
                            "agent_bindings",
                            f"{runtime}/{role} capability mapping is incomplete",
                        )
            for role in contract_roles:
                source = root / "agents" / f"{role}.md"
                parts = source.read_text().split("---", 2)
                if len(parts) < 3:
                    problem("agent_bindings", f"agents/{role}.md lacks frontmatter")
                    continue
                frontmatter = parts[1]
                if re.search(r"^(model|tools|memory):", frontmatter, re.MULTILINE):
                    problem(
                        "agent_bindings",
                        f"agents/{role}.md retains a runtime policy field",
                    )
        renderer = agent_binding_spec.get("renderer")
        if not isinstance(renderer, str) or not (root / renderer).is_file():
            problem("agent_bindings", "renderer path is missing or invalid")

    # ── B. detectable gates <-> risk-corroboration.sh (add_cat set) ────────────
    rc = (root / "hooks" / "risk-corroboration.sh").read_text()
    hook_added = set(re.findall(r'add_cat\s+"([^"]+)"', rc))
    man_detect = {g["slug"] for g in m.get("hard_gates", {}).get("detectable", [])}

    for slug in man_detect - hook_added:
        problem(
            "hard_gates",
            f"detectable '{slug}' in manifest but no add_cat in risk-corroboration.sh",
        )
    for slug in hook_added - man_detect:
        problem(
            "hard_gates",
            f"add_cat '{slug}' in risk-corroboration.sh but not in manifest detectable",
        )

    # ── C. contracts <-> disk ──────────────────────────────────────────────────
    for slug, spec in m.get("contracts", {}).items():
        if slug == "__doc__":
            continue
        if not isinstance(spec, dict):
            problem("contracts", f"{slug} value must be an object")
            continue
        surface = spec.get("surface")
        consumers = spec.get("consumers")
        if surface is not None and not isinstance(surface, list):
            problem("contracts", f"{slug} surface must be a list")
            surface = None
        elif not surface:
            problem("contracts", f"{slug} has empty/missing surface")
        if consumers is not None and not isinstance(consumers, list):
            problem("contracts", f"{slug} consumers must be a list")
            consumers = None
        elif not consumers:
            problem("contracts", f"{slug} has empty/missing consumers")
        for path in (surface or []) + (consumers or []):
            if not isinstance(path, str):
                problem("contracts", f"{slug} path element must be a string: {path!r}")
                continue
            if not (root / path).exists():
                problem("contracts", f"{slug} path '{path}' not found on disk")

    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        print(f"\n{len(problems)} manifest drift problem(s).", file=sys.stderr)
        return 1
    print(
        "manifest: consistent — inventory ↔ disk ↔ settings.json ↔ risk-corroboration.sh all agree"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--root", default=None, help="repo root (default: script's parent dir)"
    )
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    return check(root)


if __name__ == "__main__":
    sys.exit(main())
