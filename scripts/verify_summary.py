#!/usr/bin/env python3
"""Re-run the ### Verify table in a spec's SUMMARY.md and write real exit codes.

Turns proof from self-reported assertion into machine-verified fact.

Usage:
    python3 scripts/verify_summary.py <slug> [--check] [--timeout <seconds>]

    <slug>        Spec slug — reads specs/<slug>/SUMMARY.md
    --check       Compare only; do NOT overwrite the file (for hooks/CI)
    --timeout N   Per-command timeout in seconds (default: 60)

Exit codes:
    0  All non-placeholder commands ran, matched claimed exits, and passed.
    1  Any command failed, timed out, or claimed exit != actual exit.
    2  Bad invocation.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Matches a markdown table row: | cell | cell | ... |
_ROW_RE = re.compile(r"^\|(.+)\|$")

# Placeholder values in the Command column that mean "skip this row"
_PLACEHOLDER_COMMANDS = {"—", "—", "<command>", ""}


def parse_verify_table(text: str) -> list[dict]:
    """Parse the ### Verify table rows from SUMMARY.md text.

    Returns a list of dicts with keys: check, command, claimed_exit, notes.
    Placeholder rows (em-dash, <command>, or empty command) are excluded.
    """
    # Find the ### Verify section
    verify_match = re.search(r"^###\s+Verify\s*$", text, re.MULTILINE)
    if not verify_match:
        return []

    section = text[verify_match.end() :]

    # Collect table rows until we hit the next section heading or end
    rows: list[dict] = []
    in_table = False
    for line in section.splitlines():
        stripped = line.strip()
        # Stop at the next markdown heading
        if stripped.startswith("#"):
            break

        m = _ROW_RE.match(stripped)
        if not m:
            continue

        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) < 3:
            continue

        # Skip separator rows (e.g. | --- | --- | ... |)
        if all(re.match(r"^-+$", c.replace(" ", "")) for c in cells if c.strip()):
            continue

        # Skip header row (Check | Command | Exit | Notes)
        if cells[0].lower() == "check" and cells[1].lower() == "command":
            in_table = True
            continue

        if not in_table:
            in_table = True

        check = cells[0]
        raw_command = cells[1]
        claimed_exit = cells[2] if len(cells) > 2 else ""
        notes = cells[3] if len(cells) > 3 else ""

        # Strip surrounding backticks from command
        command = raw_command.strip("`").strip()

        # Skip placeholders
        if command in _PLACEHOLDER_COMMANDS or command.startswith("<"):
            continue

        rows.append(
            {
                "check": check,
                "command": command,
                "claimed_exit": claimed_exit.strip(),
                "notes": notes.strip(),
            }
        )

    return rows


def run_checks(
    rows: list[dict],
    repo_root: Path,
    timeout: int = 60,
) -> list[dict]:
    """Run each command and return results with actual_exit and timed_out."""
    results = []
    for row in rows:
        timed_out = False
        try:
            proc = subprocess.run(
                row["command"],
                shell=True,
                cwd=repo_root,
                timeout=timeout,
                capture_output=True,
            )
            actual_exit = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            actual_exit = 124  # standard timeout exit code

        results.append(
            {
                **row,
                "actual_exit": actual_exit,
                "timed_out": timed_out,
            }
        )
    return results


def _rewrite_table(text: str, results: list[dict]) -> str:
    """Overwrite the Exit column cells with actual exit codes and add/refresh
    the Verified timestamp line immediately below the ### Verify table."""
    verify_match = re.search(r"^###\s+Verify\s*$", text, re.MULTILINE)
    if not verify_match:
        return text

    section_start = verify_match.end()
    section_text = text[section_start:]

    # Build a mapping from check name -> actual exit
    exit_map = {r["check"]: r["actual_exit"] for r in results}

    new_lines: list[str] = []
    in_table = False
    table_ended = False
    verified_line_written = False
    result_lines = section_text.splitlines(keepends=True)

    i = 0
    while i < len(result_lines):
        line = result_lines[i]
        stripped = line.strip()

        # Stop processing table once we hit the next heading
        if stripped.startswith("#") and in_table:
            table_ended = True
            if not verified_line_written:
                new_lines.append(
                    f"Verified: {datetime.now().isoformat(timespec='seconds')}\n"
                )
                verified_line_written = True
            new_lines.append(line)
            i += 1
            continue

        m = _ROW_RE.match(stripped)
        if m:
            cells = [c.strip() for c in m.group(1).split("|")]
            # Detect header row
            if cells[0].lower() == "check" and cells[1].lower() == "command":
                in_table = True
                new_lines.append(line)
                i += 1
                continue

            # Detect separator row
            if all(re.match(r"^-+$", c.replace(" ", "")) for c in cells if c.strip()):
                new_lines.append(line)
                i += 1
                continue

            if in_table and len(cells) >= 3:
                check_name = cells[0]
                if check_name in exit_map:
                    cells[2] = str(exit_map[check_name])
                    # Reconstruct row preserving leading/trailing pipe
                    new_row = "| " + " | ".join(cells) + " |"
                    # Preserve line ending
                    ending = "\n" if line.endswith("\n") else ""
                    new_lines.append(new_row + ending)
                    i += 1
                    continue
        else:
            # Non-table line after table started — table has ended
            if in_table and not table_ended:
                # Check if this is the existing Verified line
                if stripped.startswith("Verified:"):
                    # Replace it
                    new_lines.append(
                        f"Verified: {datetime.now().isoformat(timespec='seconds')}\n"
                    )
                    verified_line_written = True
                    i += 1
                    continue
                elif stripped == "" and not verified_line_written:
                    # First blank line after table: insert Verified here
                    new_lines.append(
                        f"Verified: {datetime.now().isoformat(timespec='seconds')}\n"
                    )
                    verified_line_written = True
                    new_lines.append(line)
                    i += 1
                    continue

        new_lines.append(line)
        i += 1

    # If we never wrote the Verified line (table was at end of file)
    if in_table and not verified_line_written:
        new_lines.append(
            f"\nVerified: {datetime.now().isoformat(timespec='seconds')}\n"
        )

    return text[:section_start] + "".join(new_lines)


