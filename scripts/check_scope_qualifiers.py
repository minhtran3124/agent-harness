#!/usr/bin/env python3
"""List condition words that a prose rewrite dropped from a hunk. Advisory: always exits 0.

Usage: check_scope_qualifiers.py --base <ref> --head <ref>

Reads `git diff -U0 <base>..<head>` for changed `.md` files under skills/, rules/, agents/.
For each hunk and each condition word, prints one line when a removed line has the word
and no added line in the same hunk has it:

    - <file>:<old start>: dropped "<word>": <removed line, trimmed to 120 chars>

Prints `- none` when prose changed and nothing is listed. Prints nothing when no prose file
changed. On a git failure, prints one `scope-qualifiers: unavailable (<reason>)` line.

Verifies: a condition word (whole word, case-insensitive) present in a removed line of a hunk
is present in at least one added line of the same hunk.
Does not verify: that the condition still applies to the same sentences. A split that moves
sentences out of a condition's scope without removing the word (the pilot's feature-intake
Step 1 split) is not listed. It does not verify meaning, and it does not compare across hunks.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

PROSE_ROOTS = ("skills/", "rules/", "agents/")
WORDS = ("if", "unless", "only", "when", "never", "except", "for a new", "without")
PATTERNS = {word: re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) for word in WORDS}
HUNK = re.compile(r"^@@ -(\d+)")


# Pinned so the user's git config cannot change them: quoted paths, color, relative paths,
# external diff, textconv, hunk merging and prefixes. Every git call runs at the top level.
GIT_CONFIG = ("-c", "core.quotepath=false", "-c", "color.ui=never", "-c", "diff.relative=false")
DIFF_FLAGS = ("--no-color", "--no-ext-diff", "--no-textconv", "--inter-hunk-context=0",
              "--src-prefix=a/", "--dst-prefix=b/")


def git(*args: str, cwd: str | None = None) -> str:
    # surrogateescape: a file name that is not UTF-8 cannot stop the other files from being checked.
    return subprocess.run(["git", *GIT_CONFIG, *args], capture_output=True, text=True,
                          errors="surrogateescape", check=True, cwd=cwd).stdout


def hunks(diff: str):
    """Yield (file, old start, removed lines, added lines) for each hunk."""
    path, start, removed, added, in_header = None, None, [], [], True
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            if start is not None:
                yield path, start, removed, added
            path, start, removed, added, in_header = None, None, [], [], True
        elif in_header and line.startswith("+++ b/"):
            # Git adds a TAB after a path that has a space.
            path = line[len("+++ b/"):].removesuffix("\t")
        elif HUNK.match(line):
            if start is not None:
                yield path, start, removed, added
            start, removed, added, in_header = int(HUNK.match(line).group(1)), [], [], False
        elif not in_header and line.startswith("-"):
            removed.append(line[1:])
        elif not in_header and line.startswith("+"):
            added.append(line[1:])
    if start is not None:
        yield path, start, removed, added


def report(base: str, head: str) -> list[str]:
    # Root-relative names and pathspecs then agree from any working directory.
    top = git("rev-parse", "--show-toplevel").rstrip("\n")
    names = git("diff", "--name-only", "-z", "--no-renames", "--diff-filter=d",
                f"{base}..{head}", cwd=top).split("\0")
    paths = [name for name in names if name.endswith(".md") and name.startswith(PROSE_ROOTS)]
    if not paths:
        return []
    diff = git("diff", *DIFF_FLAGS, "-U0", "--no-renames", "--diff-filter=d", f"{base}..{head}", "--",
               *paths, cwd=top)
    lines = []
    for path, start, removed, added in hunks(diff):
        for word, pattern in PATTERNS.items():
            if any(pattern.search(line) for line in added):
                continue
            hit = next((line for line in removed if pattern.search(line)), None)
            if hit is not None:
                lines.append(f'- {path}:{start}: dropped "{word}": {hit.strip()[:120]}')
    return lines or ["- none"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    # A stdout encoding that cannot hold a character must not make the script exit 1.
    # sys.stdout is None when stdout is closed.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(errors="backslashreplace")
    try:
        lines = report(args.base, args.head)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        reason = exc.stderr if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        lines = [f"scope-qualifiers: unavailable ({' '.join(reason.split())})"]
    if lines:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
