#!/usr/bin/env python3
"""Assert every command a skill's own prose instructs is permitted by its `allowed-tools`.

This is the check whose absence let five of nine skills ship under-granted in the
`allowed-tools` rollout: `check-allowed-tools.sh` proves the field is PRESENT, and
`claude plugin validate` was measured to ignore tool names entirely, so nothing compared a
declared list against the skill's own body. An under-granted skill fails only at runtime, in
the middle of a real task.

Verifies:        for every registered skill, each runnable shell command in its own Markdown
                 (SKILL.md and references/*.md — NOT *prompt*.md or subagents/, which are
                 dispatch payloads run under a SUBAGENT's grant) is matched by at least one
                 declared `Bash(...)` pattern, and each mandated dispatch of a named
                 *prompt*.md has `Agent` or `Task`. Frontmatter is excluded from both scans.
Does not verify: that a list is not OVER-granted, that a skill succeeds end to end, or that
                 prose implying a file write declares `Write`/`Edit` — natural-language write
                 detection is too noisy to gate on, and is deliberately excluded rather than
                 guessed. This is traceability tier over the body text; it does not execute
                 anything.

Extraction reuses scripts/lint-skill-bash.sh's convention so the two agree: a fenced bash
block carrying a `<placeholder>` or `[optional]` is documentation, not a runnable script, and
is skipped.

Path note: deploy-harness.sh rewrites helper paths in derived docs (`scripts/x.py` becomes
`.claude/scripts/x.py`), so a pattern is matched against both the literal command and its
`.claude/`-stripped form. A source-tree grant therefore stays correct after deployment.

Stdlib only. Exit 0 = every instructed command is permitted. Exit 1 = one line per gap.
Run: python3 scripts/check_skill_tool_conformance.py [--root DIR]
"""

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

# A block that documents a shape rather than a command to run.
ILLUSTRATIVE = ("<", "[optional]")

# Heads that mean "this line is a shell command", used for inline `...` spans. Anything else
# in backticks is a path, a field name, or prose, and must not be treated as a command.
COMMAND_HEADS = (
    "python3",
    "python",
    "bash",
    "sh",
    "git",
    "ls",
    "cat",
    "grep",
    "rg",
)

# A bare "dispatch" is domain vocabulary here ("dispatch prompts" as a noun, and prohibitions
# like "do not dispatch"). Measured on the live tree, the bare word produced 3 false positives
# and 0 true ones, so the object is required: a dispatch names a backticked *prompt*.md.
DISPATCH = re.compile(r"[Dd]ispatch(?:es|ing)?\s+`[^`]*prompt[^`]*\.md`")
DISPATCH_TOOLS = ("Agent", "Task")

# A shell command whose job a native tool already does does not need a Bash grant when that
# tool is declared: the skill can simply use the tool.
NATIVE_EQUIVALENT = {"grep": "Grep", "rg": "Grep", "ls": "Glob", "cat": "Read"}


def frontmatter(text: str) -> str | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return None


def declared_tools(block: str) -> tuple[set[str], list[str], bool]:
    """Return (bare tool names, Bash(...) patterns, bash_is_unrestricted)."""
    match = re.search(r"^allowed-tools:(.*)$", block, re.MULTILINE)
    if match is None:
        return set(), [], False
    raw = match.group(1).strip()
    # Split on commas that are not inside parentheses: `Bash(a, b)` stays one entry.
    entries, depth, current = [], 0, ""
    for ch in raw:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            entries.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        entries.append(current.strip())

    bare: set[str] = set()
    patterns: list[str] = []
    unrestricted = False
    for entry in entries:
        paren = re.match(r"^Bash\((.*)\)$", entry)
        if paren:
            patterns.append(paren.group(1).strip())
        elif entry == "Bash":
            unrestricted = True
        elif entry:
            bare.add(entry)
    return bare, patterns, unrestricted


def commands(text: str) -> list[tuple[int, str]]:
    """Return (line number, command) for every runnable shell command the text instructs."""
    found: list[tuple[int, str]] = []
    lines = text.splitlines()

    in_block = False
    block_lines: list[tuple[int, str]] = []
    for number, line in enumerate(lines, start=1):
        fence = line.strip().startswith("```")
        if fence and not in_block:
            in_block = line.strip().lower() in ("```bash", "```sh", "```shell")
            block_lines = []
            continue
        if fence and in_block:
            body = "\n".join(text for _, text in block_lines)
            if not any(token in body for token in ILLUSTRATIVE):
                for n, t in block_lines:
                    stripped = t.strip()
                    if stripped and not stripped.startswith("#"):
                        found.append((n, stripped))
            in_block = False
            continue
        if in_block:
            block_lines.append((number, line))
            continue
        # Inline: a backticked span that names a command. A `<placeholder>` in an ARGUMENT
        # does not make it illustrative — `python3 x.py specs/<slug>/PLAN.md` is a real
        # instruction, and filtering the whole span on "<" silently lost it (measured: two
        # of the five known under-grants went undetected until this was narrowed to the head).
        for span in re.findall(r"`([^`]+)`", line):
            span = span.strip()
            is_command = span.startswith(COMMAND_HEADS) or span.endswith((".sh", ".py"))
            if not is_command:
                continue
            if any(t in head(span) for t in ILLUSTRATIVE):
                continue
            found.append((number, span))
    return found


