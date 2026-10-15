#!/usr/bin/env python3
"""Validate lane evidence or re-run a spec's SUMMARY.md Verify table.

Lane mode checks that the SUMMARY carries the evidence required by its declared
risk lane. Verify mode turns self-reported command results into machine-verified
fact.

Usage:
    python3 scripts/verify_summary.py <slug> [--check] [--timeout <seconds>]
    python3 scripts/verify_summary.py --lane <slug|path-to-SUMMARY.md> [more ...]
    python3 scripts/verify_summary.py --sc-history <slug> --base <ref>

    <slug>        Spec slug -- reads specs/<slug>/SUMMARY.md
    --check       Compare only; do NOT overwrite the file (for hooks/CI)
    --lane        Check lane-required evidence; never execute Verify commands
    --timeout N   Per-command timeout in seconds (default: 60)
    --sc-history  Warn when a Success Criterion recorded as failing on this branch
                  (merge-base(<ref>, HEAD)..HEAD) later had its Check/Expected
                  changed or its row removed, unless HEAD `### Deviations` names it.
                  Reads git objects from the repository containing the cwd.

Exit codes:
    0  Verification passed, or every target satisfies its declared lane.
       (--sc-history: always 0 unless REQUIRE_SC_STABLE=1 and a finding exists.)
    1  Verification failed, or any target lacks lane-required evidence.
       (--sc-history: a finding under REQUIRE_SC_STABLE=1.)
    2  Bad invocation.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_SELF_ROOT = Path(__file__).resolve().parents[1]
# A deployed copy lives at <repo>/.claude/scripts/; the sources it reads (specs/) live at the
# repo root, one level further out. In the harness repo _SELF_ROOT is already the repo root.
_REPO_ROOT = _SELF_ROOT.parent if _SELF_ROOT.name == ".claude" else _SELF_ROOT

# Matches a markdown table row: | cell | cell | ... |
_ROW_RE = re.compile(r"^\|(.+)\|$")

# Placeholder values in the Command column that mean "skip this row".
_PLACEHOLDER_COMMANDS = {"—", "–", "-", "<command>", ""}

# The untouched SUMMARY-template rollback line is not a real rollback plan.
_TEMPLATE_ROLLBACK_RE = re.compile(r"^`?git revert <sha>`?$")

# The untouched `### Not auto-verified` template bullet. Same idea as the rollback
# line above: the section being present proves nothing if it still holds the shipped
# placeholder. `- none` is deliberately NOT matched here — it is a legitimate answer
# (every claim covered by a Verify row) and the template says so.
_TEMPLATE_NOT_VERIFIED_RE = re.compile(r"^<claim>\b|^<.*>\s*$")

# Rollout: WARN-FIRST. 52 of the 53 pre-existing high-risk specs predate the
# `### Not auto-verified` section, so requiring it outright would tax every future
# edit to a legacy spec -- including a typo fix. Default is a printed warning with a
# zero exit; set REQUIRE_NOT_AUTO_VERIFIED=1 to make it blocking. Flip the default
# here (not at each call site) once the back catalogue has drained.
# Same opt-in shape as REQUIRE_VERIFY / REQUIRE_APP_GATES / RISK_CORROBORATION_STRICT.
_NOT_AUTO_VERIFIED_ENV = "REQUIRE_NOT_AUTO_VERIFIED"

# Bug-fix runs (`Input-type: bug fix`) need a red/green Verify pair or an exemption.
# Advisory by default; set REQUIRE_RED_TEST=1 to make it blocking (same opt-in shape).
_RED_TEST_ENV = "REQUIRE_RED_TEST"

# A red row: `[python3] <path>/scripts/run_at_commit.py <sha> -- <test command>`.
_RED_COMMAND_RE = re.compile(
    r"^(?:python3\s+)?(?:\S*/)?scripts/run_at_commit\.py\s+"
    r"[0-9a-fA-F]{7,40}\s+--\s+(?P<test>\S.*)$"
)
_RED_EXEMPT_RE = re.compile(r"^\s*[-*]?\s*Red test exempt:(.*)$", re.MULTILINE)

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
_RUNTIME_MODES = {"enforced", "advisory", "unsupported"}
_RUNTIME_EVIDENCE_ID_RE = re.compile(r"^codex-mode-[0-9a-f]{16}$")


def _check_runtime_metadata(text: str, summary_path: Path | None) -> list[str]:
    """Validate optional all-or-nothing sanitized runtime diagnosis metadata.

    Format-only by design (traceability tier). The local record lives in the
    gitignored, agent-writable `.harness-state/` — a record comparison at
    commit time can never be index-safe (see
    docs/solutions/harness/gate-config-must-read-index.md), and the commit
    gate judges a materialized temp copy anyway. The doctor and the session
    banner are the record's read paths; this gate only refuses malformed or
    half-supplied pairs.
    """
    mode = _header_value(text, "Runtime-mode")
    evidence_id = _header_value(text, "Runtime-evidence-id")
    if mode is None and evidence_id is None:
        return []
    if mode is None or evidence_id is None:
        return [
            "runtime metadata: `Runtime-mode` and `Runtime-evidence-id` must be supplied together"
        ]
    if mode not in _RUNTIME_MODES:
        return [f"runtime metadata: invalid Runtime-mode `{mode}`"]
    if not _RUNTIME_EVIDENCE_ID_RE.fullmatch(evidence_id):
        return ["runtime metadata: invalid Runtime-evidence-id"]
    return []


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


def parse_sc_checks(plan_text: str) -> dict[str, tuple[str, str]]:
    """Map each well-formed `SC-<n>` id to (whitespace-collapsed Check cell, exit token).

    Rows that `parse_sc_table` maps to `ERROR: ...` are left out. Fenced blocks are
    skipped the same way.
    """
    exits = parse_sc_table(plan_text)
    result: dict[str, tuple[str, str]] = {}
    in_fence = False
    for line in plan_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        m = None if in_fence else _ROW_RE.match(stripped)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        token = exits.get(cells[0], "")
        if _SC_ID_RE.match(cells[0]) and token and not token.startswith("ERROR:"):
            check = " ".join(cells[2].split()) if len(cells) > 2 else ""
            result[cells[0]] = (check, token)
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


def _all_sections(text: str, heading: str) -> str | None:
    """Join the bodies of EVERY level 1-3 heading starting with the word `heading`.

    Unlike `_section` (first exact match only), this also matches a heading with
    trailing words, such as `### Deviations (task 2)`. None when no heading matches.
    """
    starts = list(
        re.finditer(rf"^#{{1,3}}\s+{re.escape(heading)}\b.*$", text, re.MULTILINE)
    )
    if not starts:
        return None
    bodies = []
    for match in starts:
        rest = text[match.end() :]
        next_heading = re.search(r"^#{1,3}\s+\S", rest, re.MULTILINE)
        bodies.append(rest[: next_heading.start()] if next_heading else rest)
    return "\n".join(bodies)


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


def _has_real_not_auto_verified(section: str) -> bool:
    """Return whether `### Not auto-verified` holds a real entry.

    Evidence tier: TRACEABILITY.

    Verifies: the section exists and carries at least one non-placeholder bullet —
        either an explicit `- none` (every claim is covered by a Verify row) or a
        written-out claim.
    Does not verify: that the listed claims are COMPLETE, that their tier labels
        (traceability / provenance / truth) are correct, or that an unlisted claim
        does not exist. Those are judgment calls, left to human PR review. This gate
        forces the author to answer the question; it cannot check the answer.
    """
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
        if stripped and not _TEMPLATE_NOT_VERIFIED_RE.match(stripped):
            return True
    return False


def _not_auto_verified_is_blocking() -> bool:
    """Return whether a missing `### Not auto-verified` should fail the lane gate."""
    return os.environ.get(_NOT_AUTO_VERIFIED_ENV, "").strip() not in ("", "0", "false")


def _not_auto_verified_issue(text: str) -> str | None:
    """Return the negative-scope complaint for this SUMMARY, or None if satisfied.

    Lane-agnostic: the caller decides which lanes it applies to, and
    `_not_auto_verified_is_blocking()` decides whether it blocks or only warns.
    """
    section = _section(text, "Not auto-verified")
    if section is None:
        return (
            "`### Not auto-verified` section missing -- state the negative scope "
            "(what this change claims that no gate checks), or `- none`"
        )
    if not _has_real_not_auto_verified(section):
        return (
            "`### Not auto-verified` is empty or only the unedited template bullet "
            "-- write the real unverified claims, or `- none`"
        )
    return None


def _red_test_is_blocking() -> bool:
    """Return whether a missing red/green pair should fail the lane gate."""
    return os.environ.get(_RED_TEST_ENV, "").strip() not in ("", "0", "false")


def _red_green_issue(text: str) -> str | None:
    """Return the red/green complaint for a bug-fix SUMMARY, or None if satisfied.

    Verifies: (traceability) when `Input-type` is `bug fix`, `### Verify` holds a
    `red` row (run_at_commit.py <sha> -- <test>, claimed exit 1-123) and a `green`
    row (the same test command, claimed exit 0), or a `Red test exempt: <reason>`
    line with a non-empty reason.
    Does not verify: that the claimed exits are real (`--check` re-runs rows), that
    the test exercises the bug, or that an exemption reason is genuine.
    """
    if (_header_value(text, "Input-type") or "").strip().lower() != "bug fix":
        return None
    verify = _section(text, "Verify") or ""
    rows = _parse_verify_rows(verify)

    red_tests = []
    bad_red = None
    for row in rows:
        if row["check"].strip().lower() != "red":
            continue
        match = _RED_COMMAND_RE.match(row["command"])
        if not match:
            bad_red = (
                "`red` row command is not `[python3] scripts/run_at_commit.py "
                "<7-40 hex sha> -- <test command>`"
            )
        elif not (
            re.fullmatch(r"\d+", row["claimed_exit"])
            and 1 <= int(row["claimed_exit"]) <= 123
        ):
            bad_red = f"`red` row claims exit `{row['claimed_exit']}` (must be 1-123)"
        else:
            red_tests.append(" ".join(match.group("test").split()))

    for row in rows:
        if (
            row["check"].strip().lower() == "green"
            and row["claimed_exit"] == "0"
            and " ".join(row["command"].split()) in red_tests
        ):
            return None

    exempt = [m.group(1).strip() for m in _RED_EXEMPT_RE.finditer(verify)]
    if any(exempt):
        return None

    if exempt:
        missing = "`Red test exempt:` has an empty reason"
    elif red_tests:
        missing = "no `green` row with the red row's test command and claimed exit 0"
    elif bad_red:
        missing = bad_red
    else:
        missing = "no `red` row and no `Red test exempt: <reason>` line"
    return f"bug fix: red/green evidence missing in `### Verify` -- {missing}"


def check_lane_warnings(text: str) -> list[tuple[str, str]]:
    """Return non-blocking lane advisories as (message, enforcing env var) pairs.

    These are printed but never change an exit code. Each one stops being a warning
    (and becomes an error in `check_lane_evidence`) when its own env var is set --
    see `_NOT_AUTO_VERIFIED_ENV` and `_RED_TEST_ENV`.
    """
    warnings: list[tuple[str, str]] = []
    # When blocking, each issue is an error instead; do not report it twice.
    if not _not_auto_verified_is_blocking() and _resolve_lane(text) == "high-risk":
        issue = _not_auto_verified_issue(text)
        if issue:
            warnings.append((f"lane `high-risk`: {issue}", _NOT_AUTO_VERIFIED_ENV))
    if not _red_test_is_blocking():
        issue = _red_green_issue(text)
        if issue:
            warnings.append((issue, _RED_TEST_ENV))
    return warnings


def _sc_map_for_summary(
    summary_path: Path | None, plan_dir: Path | None = None
) -> dict[str, str]:
    """Parse the SC table of the sibling PLAN.md, or {} when none applies.

    `plan_dir` overrides where PLAN.md is looked up. It is required when the SUMMARY
    content is read from a staged/temp copy (e.g. `commit-gate.sh` check_lane_evidence stages the
    SUMMARY into a mktemp file) whose parent is NOT the real spec dir — without it,
    `parent / PLAN.md` never resolves and SC coverage silently fail-opens.
    """
    if plan_dir is not None:
        plan_path = Path(plan_dir) / "PLAN.md"
    elif summary_path is not None:
        plan_path = Path(summary_path).parent / "PLAN.md"
    else:
        return {}
    if not plan_path.is_file():
        return {}
    return parse_sc_table(plan_path.read_text(encoding="utf-8"))


def _check_sc_coverage(
    text: str, summary_path: Path | None, plan_dir: Path | None = None
) -> list[str]:
    """Return SC-coverage errors when a sibling PLAN.md declares an SC table.

    Fail-open: no PLAN.md or no SC table → no checks. Otherwise every SC id must be
    named by ≥1 Verify row whose claimed exit matches the SC's expected exit; a
    Criterion naming an unknown SC id is an error (typo guard).
    """
    sc_map = _sc_map_for_summary(summary_path, plan_dir)
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


def check_lane_evidence(
    text: str, summary_path: Path | None = None, plan_dir: Path | None = None
) -> list[str]:
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
        issue = _not_auto_verified_issue(text)
        if issue and _not_auto_verified_is_blocking():
            errors.append(f"lane `high-risk`: {issue}")

        rollback = _section(text, "Rollback")
        if rollback is None:
            errors.append("lane `high-risk`: missing `### Rollback` section")
        elif not _has_real_rollback(rollback):
            errors.append(
                "lane `high-risk`: `### Rollback` is empty or only the unedited "
                "template (`git revert <sha>`) -- write the real undo steps"
            )

    if _red_test_is_blocking():
        issue = _red_green_issue(text)
        if issue:
            errors.append(issue)

    errors += _check_sc_coverage(text, summary_path, plan_dir)
    errors += _check_runtime_metadata(text, summary_path)

    return errors


def _resolve_summary_path(target: str, specs_root: Path) -> Path:
    """Resolve a lane target as a direct file path first, then as a slug."""
    path = Path(target)
    if path.is_file():
        return path
    return specs_root / target / "SUMMARY.md"


def _check_lane_targets(
    targets: list[str], specs_root: Path, plan_dir: Path | None = None
) -> int:
    failed = False
    for target in targets:
        path = _resolve_summary_path(target, specs_root)
        warnings: list[tuple[str, str]] = []
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            errors = check_lane_evidence(text, summary_path=path, plan_dir=plan_dir)
            warnings = check_lane_warnings(text)
        else:
            errors = [f"{path}: not a file"]
        if errors:
            failed = True
            print(f"✗ {path} -- {len(errors)} missing:")
            for error in errors:
                print(f"    - {error}")
        else:
            print(f"✓ {path}")
        # Advisories print on BOTH paths and never set `failed`. They must survive a
        # passing run: a warning only emitted on failure is a warning nobody reads.
        for warning, env_var in warnings:
            print(f"    ! {warning} (warn-only; set {env_var}=1 to enforce)")
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


_SC_HISTORY_USAGE = "usage: verify_summary.py --sc-history <slug> --base <ref>"
_SC_STABLE_ENV = "REQUIRE_SC_STABLE"


class ScHistoryUsageError(Exception):
    """A --sc-history invocation that cannot be evaluated (exit 2)."""


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL
    ).strip()


def _git_show(root: Path, commit: str, path: str) -> str | None:
    """Return `path` at `commit`, or None when the file does not exist there."""
    try:
        return _git(root, "show", f"{commit}:{path}")
    except subprocess.CalledProcessError:
        return None


def _verify_rows_of(summary: str | None) -> list[dict]:
    """Verify rows of a SUMMARY text; [] when the file or its Verify section is absent."""
    if summary is None:
        return []
    verify = _section(summary, "Verify")
    return _parse_verify_rows(verify) if verify else []


def _verify_row_key(row: dict) -> tuple[str, str, str, str]:
    """Identity of a Verify row for D9: its Criterion plus the cells it asserts."""
    return (row["criterion"], row["check"], row["command"], row["claimed_exit"])


def _verify_row_keys(summary: str | None) -> set[tuple[str, str, str, str]]:
    return {_verify_row_key(row) for row in _verify_rows_of(summary)}


def sc_history(repo_root: Path, slug: str, base: str) -> tuple[list[str], str]:
    """Return (finding lines, summary line) for SC goalpost moves on this branch.

    Evidence tier: PROVENANCE (re-derived from git history, not re-run).

    Verifies: no SC that a commit in merge-base(base, HEAD)..HEAD recorded as failing
        (a Verify row with `Criterion: SC-n` whose integer Exit differs from SC-n's
        expected exit in that commit's PLAN, judged only at a commit where that row
        (Criterion, Check, Command, Exit) is new or changed compared with the
        previous SUMMARY in the walk -- design D9) has had its Check or Expected exit token
        changed, or its row removed, at HEAD without HEAD `### Deviations` naming SC-n.
    Does not verify: that a Deviations entry justifies the change, failures never
        committed, or weakening inside the command's own test content.

    Raises ScHistoryUsageError when `base` does not resolve or has no merge base.
    """
    try:
        _git(repo_root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    except subprocess.CalledProcessError:
        raise ScHistoryUsageError(f"--base {base!r} does not resolve to a commit")
    try:
        mb = _git(repo_root, "merge-base", base, "HEAD")
    except subprocess.CalledProcessError:
        raise ScHistoryUsageError(f"no merge base between {base!r} and HEAD")

    summary_path = f"specs/{slug}/SUMMARY.md"
    plan_path = f"specs/{slug}/PLAN.md"
    commits = _git(
        repo_root, "rev-list", "--reverse", f"{mb}..HEAD", "--", summary_path, plan_path
    ).split()
    if not commits:
        return [], f"sc-history {slug}: no SUMMARY.md or PLAN.md change on this branch"

    head_summary = _git_show(repo_root, "HEAD", summary_path)
    head_plan = _git_show(repo_root, "HEAD", plan_path)
    if head_summary is None and head_plan is None:
        return [], f"sc-history {slug}: skipped -- specs/{slug}/ is gone at HEAD"

    # SC id -> (commit, Check cell, exit token) of its FIRST failure record.
    failures: dict[str, tuple[str, str, str]] = {}
    # The first commit in the walk is compared with the merge base, so a branch that
    # opens with a PLAN-only commit does not judge a SUMMARY inherited from the base.
    previous_keys = _verify_row_keys(_git_show(repo_root, mb, summary_path))
    for commit in commits:
        summary = _git_show(repo_root, commit, summary_path)
        # D9: a Verify row is judged only where THAT row is new or changed compared
        # with the previous SUMMARY in the walk. A PLAN-only commit, or an unrelated
        # SUMMARY edit, leaves a stale row unjudged.
        rows = _verify_rows_of(summary)
        keys = {_verify_row_key(row) for row in rows}
        new_rows = [row for row in rows if _verify_row_key(row) not in previous_keys]
        previous_keys = keys
        if not new_rows:
            continue
        plan = _git_show(repo_root, commit, plan_path)
        if plan is None:
            continue
        sc_checks = parse_sc_checks(plan)
        for row in new_rows:
            sc_id = row["criterion"]
            if sc_id in failures or sc_id not in sc_checks:
                continue
            if not re.fullmatch(r"\d+", row["claimed_exit"]):
                continue
            check, token = sc_checks[sc_id]
            if int(row["claimed_exit"]) != int(token):
                failures[sc_id] = (commit, check, token)

    head_exits = parse_sc_table(head_plan) if head_plan is not None else {}
    head_checks = parse_sc_checks(head_plan) if head_plan is not None else {}
    deviations = _all_sections(head_summary, "Deviations") if head_summary else None

    findings: list[str] = []
    for sc_id, (commit, check, token) in failures.items():
        if sc_id not in head_exits:
            kind = "removed"
        elif head_checks.get(sc_id) != (check, token):
            kind = "changed"
        else:
            continue
        if deviations and re.search(
            rf"(?<![\w-]){re.escape(sc_id)}(?!\w)", deviations
        ):
            continue
        sha = _git(repo_root, "rev-parse", "--short", commit)
        findings.append(
            f"SC-GOALPOST [{sc_id}] {kind} after it failed at {sha}; "
            f"name {sc_id} in ### Deviations to acknowledge"
        )
    return findings, (
        f"sc-history {slug}: no failed SC was changed "
        f"({len(failures)} failure record(s) checked)"
    )


def _run_sc_history(slug: str, base: str) -> int:
    try:
        root = Path(_git(Path.cwd(), "rev-parse", "--show-toplevel"))
        findings, summary = sc_history(root, slug, base)
    except ScHistoryUsageError as exc:
        print(f"error: {exc}\n{_SC_HISTORY_USAGE}", file=sys.stderr)
        return 2
    except (OSError, subprocess.CalledProcessError):
        print(
            f"error: not inside a git repository, or git cannot run\n{_SC_HISTORY_USAGE}",
            file=sys.stderr,
        )
        return 2
    except Exception as exc:  # noqa: BLE001 — exit 1 must only ever mean a finding
        print(
            f"sc-history: unexpected error: {type(exc).__name__}: {exc}", file=sys.stderr
        )
        return 2
    for line in findings:
        print(line)
    if not findings:
        print(summary)
    if findings and os.environ.get(_SC_STABLE_ENV, "").strip() == "1":
        return 1
    return 0


def main(argv: list[str], specs_root: Path | None = None) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    import argparse

    parser = argparse.ArgumentParser(prog="verify_summary.py", add_help=False)
    parser.add_argument("targets", nargs="*")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--lane", action="store_true")
    parser.add_argument("--plan-dir", default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--sc-history", default=None)
    parser.add_argument("--base", default=None)
    parser.add_argument("-h", "--help", action="store_true")

    args = parser.parse_args(argv)

    if args.help:
        print(__doc__, file=sys.stderr)
        return 2

    if args.sc_history is not None:
        if (
            args.base is None
            or args.check
            or args.lane
            or args.plan_dir is not None
            or args.timeout is not None
            or args.targets
        ):
            print(_SC_HISTORY_USAGE, file=sys.stderr)
            return 2
        return _run_sc_history(args.sc_history, args.base)

    if args.base is not None:
        print(__doc__, file=sys.stderr)
        return 2
    timeout = 60 if args.timeout is None else args.timeout

    if specs_root is None:
        specs_root = _REPO_ROOT / "specs"

    plan_dir = Path(args.plan_dir) if args.plan_dir else None

    if args.lane:
        if args.check or not args.targets:
            print(__doc__, file=sys.stderr)
            return 2
        return _check_lane_targets(args.targets, specs_root, plan_dir=plan_dir)

    if len(args.targets) != 1:
        print(__doc__, file=sys.stderr)
        return 2

    summary_path = specs_root / args.targets[0] / "SUMMARY.md"
    if not summary_path.is_file():
        print(f"error: {summary_path} not found", file=sys.stderr)
        return 2

    text = summary_path.read_text(encoding="utf-8")
    rows = parse_verify_table(text)

    # SC coverage is a property of the tables, not of execution — it must hold in
    # single-target mode too. `--check <slug>` is the documented ship gate (and what
    # ci-strict-gate.sh runs), so an uncovered Success Criterion has to fail HERE,
    # not only under --lane.
    coverage_errors = _check_sc_coverage(text, summary_path, plan_dir)
    for error in coverage_errors:
        print(f"SC-COVERAGE  {error}")

    if not rows:
        print(
            "warning: no checks ran (all commands are placeholders or table is empty)"
        )
        if not args.check:
            # Still add Verified line even when no checks ran? No — don't
            # claim machine-verified if nothing ran. Just return 0 with warning.
            pass
        return 1 if coverage_errors else 0

    repo_root = _REPO_ROOT
    results = run_checks(rows, repo_root=repo_root, timeout=timeout)

    # SC expected exits from the sibling PLAN.md (empty when none) — a
    # Criterion-mapped row is also validated against its SC's expected exit.
    sc_map = _sc_map_for_summary(summary_path, plan_dir)

    failed = bool(coverage_errors)
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
                f"(limit: {timeout}s)"
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
