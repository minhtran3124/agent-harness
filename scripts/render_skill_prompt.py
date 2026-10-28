#!/usr/bin/env python3
"""Compose isolated-subagent prompts and validate contextual policy delivery."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


CONTEXT_MATRIX = {
    "implementer": {
        "path": "skills/implement/implementer-prompt.md",
        "required": ["Deviations:"],
    },
    "intent-controller": {
        "path": "skills/intent-review/SKILL.md",
        "required": [],
        "rationale": "Plan-blind by design: the reviewer gets only the request and the diff range, so it receives no rules or plan text.",
    },
}


def read(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"missing fragment: {path}")
    return path.read_text(encoding="utf-8").strip()


def render(fragments: list[Path], values: dict[str, str]) -> str:
    parts = []
    for path in fragments:
        text = read(path)
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        if "{{" in text or "}}" in text:
            raise ValueError(f"unresolved placeholder in {path}")
        parts.append(f"<!-- source: {path.as_posix()} -->\n{text}")
    return "\n\n".join(parts) + "\n"


def check_all(root: Path) -> list[str]:
    errors = []
    for context, spec in CONTEXT_MATRIX.items():
        path = root / spec["path"]
        if not path.is_file():
            errors.append(f"missing context source: {context} -> {spec['path']}")
            continue
        text = path.read_text(encoding="utf-8")
        required = spec["required"]
        if not required and not spec.get("rationale"):
            errors.append(f"empty delivery has no rationale: {context}")
        for token in required:
            if token not in text:
                errors.append(
                    f"missing required policy delivery: {context} -> {spec['path']} -> {token}"
                )
        for token in spec.get("required_reads", []):
            read_pattern = re.compile(rf"\bRead\b[^\n]*`{re.escape(token)}`")
            if not read_pattern.search(text):
                errors.append(
                    f"missing required policy Read: {context} -> {spec['path']} -> {token}"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragment", type=Path, action="append", default=[])
    parser.add_argument("--values", type=Path)
    parser.add_argument("--check-all", action="store_true")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    args = parser.parse_args()
    try:
        if args.check_all:
            errors = check_all(args.root.resolve())
            if errors:
                for error in errors:
                    print(f"prompt-compose: {error}", file=sys.stderr)
                return 1
            print("prompt-compose: all contracts present")
            return 0
        if not args.fragment:
            parser.error("provide --fragment or --check-all")
        values = json.loads(args.values.read_text()) if args.values else {}
        if not isinstance(values, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in values.items()
        ):
            raise ValueError("--values must be a JSON object of strings")
        print(render(args.fragment, values), end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"prompt-compose: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
