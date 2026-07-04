#!/usr/bin/env python3
"""Check that a spec's SUMMARY.md carries the evidence its declared Lane requires.

This is the single source of truth for the lane -> evidence mapping that
`rules/auto-correct-scope.md` (Lane-aware autonomy table) and
`skills/feature-intake/SKILL.md` (Step 7) describe in prose. Encoding it once, as a
testable check, keeps the three prose copies from drifting (IDEA-10).

Mapping (ceremony scales with risk):

    tiny       -> header only: Lane / Confidence / Reason present and non-placeholder
    normal     -> the above + a non-placeholder `### Verify` row (>=1 real command)
    high-risk  -> the above + a non-empty `### Rollback` entry

`### Verify` rows whose command is a template placeholder (`<command>`, em-dash, empty,
or bare backticks) do not count — evidence over assertion.

Usage:
    python scripts/check_lane_evidence.py <slug|path-to-SUMMARY.md> [more ...]

Exit code 0 = all pass; 1 = a SUMMARY is missing its lane-required evidence;
2 = bad invocation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_LANES = ("tiny", "normal", "high-risk")
# Kept identical to scripts/verify_summary.py's set (em-dash, en-dash, ASCII hyphen).
_PLACEHOLDER_COMMANDS = {"<command>", "—", "–", "-", ""}


def _is_placeholder(value: str) -> bool:
    """A header value is unfilled if it is empty, fully angle-wrapped (`<...>`), or
    still the literal `a | b | c` option-list template.

    Deliberately narrow: real prose may contain a `|` inside backticks (e.g. a regex
    like ``(^|/)hooks/``) or angle brackets mid-sentence — those are NOT placeholders.
    Only the whole-value template shapes are flagged."""
    v = value.strip()
    if not v:
        return True
    if v.startswith("<") and v.endswith(">"):  # e.g. "<one sentence ...>"
        return True
    # template option list: short word-ish tokens around ` | ` separators only,
    # e.g. "tiny | normal | high-risk" / "high | medium | low".
    if " | " in v and re.fullmatch(r"[\w/ +-]+(?: \| [\w/ +-]+)+", v):
        return True
    return False


def _header_value(text: str, field: str) -> str | None:
    """Return the value of a `Field:` header line, or None if the line is absent.

    Tolerates a markdown-bold variant (`**Field:** value`) — some older SUMMARYs bold
    the header — by stripping leading/trailing `*` from the match and value."""
    m = re.search(
        rf"^\*{{0,2}}\s*{field}\s*:\s*(.*)$", text, re.MULTILINE | re.IGNORECASE
    )
    if not m:
        return None
    return m.group(1).strip().strip("*").strip()


def _resolve_lane(text: str) -> str | None:
    raw = _header_value(text, "Lane")
    if raw is None:
        return None
    raw = raw.strip().lower()
    # The unfilled template option list (`tiny | normal | high-risk`) is not a lane.
    if "|" in raw:
        return None
    # The lane must LEAD the value (decoration after it is fine — e.g.
    # `high-risk (hard gate: hooks/*)`), but `not-normal` / `normal-ish` must NOT
    # resolve (the old search-anywhere substring bug, DR-Low).
    m = re.match(r"(tiny|normal|high-risk)(?![\w-])", raw)
    return m.group(1) if m else None


def _section(text: str, heading: str) -> str | None:
    """Return the body of a `### <heading>` section up to the next heading, or None."""
    m = re.search(rf"^#{{1,3}}\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not m:
        return None
    rest = text[m.end() :]
    nxt = re.search(r"^#{1,3}\s+\S", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def _has_real_verify_row(section: str) -> bool:
    """True if the Verify table has >=1 row whose command cell is not a placeholder."""
    for line in section.splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() == "check" and cells[1].lower() == "command":
            continue  # header row
        if all(re.fullmatch(r"-+", c.replace(" ", "")) for c in cells if c):
            continue  # separator row
        command = cells[1].strip("`").strip()
        if (
            command
            and command not in _PLACEHOLDER_COMMANDS
            and not command.startswith("<")
        ):
            return True
    return False


# The untouched SUMMARY-template rollback line — an unedited template is NOT a real
# rollback plan (DR: the high-risk lane's only extra requirement was satisfiable by
# never editing the template).
_TEMPLATE_ROLLBACK_RE = re.compile(r"^`?git revert <sha>`?$")


def _has_real_rollback(section: str) -> bool:
    """True if the Rollback section has a non-empty, non-comment content line that
    is not just the unedited template placeholder."""
    in_comment = False
    for line in section.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("<!--"):
            in_comment = "-->" not in s
            continue
        if in_comment:
            in_comment = "-->" not in s
            continue
        # a real bullet / line of content — unless it's the literal template line
        stripped = s.lstrip("-* ").strip()
        if stripped and not _TEMPLATE_ROLLBACK_RE.match(stripped):
            return True
    return False


def check_summary(text: str) -> list[str]:
    """Return a list of missing-evidence messages (empty == satisfies its lane)."""
    errors: list[str] = []

    lane = _resolve_lane(text)
    if lane is None:
        return ["header: cannot resolve `Lane:` (tiny | normal | high-risk)"]

    # Header fields required for every lane.
    for field in ("Lane", "Confidence", "Reason"):
        val = _header_value(text, field)
        if val is None:
            errors.append(f"header: missing `{field}:` line")
        elif _is_placeholder(val):
            errors.append(f"header: `{field}:` is unfilled (still a placeholder)")

    # normal + high-risk require real verification evidence.
    if lane in ("normal", "high-risk"):
        verify = _section(text, "Verify")
        if verify is None:
            errors.append(f"lane `{lane}`: missing `### Verify` section")
        elif not _has_real_verify_row(verify):
            errors.append(
                f"lane `{lane}`: `### Verify` has no real command row "
                "(all rows are placeholders)"
            )

    # high-risk additionally requires a rollback path.
    if lane == "high-risk":
        rollback = _section(text, "Rollback")
        if rollback is None:
            errors.append("lane `high-risk`: missing `### Rollback` section")
        elif not _has_real_rollback(rollback):
            errors.append(
                "lane `high-risk`: `### Rollback` is empty or only the unedited "
                "template (`git revert <sha>`) — write the real undo steps"
            )

    return errors


def _resolve_path(arg: str, specs_root: Path) -> Path:
    """Accept a slug (-> specs/<slug>/SUMMARY.md) or a direct path."""
    p = Path(arg)
    if p.is_file():
        return p
    return specs_root / arg / "SUMMARY.md"


def check_file(path: Path) -> list[str]:
    if not path.is_file():
        return [f"{path}: not a file"]
    return check_summary(path.read_text(encoding="utf-8"))


def main(argv: list[str], specs_root: Path | None = None) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    if specs_root is None:
        specs_root = _REPO_ROOT / "specs"

    failed = False
    for arg in argv:
        path = _resolve_path(arg, specs_root)
        errors = check_file(path)
        if errors:
            failed = True
            print(f"✗ {path} — {len(errors)} missing:")
            for e in errors:
                print(f"    - {e}")
        else:
            print(f"✓ {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
