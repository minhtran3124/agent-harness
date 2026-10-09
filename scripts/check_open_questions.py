#!/usr/bin/env python3
"""Warn when a spec slug ships while an open question in a QUESTIONS.md register closes at it.

A register is an optional `specs/<slug>/QUESTIONS.md` (shape: templates/QUESTIONS.template.md)
of non-blocking open questions, one `## OQ-<n>` block each. Every `specs/*/QUESTIONS.md` under
the root is read, because a question in a parent spec usually closes at a child phase's slug.

Verifies:        when slug X ships, no block with `status: open` names X in `closes-at`
                 (`X` or `X#<task>`; `X-other` does not match), and every block in every
                 register is well-formed (required fields present and non-empty, `status` and
                 `decided-by` in their value sets, a `closes-at` of `<slug>` or `<slug>#<task>`,
                 `closed-by` on a closed block, no duplicate `OQ-<n>` in one file, no
                 repeated field in one block, and no heading naming `OQ-` that is not
                 exactly `## OQ-<n>`).
Does not verify: that a closed question was answered correctly, or that its `closed-by`
                 evidence is true. Tier: traceability.

`--root` defaults to the current directory, never to this script's location: the deployed copy
lives in `<consumer>/.claude/scripts/`, whose parent holds no `specs/`.

Stdlib only. Findings go to stderr. Exit 0 = no findings, or findings under the default warn
mode; exit 1 = findings and REQUIRE_QUESTIONS_CLOSED=1; exit 2 = usage error (no --slug).
Run: python3 scripts/check_open_questions.py --slug <slug> [--root DIR]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Any heading naming an OQ, at any depth or case, so a near miss (`### OQ-1`, `##OQ-1`,
# `## oq-1`) is reported as malformed instead of silently dropping its block.
HEADING = re.compile(r"^#+\s*OQ-", re.IGNORECASE)
VALID_HEADING = re.compile(r"^##\s+OQ-([1-9][0-9]*)\s*$")
FIELD = re.compile(r"^-\s+([a-z-]+):(.*)$")
CLOSES_AT = re.compile(r"^[^\W_](?:[\w.-]*[^\W_])?(?:#[\w.-]*[^\W_])?$")
REQUIRED = ("raised-by", "closes-at", "decided-by", "default-until-closed", "status")
FIELDS = REQUIRED + ("closed-by",)
DECIDED_BY = ("measurement", "owner")
STATUS = ("open", "closed")


def parse(text: str) -> tuple[list[tuple[str, dict[str, str], list[str]]], list[str]]:
    """Return (blocks as (id, fields, duplicated field names), defects found while splitting).

    A repeated field keeps its first value for matching; the repeat is returned so the
    caller reports it rather than one value silently winning.
    """
    blocks: list[tuple[str, dict[str, str], list[str]]] = []
    defects: list[str] = []
    current: dict[str, str] | None = None
    repeats: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("#"):
            current = None
            if HEADING.match(line):
                match = VALID_HEADING.match(line)
                if match is None:
                    defects.append(f"line {number}: heading is not '## OQ-<n>': {line.strip()}")
                else:
                    current, repeats = {}, []
                    blocks.append((f"OQ-{match.group(1)}", current, repeats))
            continue
        field = FIELD.match(line.strip())
        if current is not None and field and field.group(1) in FIELDS:
            name = field.group(1)
            if name in current:
                repeats.append(name)
            else:
                current[name] = field.group(2).strip()
    return blocks, defects


def check(register: Path, rel: str, slug: str) -> list[str]:
    try:
        # utf-8-sig drops a leading byte-order mark, which would otherwise hide a `## OQ-1`
        # on line 1 from the heading match.
        text = register.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        return [f"{rel}: unreadable register: {error}"]

    blocks, defects = parse(text)
    findings = [f"{rel}: {defect}" for defect in defects]
    seen: set[str] = set()
    for oq, fields, repeats in blocks:
        problems = []
        if oq in seen:
            problems.append(f"duplicate {oq} in this file")
        seen.add(oq)
        problems += [f"duplicate field {name}" for name in repeats]
        problems += [f"missing or empty {key}" for key in REQUIRED if not fields.get(key)]
        decided_by, status = fields.get("decided-by"), fields.get("status")
        closes_at = fields.get("closes-at", "")
        if decided_by and decided_by not in DECIDED_BY:
            problems.append(f"decided-by must be measurement or owner, got {decided_by!r}")
        if status and status not in STATUS:
            problems.append(f"status must be open or closed, got {status!r}")
        if closes_at and not CLOSES_AT.match(closes_at):
            problems.append(f"closes-at must be <slug> or <slug>#<task>, got {closes_at!r}")
        if status == "closed" and not fields.get("closed-by"):
            problems.append("closed block has no closed-by")
        findings += [f"{rel}: {oq}: malformed: {problem}" for problem in problems]

        if status == "open" and (closes_at == slug or closes_at.startswith(slug + "#")):
            default = fields.get("default-until-closed", "")
            findings.append(
                f"{rel}: {oq}: open question closes at {closes_at}; "
                f"default-until-closed: {default}"
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slug", required=True, help="the spec slug that is shipping")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    args = parser.parse_args()
    if not args.slug.strip():
        parser.error("--slug must not be empty")

    findings: list[str] = []
    for register in sorted(args.root.glob("specs/*/QUESTIONS.md")):
        rel = register.relative_to(args.root).as_posix()
        findings += check(register, rel, args.slug.strip())
    if not findings:
        return 0

    for finding in findings:
        print(finding, file=sys.stderr)
    if os.environ.get("REQUIRE_QUESTIONS_CLOSED") == "1":
        return 1
    print(
        f"{len(findings)} open-question finding(s); warn-only "
        "(set REQUIRE_QUESTIONS_CLOSED=1 to block).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
