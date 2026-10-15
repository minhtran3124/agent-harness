#!/usr/bin/env python3
"""Compare the STE hard count of each prose file with its baseline. Warn only.

The script lints every `skills/*/*.md`, `skills/*/*/*.md`, `rules/*.md` and `agents/*.md` file
with `skills/asd-ste100/scripts/ste-lint.py --json`. It reads the `hard_count` field. Advisory
findings do not count. It compares each count with `scripts/ste-baseline.json` and prints:

  WARN <file>: hard <n> > baseline <b>     the file got worse (a missing entry has baseline 0)
  WARN <file>: in baseline, file is gone   remove the entry with --update
  NOTE <file>: hard <n> < baseline <b>     the file got better, lower the entry with --update
  ste-baseline: skipped (<reason>)         the linter, git, or the baseline file did not work

Verifies:        each prose file's hard count is not above its baseline entry, and each
                 baseline entry names a file that exists. With --against, the baseline entry
                 is the one in the baseline file at that git ref. Tier: traceability.
Does not verify: that the prose is good STE. The linter checks structure only. It does not
                 check advisory findings, meaning, or files outside the four globs. With
                 --against, it does not verify that the ref is the correct start point.

The default run always exits 0. It never blocks a build or a commit. `--strict` exits 1 when a
WARN line prints, and exits 1 when the run is skipped. Only SC-6, task Done checks, and tests
use `--strict`. `--against <git-ref>` reads the baseline file at that ref with
`git -C <root> show <ref>:scripts/ste-baseline.json`, not from the tree. Use it with or
without `--strict`. It cannot be used with `--update` (exit 2). `--update` rewrites the
baseline file from the current tree. `--root` sets the tree to lint. The default is the parent
of this script's directory, so the current directory has no effect.
Run: python3 scripts/check_ste_baseline.py [--strict | --update] [--against REF] [--root DIR]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

GLOBS = ("skills/*/*.md", "skills/*/*/*.md", "rules/*.md", "agents/*.md")
LINTER = "skills/asd-ste100/scripts/ste-lint.py"
BASELINE = "scripts/ste-baseline.json"

# Rules that the check and --update both silence.
# Rule: disable a rule only when most sampled hard findings are false positives on tables or
# inline code. On 2026-10-14 we sampled up to 5 hard findings per rule across the 72 files:
#   long-sentence (171 hits): 5 of 5 true. One is a long table cell, which is still long.
#   semicolon (327 hits): 5 of 5 true. One is in a table cell. The linter skips inline code.
#   synonym-rotation (40 hits): 3 of 5 true. 2 are doubtful (a field name, an example file).
#   phrasal-verb (5), nominalization (3), marketing-adjective (7): all hits are in
#     skills/asd-ste100, which quotes the bad words as examples. These are mentions, not
#     table or inline-code errors. The per-file baseline holds them, so the rules stay on.
# No rule has mostly false findings on tables or inline code, so that test disables none.
# User decision of 2026-10-15: disable synonym-rotation for a different reason. Test H3
# measured no effect for the one-word rule (specs/ste-terminology-evidence/DECISION.md).
# A rule with a measured null must not block, so the counts do not include it.
DISABLED_RULES: tuple[str, ...] = ("synonym-rotation",)


class Skip(Exception):
    """The linter or the baseline file did not give usable data."""


def prose_files(root: Path) -> list[str]:
    found = {p.relative_to(root).as_posix() for g in GLOBS for p in root.glob(g) if p.is_file()}
    return sorted(found)


def hard_count(root: Path, rel: str) -> int:
    cmd = [sys.executable, str(root / LINTER), "--json",
           "--disable", ",".join(DISABLED_RULES), rel]
    try:
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Skip(f"linter did not run on {rel}: {exc}") from exc
    # The linter exits 1 when the hard count is above its own --baseline. That is not a crash.
    if result.returncode not in (0, 1):
        raise Skip(f"linter exit {result.returncode} on {rel}: {result.stderr.strip()[:200]}")
    try:
        count = json.loads(result.stdout)["hard_count"]
    except (ValueError, KeyError, TypeError) as exc:
        raise Skip(f"linter gave invalid JSON on {rel}") from exc
    if not isinstance(count, int):
        raise Skip(f"linter gave a hard_count that is not an integer on {rel}")
    return count


def read_baseline_text(root: Path, ref: str | None) -> str:
    if ref is None:
        try:
            return (root / BASELINE).read_text(encoding="utf-8")
        # ValueError includes UnicodeDecodeError (a file that is not UTF-8).
        except (OSError, ValueError) as exc:
            raise Skip(f"cannot read {BASELINE}: {exc}") from exc
    cmd = ["git", "-C", str(root), "show", f"{ref}:{BASELINE}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise Skip(f"git show did not run for {ref}: {exc}") from exc
    if result.returncode != 0:
        raise Skip(f"cannot read {BASELINE} at {ref}: {result.stderr.strip()[:200]}")
    return result.stdout


def load_baseline(root: Path, ref: str | None = None) -> dict[str, int]:
    text = read_baseline_text(root, ref)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise Skip(f"cannot read {BASELINE}: {exc}") from exc
    if not isinstance(data, dict):
        raise Skip(f"{BASELINE} is not a JSON object")
    for rel, value in data.items():
        # A bool is an int subclass in Python. Reject it too.
        if not isinstance(value, int) or isinstance(value, bool):
            raise Skip(f"{BASELINE} entry {rel} is not an integer")
    return data


def compare(counts: dict[str, int], baseline: dict[str, int]) -> list[str]:
    lines = []
    for rel, hard in counts.items():
        base = baseline.get(rel, 0)
        if hard > base:
            lines.append(f"WARN {rel}: hard {hard} > baseline {base}")
        elif hard < base:
            lines.append(f"NOTE {rel}: hard {hard} < baseline {base} (lower it with --update)")
    for rel in sorted(set(baseline) - set(counts)):
        lines.append(f"WARN {rel}: in baseline, file is gone (remove it with --update)")
    return lines


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--strict", action="store_true", help="exit 1 when a WARN line prints")
    mode.add_argument("--update", action="store_true", help="rewrite the baseline file")
    parser.add_argument("--against", metavar="REF",
                        help="compare with the baseline file at this git ref")
    args = parser.parse_args(argv)
    if args.update and args.against is not None:
        parser.error("--against cannot be used with --update")
    # An empty ref makes `git show :path` read the staged copy, which is not a pinned ref.
    if args.against is not None and not args.against.strip():
        parser.error("--against needs a git ref, not an empty value")
    root = args.root.resolve()
    try:
        counts = {rel: hard_count(root, rel) for rel in prose_files(root)}
        if args.update:
            (root / BASELINE).write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n",
                                         encoding="utf-8")
            print(f"ste-baseline: wrote {len(counts)} entries to {BASELINE}")
            return 0
        lines = compare(counts, load_baseline(root, args.against))
    except Skip as exc:
        print(f"ste-baseline: skipped ({exc})")
        return 1 if args.strict else 0
    for line in lines:
        print(line)
    warnings = sum(line.startswith("WARN ") for line in lines)
    print(f"ste-baseline: {len(counts)} files checked, {warnings} above baseline or gone")
    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
