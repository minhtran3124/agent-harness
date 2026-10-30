#!/usr/bin/env python3
"""Check a release-summary draft against its fact-list JSON.

Verifies:        every PR number in a citation group, "(#n)", "(#n, #m)", "(#n and #m)",
                 "(#n; #m)" or "(#n, m)", is a PR in the fact list (breaking and groups);
                 a group with prose, such as "(#1 priority item)", is not a citation, and a 4-digit number is a year;
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

PAREN = re.compile(r"\(([^()]*)\)")
SEP = re.compile(r"\s*(?:,|;|\band\b)\s*")
PR_TOKEN = re.compile(r"#(\d+)")
BARE = re.compile(r"\d+")
TODO = "[NEEDS HUMAN]"
ACTION = "What you need to do:"


def pr_set(facts: dict) -> set[int]:
    items = list(facts.get("breaking", []))
    for group in facts.get("groups", {}).values():
        items.extend(group)
    return {i["pr"] for i in items if isinstance(i.get("pr"), int)}


def citations(text: str) -> list[int]:
    """PR numbers of every citation group in text.

    A parenthesised group is a citation only when every token is a PR token
    (#n) or, after the first, a bare number; the first token must be #n. A bare
    number of 4+ digits is a year and is ignored. Prose in the group makes it
    not a citation.
    """
    found: list[int] = []
    for m in PAREN.finditer(text):
        tokens = [t for t in SEP.split(m.group(1).strip()) if t]
        if not tokens or not PR_TOKEN.fullmatch(tokens[0]):
            continue
        if not all(PR_TOKEN.fullmatch(t) or BARE.fullmatch(t) for t in tokens):
            continue
        for t in tokens:
            digits = t.lstrip("#")
            if t.startswith("#") or len(digits) <= 3:
                found.append(int(digits))
    return found


def check(facts: dict, draft: str) -> list[str]:
    errors: list[str] = []
    prs = pr_set(facts)
    for n in sorted(set(citations(draft))):
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
        if not citations(stripped) and TODO not in stripped:
            errors.append(f"line {idx + 1}: bullet has no (#n) and no {TODO}")
        top_level = not line.startswith((" ", "\t"))
        if section == "breaking changes" and top_level:
            listed.update(citations(stripped))
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
