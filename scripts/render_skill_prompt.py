#!/usr/bin/env python3
"""Compose isolated-subagent prompts and validate contextual policy delivery."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


CONTEXT_MATRIX = {
    "main.plan-author": {
        "path": "skills/writing-plans/SKILL.md",
        "required": ["rules/plan-format.md", "rules/terminology.md"],
        "required_reads": ["rules/terminology.md"],
    },
    "main.research-author": {
        "path": "skills/xia2/SKILL.md",
        "required": ["rules/terminology.md"],
        "required_reads": ["rules/terminology.md"],
    },
    "main.summary-author": {
        "path": "skills/feature-intake/SKILL.md",
        "required": ["rules/terminology.md"],
        "required_reads": ["rules/terminology.md"],
    },
    "main.plan-executor": {
        "path": "skills/subagent-driven-development/SKILL.md",
        "required": [
            "rules/plan-format.md",
            "rules/wave-parallelism.md",
            "rules/auto-correct-scope.md",
            "rules/terminology.md",
        ],
        "required_reads": ["rules/terminology.md"],
    },
    "implementer": {
        "path": "skills/subagent-driven-development/implementer-prompt.md",
        "required": ["rules/auto-correct-scope.md"],
    },
    "task-reviewer": {
        "path": "skills/subagent-driven-development/task-reviewer-prompt.md",
        "required": [],
        "rationale": "Consumes a normalized task brief and review package; it does not parse plan syntax or route fixes.",
    },
    "plan-document-reviewer": {
        "path": "skills/writing-plans/plan-document-reviewer-prompt.md",
        "required": ["rules/plan-format.md", "rules/terminology.md"],
        "required_reads": ["rules/terminology.md"],
    },
    "correctness-controller": {
        "path": "skills/correctness-review/SKILL.md",
        "required": ["rules/auto-correct-scope.md"],
    },
    "correctness-reviewer": {
        "path": "skills/correctness-review/prompts/shared.md",
        "required": ["rules/auto-correct-scope.md"],
    },
    "correctness-scorer": {
        "path": "skills/correctness-review/correctness-scorer-prompt.md",
        "required": [],
        "rationale": "Scores evidence only; Rule classification and fix routing occur after scoring in the controller.",
    },
    "intent-controller": {
        "path": "skills/intent-review/SKILL.md",
        "required": ["rules/auto-correct-scope.md"],
    },
    "resume": {
        "path": "skills/subagent-driven-development/references/resume.md",
        "required": ["rules/plan-format.md", "rules/wave-parallelism.md"],
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

    config = root / "skills/correctness-review/review-config.json"
    try:
        data = json.loads(read(config))
        angles = data.get("finder_angles")
        if not isinstance(angles, list) or len(set(angles)) != 6:
            errors.append("invalid correctness finder-angle config")
        if data.get("default_threshold") != 75 or data.get("minimum_threshold") != 60:
            errors.append("invalid correctness threshold config")
    except (ValueError, json.JSONDecodeError):
        errors.append("missing or unreadable correctness review config")
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
