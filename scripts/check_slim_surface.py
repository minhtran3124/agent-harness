#!/usr/bin/env python3
"""Pin the slim-skill-surface retirement: three skills are gone, from disk AND registry.

A half-revert is the failure this guards: restoring `skills/<name>/SKILL.md` without the
manifest entry (or the reverse) leaves `check_manifest.py` red and the router pointing at a
skill that may or may not exist. This checks both halves together, so either direction of
drift fails here with a named reason.

Usage: python3 scripts/check_slim_surface.py [--root DIR]
Exit 0 = retired cleanly. Exit 1 = one line per surviving reference.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RETIRED = ("executing-plans", "review-diff", "create-pr")


def check(root: Path) -> int:
    problems: list[str] = []

    for name in RETIRED:
        skill = root / "skills" / name
        if skill.exists():
            problems.append(
                f"skills/{name}/ still exists on disk (retired by slim-skill-surface)"
            )

    manifest_path = root / "harness-manifest.json"
    if not manifest_path.is_file():
        problems.append("harness-manifest.json not found")
    else:
        try:
            skills = set(json.loads(manifest_path.read_text()).get("skills", []))
        except json.JSONDecodeError as e:
            problems.append(f"harness-manifest.json is invalid JSON: {e}")
            skills = set()
        for name in RETIRED:
            if name in skills:
                problems.append(
                    f"'{name}' still listed in harness-manifest.json skills[]"
                )

    if problems:
        for p in problems:
            print(f"slim-surface: {p}", file=sys.stderr)
        return 1
    print(f"slim-surface: {', '.join(RETIRED)} retired from disk and manifest")
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