def main(argv: list[str], specs_root: Path | None = None) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    import argparse

    parser = argparse.ArgumentParser(prog="verify_summary.py", add_help=False)
    parser.add_argument("slug", nargs="?", default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("-h", "--help", action="store_true")

    args = parser.parse_args(argv)

    if args.help or args.slug is None:
        print(__doc__, file=sys.stderr)
        return 2

    if specs_root is None:
        specs_root = _REPO_ROOT / "specs"

    summary_path = specs_root / args.slug / "SUMMARY.md"
    if not summary_path.is_file():
        print(f"error: {summary_path} not found", file=sys.stderr)
        return 2

    text = summary_path.read_text(encoding="utf-8")
    rows = parse_verify_table(text)

    if not rows:
        print(
            "warning: no checks ran (all commands are placeholders or table is empty)"
        )
        if not args.check:
            # Still add Verified line even when no checks ran? No — don't
            # claim machine-verified if nothing ran. Just return 0 with warning.
            pass
        return 0

    repo_root = _REPO_ROOT
    results = run_checks(rows, repo_root=repo_root, timeout=args.timeout)

    failed = False
    for r in results:
        if r["timed_out"]:
            print(
                f"TIMEOUT  [{r['check']}]  command: {r['command']}  "
                f"(limit: {args.timeout}s)"
            )
            failed = True
            continue

        try:
            claimed = int(r["claimed_exit"])
        except (ValueError, TypeError):
            claimed = None

        actual = r["actual_exit"]
        is_mismatch = claimed is not None and claimed != actual

        if actual != 0 or is_mismatch:
            if is_mismatch:
                print(
                    f"MISMATCH [{r['check']}]  claimed={claimed}  actual={actual}  "
                    f"command: {r['command']}"
                )
            else:
                print(
                    f"FAIL     [{r['check']}]  claimed={claimed}  actual={actual}  "
                    f"command: {r['command']}"
                )
            failed = True
        else:
            print(f"PASS     [{r['check']}]  exit={actual}")

    if not args.check:
        new_text = _rewrite_table(text, results)
        summary_path.write_text(new_text, encoding="utf-8")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
