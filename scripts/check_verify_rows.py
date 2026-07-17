#!/usr/bin/env python3
"""Lint the `### Verify` table rows in spec SUMMARY.md files.

Enforces the two rules a Verify row must obey so it survives machine re-execution
(docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md):

  1. PIPE-FREE — the `### Verify` table is parsed by splitting each row on `|`
     (verify_summary.py). An unescaped `|` in a command splits the cell (the row
     then has the wrong column count); an escaped `\\|` survives but still means the
     command uses a pipe. Either way: rewrite pipe-free (`grep -e a -e b`,
     `X; a=$?; test -a`, redirect instead of `| wc`).
  2. UNDER 60s — ci-strict-gate.sh re-runs each Verify command under a 60s
     per-command cap (= plan-format Guardrail 3). A full-suite / build invocation
     times out and blocks the gate. Those belong to the CI `tests` job, cited in
     prose — never a Verify row.

Usage:
    python3 scripts/check_verify_rows.py <SUMMARY.md>...    # check the given files
    python3 scripts/check_verify_rows.py                    # read paths from stdin

Exit 0 = clean, 1 = at least one violation, 2 = bad invocation.
Scope is intentionally per-file (callers pass only the CHANGED SUMMARYs) — this
lints new/edited rows, it does not retroactively police already-shipped specs.
"""

from __future__ import annotations

import re
import sys

_SENTINEL = "\x00"
# Full-suite / build invocations that exceed the strict gate's 60s per-command cap.
# run-tests.sh is flagged only when EXECUTED (after bash/sh/source/./ or at a
# command-segment start) — not when it is merely a grep argument or a path string.
_RUN_TESTS = re.compile(
    r"(?:^|[;&|(]\s*|\b(?:bash|sh|source)\s+|\.\s+|\./)\S*run-tests\.sh"
)
_OTHER_SLOW = re.compile(r"\bmake\s+\S*test|\btox\b|full[ -]suite", re.I)


def _is_too_slow(cmd: str) -> bool:
    return bool(_RUN_TESTS.search(cmd) or _OTHER_SLOW.search(cmd))


def _split_escaped(row: str) -> list[str]:
    """Split a markdown row on unescaped `|`, honoring `\\|` (as verify_summary does)."""
    row = row.replace(r"\|", _SENTINEL).strip().strip("|")
    return [c.strip().replace(_SENTINEL, "|") for c in row.split("|")]


def check_summary_text(text: str) -> list[str]:
    """Return a list of violation messages for the `### Verify` table (empty = clean)."""
    m = re.search(r"^###\s+Verify\s*$", text, re.MULTILINE)
    if not m:
        return []
    section = text[m.end() :]
    violations: list[str] = []
    header_cols = None
    for line in section.splitlines():
        s = line.strip()
        if s.startswith("#"):
            break
        if not s.startswith("|"):
            continue
        cells = _split_escaped(s)
        # separator row
        if all(re.fullmatch(r"-+", c) for c in cells if c):
            continue
        # header row
        if (
            cells
            and cells[0].lower() == "check"
            and "command" in [c.lower() for c in cells]
        ):
            header_cols = len(cells)
            continue
        if header_cols is None:
            continue
        raw_cmd = cells[1] if len(cells) > 1 else ""
        cmd = raw_cmd.strip("`").strip()
        label = cells[0] or "<row>"
        # Rule 1a — an unescaped pipe split the row into the wrong column count.
        if len(cells) != header_cols:
            violations.append(
                f"[{label}] Verify row has {len(cells)} cells (expected {header_cols}) "
                f"— an unescaped `|` in the command splits the cell; rewrite pipe-free"
            )
            continue
        # Rule 1b — an escaped pipe survived: the command still uses a pipe.
        if "|" in cmd:
            violations.append(
                f"[{label}] Verify command contains a pipe `|` — rewrite pipe-free "
                f"(grep -e a -e b / capture $? / redirect instead of `| wc`): {cmd}"
            )
        # Rule 2 — full-suite / build as a Verify row (exceeds the 60s strict-gate cap).
        if _is_too_slow(cmd):
            violations.append(
                f"[{label}] Verify command runs a full suite/build (>60s strict-gate cap) "
                f"— cite it in prose (CI `tests` job), don't make it a Verify row: {cmd}"
            )
    return violations


def main(argv: list[str]) -> int:
    paths = argv[1:] if len(argv) > 1 else [p.strip() for p in sys.stdin if p.strip()]
    if not paths:
        return 0  # nothing changed → nothing to lint
    failed = False
    for path in paths:
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue  # a deleted SUMMARY in the diff — skip
        for v in check_summary_text(text):
            print(f"{path}: {v}")
            failed = True
    if not failed:
        print(
            "  ✓ verify-row lint: all checked SUMMARY Verify rows are pipe-free and <60s"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
