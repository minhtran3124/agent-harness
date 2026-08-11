#!/usr/bin/env python3
"""Enforce the owned inventory of runtime-coupled instruction sources."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any


INVENTORY = "specs/codex-support/neutralization-inventory.json"
ALLOWED_CLASSIFICATIONS = {
    "shared-source-violation",
    "runtime-entry-binding",
    "test-fixture",
    "false-positive",
}
VENDOR_FIELDS = {"model", "tools", "disallowedTools"}
SUPPORTED_CATEGORIES = {
    "deployed-rule-path",
    "deployed-skill-path",
    "slash-skill-invocation",
    "vendor-agent-policy",
}


def _load_inventory(root: Path, errors: list[str]) -> dict[str, Any]:
    path = root / INVENTORY
    try:
        payload = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"inventory is not readable JSON: {exc}")
        return {}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        errors.append("inventory schema_version must be 1")
        return {}
    return payload


def _safe_relative(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _slash_pattern(skill_names: list[str]) -> re.Pattern[str]:
    names = "|".join(
        re.escape(name) for name in sorted(skill_names, key=len, reverse=True)
    )
    return re.compile(rf"(?<![A-Za-z0-9_.\\])/(?:{names})(?![A-Za-z0-9-])")


def _frontmatter_vendor_lines(path: Path, lines: list[str]) -> set[int]:
    if path.parent.name != "agents" or path.suffix != ".md" or not lines:
        return set()
    if lines[0].strip() != "---":
        return set()
    result: set[int] = set()
    for number, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            break
        key = line.split(":", 1)[0].strip()
        if key in VENDOR_FIELDS:
            result.add(number)
    return result


def _scan_file(
    path: Path, relative: str, slash: re.Pattern[str]
) -> list[dict[str, Any]]:
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    vendor_lines = _frontmatter_vendor_lines(path, lines)
    found: list[dict[str, Any]] = []
    for number, line in enumerate(lines, start=1):
        categories: list[str] = []
        if ".claude/rules/" in line:
            categories.append("deployed-rule-path")
        if ".claude/skills/" in line:
            categories.append("deployed-skill-path")
        if slash.search(line):
            categories.append("slash-skill-invocation")
        if number in vendor_lines or re.search(
            r"\bmodel:\s*claude-[A-Za-z0-9-]+", line
        ):
            categories.append("vendor-agent-policy")
        for category in categories:
            found.append(
                {
                    "path": relative,
                    "category": category,
                    "line": number,
                    "text": line.strip()[:240],
                }
            )
    return found


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    inventory = _load_inventory(root, errors)
    if not inventory:
        return errors
    roots = inventory.get("scan_roots")
    skill_names = inventory.get("skill_names")
    entries = inventory.get("findings")
    if (
        not isinstance(roots, list)
        or not roots
        or not all(_safe_relative(v) for v in roots)
    ):
        errors.append(
            "scan_roots must be a non-empty list of repository-relative paths"
        )
        return errors
    if (
        not isinstance(skill_names, list)
        or not skill_names
        or not all(
            isinstance(v, str) and re.fullmatch(r"[a-z][a-z0-9-]*", v)
            for v in skill_names
        )
    ):
        errors.append("skill_names must be a non-empty list of kebab-case names")
        return errors
    if len(skill_names) != len(set(skill_names)):
        errors.append("skill_names contains duplicates")
    if not isinstance(entries, list):
        errors.append("findings must be a list")
        return errors

    declared: Counter[tuple[str, str]] = Counter()
    for index, entry in enumerate(entries):
        label = f"findings[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        path = entry.get("path")
        category = entry.get("category")
        classification = entry.get("classification")
        count = entry.get("count")
        if not _safe_relative(path):
            errors.append(f"{label}.path must be repository-relative")
            continue
        if category not in SUPPORTED_CATEGORIES:
            errors.append(f"{label}.category is unsupported")
        if classification not in ALLOWED_CLASSIFICATIONS:
            errors.append(f"{label}.classification is unsupported")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            errors.append(f"{label}.count must be a positive integer")
        if not isinstance(entry.get("owner"), str) or not entry.get("owner"):
            errors.append(f"{label} must name an owner")
        if not isinstance(entry.get("exit_condition"), str) or not entry.get(
            "exit_condition"
        ):
            errors.append(f"{label} must define an exit_condition")
        key = (path, category)
        if declared[key]:
            errors.append(f"duplicate inventory entry for {path}:{category}")
        elif isinstance(count, int):
            declared[key] = count
        if not (root / path).is_file():
            errors.append(f"stale inventory path not found: {path}")

    slash = _slash_pattern(skill_names)
    occurrences: list[dict[str, Any]] = []
    for scan_root in roots:
        base = root / scan_root
        if base.is_file():
            paths = [base]
        elif base.is_dir():
            paths = sorted(
                path
                for path in base.rglob("*")
                if path.is_file() and path.suffix in {".md", ".py", ".sh"}
            )
        else:
            errors.append(f"scan root not found: {scan_root}")
            continue
        for path in paths:
            relative = path.relative_to(root).as_posix()
            occurrences.extend(_scan_file(path, relative, slash))

    observed = Counter((item["path"], item["category"]) for item in occurrences)
    for key in sorted(observed.keys() | declared.keys()):
        actual = observed[key]
        expected = declared[key]
        if actual == expected:
            continue
        path, category = key
        errors.append(
            f"{path}:{category} inventory count mismatch: declared {expected}, observed {actual}"
        )
        for item in occurrences:
            if (item["path"], item["category"]) == key:
                errors.append(
                    f"  {item['path']}:{item['line']} [{item['category']}] {item['text']}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"runtime-neutral: {error}", file=sys.stderr)
        print(f"runtime-neutral: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(f"runtime-neutral: {INVENTORY} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