def head(command: str) -> str:
    """The portion permission matching keys on: up to the first pipe, chain, or redirect."""
    return re.split(r"[|;&><]|\&\&", command)[0].strip()


def permitted(
    command: str, patterns: list[str], unrestricted: bool, bare: set[str]
) -> bool:
    if unrestricted:
        return True
    target = head(command)

    # A native tool can stand in for its shell equivalent (`grep` -> the Grep tool).
    native = NATIVE_EQUIVALENT.get(target.split()[0] if target.split() else "")
    if native and native in bare:
        return True

    variants = {target, target.replace(".claude/", "")}
    # A script named without an interpreter is run either way; both spellings must be granted.
    if target.endswith((".sh", ".py")) or " " not in target:
        variants |= {f"bash {v}" for v in list(variants)} | {
            f"python3 {v}" for v in list(variants)
        }
    for pattern in patterns:
        # `Bash(git diff *)` grants `git diff` itself, not only `git diff <something>`.
        candidates = {pattern, pattern + "*"}
        if pattern.endswith(" *"):
            candidates.add(pattern[:-2])
        for variant in variants:
            if any(fnmatch.fnmatch(variant, c) for c in candidates):
                return True
    return False


def check(root: Path) -> int:
    manifest_path = root / "harness-manifest.json"
    if not manifest_path.is_file():
        print(
            f"conformance: harness-manifest.json not found at {root}", file=sys.stderr
        )
        return 1
    manifest = json.loads(manifest_path.read_text())
    names = manifest.get("skills", [])
    if not names:
        print(
            "conformance: no skills registered — refusing to report clean",
            file=sys.stderr,
        )
        return 1

    problems: list[str] = []
    checked_skills = checked_commands = 0

    for name in names:
        skill_dir = root / "skills" / name
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        block = frontmatter(skill_md.read_text())
        if block is None:
            continue
        bare, patterns, unrestricted = declared_tools(block)
        if not bare and not patterns and not unrestricted:
            # Presence is check-allowed-tools.sh's job; nothing to compare against here.
            continue
        checked_skills += 1

        docs = [skill_md] + sorted((skill_dir / "references").glob("*.md"))
        for doc in docs:
            raw = doc.read_text()
            # Blank the frontmatter rather than slicing it off: slicing shifts every reported
            # line number, and a finding that points at the wrong line is worse than none.
            fm = frontmatter(raw)
            if fm is None:
                text = raw
            else:
                blanked = ["", *([""] * len(fm.splitlines())), ""]
                text = "\n".join(blanked + raw.splitlines()[len(fm.splitlines()) + 2 :])
            rel = doc.relative_to(root)
            for number, command in commands(text):
                checked_commands += 1
                if not permitted(command, patterns, unrestricted, bare):
                    problems.append(
                        f"conformance: {rel}:{number} instructs `{head(command)}` "
                        f"but {name} declares no matching Bash(...) pattern"
                    )
            if DISPATCH.search(text) and not (bare & set(DISPATCH_TOOLS)):
                line = next(
                    (
                        i
                        for i, t in enumerate(text.splitlines(), 1)
                        if DISPATCH.search(t)
                    ),
                    1,
                )
                problems.append(
                    f"conformance: {rel}:{line} mandates a subagent dispatch "
                    f"but {name} declares neither Agent nor Task"
                )

    if problems:
        print("  ✗ skill tool conformance:", file=sys.stderr)
        for line in sorted(set(problems)):
            print(f"      {line}", file=sys.stderr)
        print(
            "      Widen the skill's allowed-tools, or stop instructing the command. "
            "An under-granted skill breaks mid-task at runtime.",
            file=sys.stderr,
        )
        return 1

    print(
        f"  ✓ skill tool conformance: {checked_commands} instructed command(s) "
        f"across {checked_skills} skill(s) are all permitted"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", default=Path(__file__).resolve().parent.parent, type=Path
    )
    args = parser.parse_args()
    return check(args.root)


if __name__ == "__main__":
    sys.exit(main())
