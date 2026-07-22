#!/usr/bin/env python3
"""Validate lane evidence or re-run a spec's SUMMARY.md Verify table.

Lane mode checks that the SUMMARY carries the evidence required by its declared
risk lane. Verify mode turns self-reported command results into machine-verified
fact.

Usage:
    python3 scripts/verify_summary.py <slug> [--check] [--timeout <seconds>]
    python3 scripts/verify_summary.py --lane <slug|path-to-SUMMARY.md> [more ...]

    <slug>        Spec slug -- reads specs/<slug>/SUMMARY.md
    --check       Compare only; do NOT overwrite the file (for hooks/CI)
    --lane        Check lane-required evidence; never execute Verify commands
    --timeout N   Per-command timeout in seconds (default: 60)

Exit codes:
    0  Verification passed, or every target satisfies its declared lane.
    1  Verification failed, or any target lacks lane-required evidence.
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
_PLACEHOLDER_COMMANDS = {"—", "–", "-", "<command>", ""}

# The untouched SUMMARY-template rollback line is not a real rollback plan.
_TEMPLATE_ROLLBACK_RE = re.compile(r"^`?git revert <sha>`?$")

# A whole command that proves nothing: exit-0 of a no-op is not evidence.
# `true`, `:`, `exit 0`, or a bare `echo …` (echo piped/chained into a real tool is
# NOT trivial — `echo x | grep x` still asserts something).
# BEST-EFFORT, not a security boundary: only the bare word forms are caught —
# wrapped no-ops (`true;`, `(true)`, `/usr/bin/true`, `command true`) still execute
# and pass. The gate's real defense is human PR review of the Verify table; this
# denylist removes the laziest forgery class (DR-6).
_TRIVIAL_RE = re.compile(r"^\s*(?:true|:|exit\s+0|echo\b[^|&;`$()]*)\s*$")

# A PLAN.md §3 Success-Criteria id: `SC-1`, `SC-2`, ...
_SC_ID_RE = re.compile(r"^SC-\d+$")

# An `Expected` cell must lead with the machine-read token `exit <n>` (n may be
# non-zero — negative proof is legal); free text may follow.
_SC_EXPECTED_RE = re.compile(r"^exit\s+(\d+)\b")


def parse_sc_table(plan_text: str) -> dict[str, str]:
    """Map each `SC-<n>` id to its expected-exit token from a PLAN.md §3 table.

    Only markdown table rows whose first cell matches `^SC-\\d+$` are read; fenced
    blocks (illustrations) are skipped via a simple in-fence toggle. A value is the
    numeric exit string (e.g. "0", "1"). Malformed rows map the id to an
    `ERROR: ...` string instead: a duplicate id, or an `Expected` cell that does
    not lead with `exit <n>`.
    """
    result: dict[str, str] = {}
    in_fence = False
    for line in plan_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        m = _ROW_RE.match(stripped)
        if not m:
            continue

        cells = [c.strip() for c in m.group(1).split("|")]
        sc_id = cells[0]
        if not _SC_ID_RE.match(sc_id):
            continue

        if sc_id in result:
            result[sc_id] = f"ERROR: duplicate id {sc_id}"
            continue

        expected = cells[3] if len(cells) > 3 else ""
        em = _SC_EXPECTED_RE.match(expected)
        if not em:
            result[sc_id] = (
                f"ERROR: {sc_id} `Expected` must lead with `exit <n>` (got {expected!r})"
            )
            continue

        result[sc_id] = em.group(1)
    return result


def _parse_verify_rows(section: str) -> list[dict]:
    """Parse Verify table rows from an already-resolved section body."""
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
        criterion = cells[4] if len(cells) > 4 else ""

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
                "criterion": criterion.strip(),
            }
        )

    return rows


def parse_verify_table(text: str) -> list[dict]:
    """Parse the canonical ### Verify table rows from SUMMARY.md text.

    Returns a list of dicts with keys: check, command, claimed_exit, notes.
    Placeholder rows (em-dash, <command>, or empty command) are excluded.
    """
    verify_match = re.search(r"^###\s+Verify\s*$", text, re.MULTILINE)
    if not verify_match:
        return []
    return _parse_verify_rows(text[verify_match.end() :])


def _is_placeholder(value: str) -> bool:
    """Return whether a SUMMARY header value still has a template shape."""
    value = value.strip()
    if not value:
        return True
    if value.startswith("<") and value.endswith(">"):
        return True
    # Keep this narrow: real prose may contain a pipe in backticks or angle
    # brackets mid-sentence. Only a whole option-list value is a placeholder.
    return bool(" | " in value and re.fullmatch(r"[\w/ +-]+(?: \| [\w/ +-]+)+", value))


def _header_value(text: str, field: str) -> str | None:
    """Read a plain or markdown-bold `Field:` header value."""
    match = re.search(
        rf"^\*{{0,2}}\s*{field}\s*:\s*(.*)$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip().strip("*").strip()


def _resolve_lane(text: str) -> str | None:
    raw = _header_value(text, "Lane")
    if raw is None:
        return None
    raw = raw.strip().lower()
    if "|" in raw:
        return None
    match = re.match(r"(tiny|normal|high-risk)(?![\w-])", raw)
    return match.group(1) if match else None


def _section(text: str, heading: str) -> str | None:
    """Return a markdown section body through the next level 1-3 heading."""
    match = re.search(rf"^#{{1,3}}\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        return None
    rest = text[match.end() :]
    next_heading = re.search(r"^#{1,3}\s+\S", rest, re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def _has_real_rollback(section: str) -> bool:
    """Return whether Rollback contains content beyond comments/template text."""
    in_comment = False
    for line in section.splitlines():
        value = line.strip()
        if not value:
            continue
        if value.startswith("<!--"):
            in_comment = "-->" not in value
            continue
        if in_comment:
            in_comment = "-->" not in value
            continue
        stripped = value.lstrip("-* ").strip()
        if stripped and not _TEMPLATE_ROLLBACK_RE.match(stripped):
            return True
    return False


def _sc_map_for_summary(summary_path: Path | None) -> dict[str, str]:
    """Parse the SC table of the sibling PLAN.md, or {} when none applies."""
    if summary_path is None:
        return {}
    plan_path = Path(summary_path).parent / "PLAN.md"
    if not plan_path.is_file():
        return {}
    return parse_sc_table(plan_path.read_text(encoding="utf-8"))


def _check_sc_coverage(text: str, summary_path: Path | None) -> list[str]:
    """Return SC-coverage errors when a sibling PLAN.md declares an SC table.

    Fail-open: no PLAN.md or no SC table → no checks. Otherwise every SC id must be
    named by ≥1 Verify row whose claimed exit matches the SC's expected exit; a
    Criterion naming an unknown SC id is an error (typo guard).
    """
    sc_map = _sc_map_for_summary(summary_path)
    if not sc_map:
        return []

    errors: list[str] = []
    for sc_id, value in sc_map.items():
        if value.startswith("ERROR:"):
            errors.append(f"SC table: {value[len('ERROR:') :].strip()}")

    valid = {k: v for k, v in sc_map.items() if not v.startswith("ERROR:")}

    verify = _section(text, "Verify")
    rows = _parse_verify_rows(verify) if verify else []

    covered: dict[str, set[str]] = {}
    for row in rows:
        criterion = row.get("criterion", "")
        if not criterion:
            continue
        if criterion not in sc_map:
            errors.append(
                f"Verify row `{row['check']}` Criterion `{criterion}` names an "
                "unknown SC id (not in PLAN.md §3)"
            )
            continue
        covered.setdefault(criterion, set()).add(row["claimed_exit"])

    for sc_id, expected in valid.items():
        if expected not in covered.get(sc_id, set()):
            errors.append(
                f"SC coverage: `{sc_id}` (expected exit {expected}) is not named by "
                "any Verify row with a matching claimed exit"
            )

    return errors


def check_lane_evidence(text: str, summary_path: Path | None = None) -> list[str]:
    """Return missing-evidence messages for the SUMMARY's declared lane."""
    errors: list[str] = []
    lane = _resolve_lane(text)
    if lane is None:
        return ["header: cannot resolve `Lane:` (tiny | normal | high-risk)"]

    for field in ("Lane", "Confidence", "Reason"):
        value = _header_value(text, field)
        if value is None:
            errors.append(f"header: missing `{field}:` line")
        elif _is_placeholder(value):
            errors.append(f"header: `{field}:` is unfilled (still a placeholder)")

    if lane in ("normal", "high-risk"):
        verify = _section(text, "Verify")
        if verify is None:
            errors.append(f"lane `{lane}`: missing `### Verify` section")
        elif not _parse_verify_rows(verify):
            errors.append(
                f"lane `{lane}`: `### Verify` has no real command row "
                "(all rows are placeholders)"
            )

    if lane == "high-risk":
        rollback = _section(text, "Rollback")
        if rollback is None:
            errors.append("lane `high-risk`: missing `### Rollback` section")
        elif not _has_real_rollback(rollback):
            errors.append(
                "lane `high-risk`: `### Rollback` is empty or only the unedited "
                "template (`git revert <sha>`) -- write the real undo steps"
            )

    errors += _check_sc_coverage(text, summary_path)

    return errors


