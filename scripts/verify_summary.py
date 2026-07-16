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

# Placeholder values in the Command column that mean "skip this row".
# Kept identical to scripts/check_lane_evidence.py's set (em-dash, en-dash, ASCII
# hyphen — the old duplicate em-dash here was a typo'd hyphen and the sets diverged).
_PLACEHOLDER_COMMANDS = {"—", "–", "-", "<command>", ""}

# A whole command that proves nothing: exit-0 of a no-op is not evidence.
# `true`, `:`, `exit 0`, or a bare `echo …` (echo piped/chained into a real tool is
# NOT trivial — `echo x | grep x` still asserts something).
# BEST-EFFORT, not a security boundary: only the bare word forms are caught —
# wrapped no-ops (`true;`, `(true)`, `/usr/bin/true`, `command true`) still execute
# and pass. The gate's real defense is human PR review of the Verify table; this
# denylist removes the laziest forgery class (DR-6).
_TRIVIAL_RE = re.compile(r"^\s*(?:true|:|exit\s+0|echo\b[^|&;`$()]*)\s*$")


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
        # Trivial commands are rejected without execution — running them proves nothing.
        if _TRIVIAL_RE.match(row["command"]):
            results.append(
                {**row, "actual_exit": None, "timed_out": False, "trivial": True}
            )
            continue
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


def _rewrite_table(text: str, results: list[dict], stamp_verified: bool = True) -> str:
    """Overwrite the Exit column cells with actual exit codes. When stamp_verified,
    add/refresh the `Verified:` timestamp line below the table; otherwise DROP any
    existing stamp — a failing table must never read as machine-verified.

    Results are consumed in ROW ORDER (the same order parse_verify_table emitted
    them), not keyed by check name — duplicate check names cannot collide."""
    verify_match = re.search(r"^###\s+Verify\s*$", text, re.MULTILINE)
    if not verify_match:
        return text

    section_start = verify_match.end()
    section_text = text[section_start:]

    # Consume results in the order parse_verify_table produced them.
    queue = list(results)

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
            if stamp_verified and not verified_line_written:
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
                # EXACTLY the same skip criteria as parse_verify_table (incl. the
                # startswith("<") arm), or the queue shifts and exits land on the
                # wrong rows.
                command = cells[1].strip("`").strip()
                is_skipped = command in _PLACEHOLDER_COMMANDS or command.startswith("<")
                if not is_skipped and queue:
                    result = queue.pop(0)
                    # Trivial rows were never executed (actual_exit None) — leave the
                    # cell as claimed; the missing Verified stamp marks the failure.
                    if result["actual_exit"] is not None:
                        cells[2] = str(result["actual_exit"])
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
                # Existing Verified line: refresh it when stamping, DROP it when not
                # (a stale stamp on a now-failing table is a false claim).
                if stripped.startswith("Verified:"):
                    if stamp_verified:
                        new_lines.append(
                            f"Verified: {datetime.now().isoformat(timespec='seconds')}\n"
                        )
                    verified_line_written = True
                    i += 1
                    continue
                elif stripped == "" and stamp_verified and not verified_line_written:
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
    if stamp_verified and in_table and not verified_line_written:
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
        if r.get("trivial"):
            print(
                f"TRIVIAL  [{r['check']}]  command is not evidence "
                f"(no-op always exits 0): {r['command']}"
            )
            failed = True
            continue

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

        # A row PASSES when the claim matches reality — even a non-zero claim
        # (negative proof: "this command must fail" is a legitimate, pinnable check).
        # It FAILS on claim-vs-reality mismatch, or on an unclaimed non-zero exit.
        if claimed is not None and claimed != actual:
            print(
                f"MISMATCH [{r['check']}]  claimed={claimed}  actual={actual}  "
                f"command: {r['command']}"
            )
            failed = True
        elif claimed is None and actual != 0:
            print(
                f"FAIL     [{r['check']}]  claimed={claimed}  actual={actual}  "
                f"command: {r['command']}"
            )
            failed = True
        else:
            print(f"PASS     [{r['check']}]  exit={actual}")

    if not args.check:
        # Always record the ACTUAL exits, but only stamp `Verified:` when everything
        # passed — a failing table must never read as machine-verified (DR-19b).
        new_text = _rewrite_table(text, results, stamp_verified=not failed)
        summary_path.write_text(new_text, encoding="utf-8")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
