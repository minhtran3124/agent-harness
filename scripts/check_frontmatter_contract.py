#!/usr/bin/env python3
"""Enforce the frontmatter fields the Claude Code runtime needs to load a skill or agent.

Driven by harness-manifest.json's `skills` and `agents` registers — the same source of truth
check_manifest.py uses — so there is no allowlist and no path heuristic. agents/README.md,
agents/PROJECT.md and agents/PROJECT.template.md are simply not registered, which is exactly
why they are not agents; nothing has to be exempted by name.

Verifies:        every REGISTERED skill and agent has a frontmatter block whose `name:` and
                 `description:` are present and non-empty, and whose `name:` matches the
                 register key. A skill with no `description:` never appears in the model's
                 skill list, so it silently stops being invocable.
Does not verify: that a description is GOOD (it routes well), or that a body matches its
                 frontmatter. Description length has its own ceiling in
                 scripts/audit_skill_prompts.py; `allowed-tools` presence is
                 scripts/check-allowed-tools.sh. This is traceability tier: fields exist and
                 parse. It deliberately does not re-check manifest<->disk presence — that is
                 check_manifest.py section A, and duplicating it would create two places to
                 fix the same drift.

Why this and not `claude plugin validate --strict`: that validator models the repo as a
packaged marketplace plugin (this repo has no `.claude-plugin/`, so it reports
`manifest: null`) and classifies every *.md under agents/ as an agent, which costs a
three-file allowlist of permanent blind spots to suppress. It is also an external CLI that
CI runners do not ship, so it can never gate a pull request. This check reaches the same
load-bearing coverage with stdlib only, and runs everywhere.

Stdlib only (no pyyaml) so CI needs no extra dependency — same constraint as check_manifest.py.

Exit 0 = every registered component carries the contract. Exit 1 = one
"frontmatter: ..." line per problem.
Run: python3 scripts/check_frontmatter_contract.py [--root DIR]
"""

import argparse
import re
import json
import sys
from pathlib import Path

REQUIRED = ("name", "description")


def frontmatter(text: str) -> str | None:
    """Return the frontmatter block, or None when the file does not open with one.

    A file must start with a `---` line and close with a later `---` line. An unterminated
    block returns None rather than the whole file: treating the body as frontmatter is how a
    grep-based check comes to accept a `description:` that is really prose (the failure mode
    recorded against the awk parser in scripts/check-allowed-tools.sh).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return None


def field(block: str, key: str) -> str | None:
    """Return a top-level scalar field's value, or None when absent.

    Handles the three shapes that appear in this repo: a plain scalar, a quoted scalar, and a
    block scalar (`>` or `|`) whose content is on following indented lines. Only column-0 keys
    count, so a `description:` nested inside another mapping is not mistaken for the real one.
    """
    pattern = rf"^{re.escape(key)}:(.*)$"
    match = re.search(pattern, block, re.MULTILINE)
    if match is None:
        return None
    value = match.group(1).strip()
    if value in (">", "|", ">-", "|-", ">+", "|+"):
        # Block scalar: the value is the indented continuation lines that follow.
        tail = block[match.end() :].splitlines()
        collected = []
        for line in tail:
            if line.strip() == "":
                continue
            if not line.startswith((" ", "\t")):
                break
            collected.append(line.strip())
        return " ".join(collected)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    return value


def check(root: Path) -> int:
    problems: list[str] = []

    manifest_path = root / "harness-manifest.json"
    if not manifest_path.is_file():
        print(
            f"frontmatter: harness-manifest.json not found at {root}",
            file=sys.stderr,
        )
        return 1
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        print(
            f"frontmatter: harness-manifest.json is invalid JSON: {e}", file=sys.stderr
        )
        return 1

    registered: list[tuple[str, Path]] = []
    for name in manifest.get("skills", []):
        registered.append((name, root / "skills" / name / "SKILL.md"))
    for name in manifest.get("agents", []):
        registered.append((name, root / "agents" / f"{name}.md"))

    if not registered:
        # Fail closed. A manifest with empty registers would otherwise make this check pass
        # while inspecting nothing, which is indistinguishable from a real pass.
        print(
            "frontmatter: harness-manifest.json registers no skills or agents "
            "(nothing to check — refusing to report clean)",
            file=sys.stderr,
        )
        return 1

    checked = 0
    for name, path in registered:
        rel = path.relative_to(root)
        if not path.is_file():
            # Presence is check_manifest.py's job; skip quietly so one missing file does not
            # produce the same complaint from two checkers.
            continue
        checked += 1
        block = frontmatter(path.read_text())
        if block is None:
            problems.append(f"frontmatter: {rel} has no frontmatter block")
            continue
        for key in REQUIRED:
            value = field(block, key)
            if value is None:
                problems.append(f"frontmatter: {rel} is missing `{key}:`")
            elif value == "":
                problems.append(f"frontmatter: {rel} has an empty `{key}:`")
        actual = field(block, "name")
        if actual not in (None, "", name):
            problems.append(
                f"frontmatter: {rel} declares `name: {actual}` but is registered as `{name}`"
            )

    if problems:
        print("  ✗ frontmatter contract:", file=sys.stderr)
        for line in problems:
            print(f"      {line}", file=sys.stderr)
        print(
            "      A registered skill or agent without a non-empty name and description "
            "is not loadable by the runtime.",
            file=sys.stderr,
        )
        return 1

    print(
        f"  ✓ frontmatter contract: {checked} registered skill(s)/agent(s) carry name + description"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parent.parent,
        type=Path,
        help="repository root (default: the parent of scripts/)",
    )
    args = parser.parse_args()
    return check(args.root)


if __name__ == "__main__":
    sys.exit(main())
