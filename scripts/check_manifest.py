#!/usr/bin/env python3
"""Enforce that harness-manifest.json stays the single source of truth.

Checks (all mechanical, stdlib-only so CI needs no pyyaml):
  A. inventory presence scan (register-vs-scan): every manifest hook/skill/agent exists on disk
     and every disk component is in the manifest; each hook's `wired` flag matches settings.json.
  B. gate <-> enforcer: hard_gates.detectable slugs == risk-corroboration.sh's `add_cat` set
     == its category_mode branches (bidirectional).

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

    # ── B. detectable gates <-> risk-corroboration.sh (add_cat + category_mode) ─
    rc = (root / "hooks" / "risk-corroboration.sh").read_text()
    hook_added = set(re.findall(r'add_cat\s+"([^"]+)"', rc))
    # category_mode branches look like:  auth) ... ;;   or  data-loss/migration) ... ;;
    hook_modes = set(
        re.findall(r"^\s*([a-z][a-z/-]*)\)\s*echo\s+\"(?:block|warn)\"", rc, re.M)
    )
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
    for slug in man_detect - hook_modes:
        problem(
            "hard_gates",
            f"detectable '{slug}' has no category_mode branch in risk-corroboration.sh",
        )

    # ── C. contracts <-> disk ──────────────────────────────────────────────────
    for slug, spec in m.get("contracts", {}).items():
        if slug == "__doc__":
            continue
        if not spec.get("surface"):
            problem("contracts", f"{slug} has empty/missing surface")
        if not spec.get("consumers"):
            problem("contracts", f"{slug} has empty/missing consumers")
        for path in spec.get("surface", []) + spec.get("consumers", []):
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