def _resolve_summary_path(target: str, specs_root: Path) -> Path:
    """Resolve a lane target as a direct file path first, then as a slug."""
    path = Path(target)
    if path.is_file():
        return path
    return specs_root / target / "SUMMARY.md"


def _check_lane_targets(targets: list[str], specs_root: Path) -> int:
    failed = False
    for target in targets:
        path = _resolve_summary_path(target, specs_root)
        if path.is_file():
            errors = check_lane_evidence(
                path.read_text(encoding="utf-8"), summary_path=path
            )
        else:
            errors = [f"{path}: not a file"]
        if errors:
            failed = True
            print(f"✗ {path} -- {len(errors)} missing:")
            for error in errors:
                print(f"    - {error}")
        else:
            print(f"✓ {path}")
    return 1 if failed else 0


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
    parser.add_argument("targets", nargs="*")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--lane", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("-h", "--help", action="store_true")

    args = parser.parse_args(argv)

    if args.help:
        print(__doc__, file=sys.stderr)
        return 2

    if specs_root is None:
        specs_root = _REPO_ROOT / "specs"

    if args.lane:
        if args.check or not args.targets:
            print(__doc__, file=sys.stderr)
            return 2
        return _check_lane_targets(args.targets, specs_root)

    if len(args.targets) != 1:
        print(__doc__, file=sys.stderr)
        return 2

    summary_path = specs_root / args.targets[0] / "SUMMARY.md"
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

    # SC expected exits from the sibling PLAN.md (empty when none) — a
    # Criterion-mapped row is also validated against its SC's expected exit.
    sc_map = _sc_map_for_summary(summary_path)

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

        # SC gate: a Criterion-mapped row must actually exit its SC's expected
        # code. Distinct from claimed-vs-actual — it catches a row that matches
        # its own claim but points at the wrong SC.
        criterion = r.get("criterion", "")
        sc_expected = sc_map.get(criterion)
        if sc_expected is not None and not sc_expected.startswith("ERROR:"):
            if actual != int(sc_expected):
                print(
                    f"SC-FAIL  [{r['check']}]  criterion={criterion}  "
                    f"sc_expected={sc_expected}  actual={actual}  "
                    f"command: {r['command']}"
                )
                failed = True
                continue

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
