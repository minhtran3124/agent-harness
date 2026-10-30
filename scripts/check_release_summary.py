#!/usr/bin/env python3
"""Check a release-summary draft against its fact-list JSON.

Verifies:        every (#n) in the draft is a PR in the fact list (breaking and groups);
                 every bullet under "## Breaking changes" has an indented
                 "What you need to do:" line; every PR in the fact list's `breaking` array is a bullet there;
                 every other bullet cites (#n) or carries
                 [NEEDS HUMAN]. Tier: traceability.
Does not verify: that a statement is true to its PR, or the tone.
Run: python3 scripts/check_release_summary.py <fact-list.json> <draft.md>
Exit: 0 pass, 1 a check failed, 2 bad usage or unreadable input.
"""
from __future__ import annotations

import json
import re
import sys

CITE = re.compile(r"\((#\d+(?:\s*,\s*#\d+)*)[^)]*\)")
NUM = re.compile(r"\d+")
TODO = "[NEEDS HUMAN]"
ACTION = "What you need to do:"


def pr_set(facts: dict) -> set[int]:
    items = list(facts.get("breaking", []))
    for group in facts.get("groups", {}).values():
        items.extend(group)
    return {i["pr"] for i in items if isinstance(i.get("pr"), int)}


def check(facts: dict, draft: str) -> list[str]:
    errors: list[str] = []
    prs = pr_set(facts)
    for n in sorted({int(n) for c in CITE.findall(draft) for n in NUM.findall(c)}):
        if n not in prs:
            errors.append(f"(#{n}) is not a PR in the fact list")
    lines = draft.splitlines()
    section = ""
    listed: set[int] = set()
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        if stripped[2:].startswith(ACTION):
            continue
        if not CITE.search(stripped) and TODO not in stripped:
            errors.append(f"line {idx + 1}: bullet has no (#n) and no {TODO}")
        top_level = not line.startswith((" ", "\t"))
        if section == "breaking changes" and top_level:
            listed.update(int(n) for c in CITE.findall(stripped) for n in NUM.findall(c))
            nxt = next((l for l in lines[idx + 1:] if l.strip()), "")
            if not (nxt.startswith((" ", "\t")) and nxt.strip().startswith(ACTION)):
                errors.append(f"line {idx + 1}: breaking item has no '{ACTION}' line")
    for item in facts.get("breaking", []):
        pr = item.get("pr")
        if isinstance(pr, int) and pr not in listed:
            errors.append(f"breaking PR (#{pr}) is not a bullet under 'Breaking changes'")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.split("Run: ")[1].splitlines()[0], file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            facts = json.load(f)
        with open(argv[2], encoding="utf-8") as f:
            draft = f.read()
    except (OSError, ValueError) as e:
        print(f"check_release_summary: {e}", file=sys.stderr)
        return 2
    errors = check(facts, draft)
    for e in errors:
        print(f"FAIL {e}")
    if errors:
        return 1
    print("release-summary: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
