#!/usr/bin/env python3
"""Validate a PLAN.md against rules/plan-format.md.

Checks (see `.claude/rules/plan-format.md`):

1. Frontmatter exists and contains `slug` + `status`; `status` is one of the
   allowed values (proposed | active | paused | shipped).
2. Every `<task>` block carries non-empty `<files>`, `<action>`, `<verify>`,
   `<done>`.
3. `<verify>` is a single shell command (one line). `&&` chaining is allowed —
   the spec's own examples use it — but a multi-line block is not.
4. No file overlap between tasks that share the same `wave` (guardrail 1:
   parallel same-wave tasks must touch disjoint files to avoid merge conflicts).

Usage:
    python scripts/check_plan_format.py specs/<slug>/PLAN.md [more.md ...]

Exit code 0 = all files pass; 1 = at least one violation; 2 = bad invocation.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ALLOWED_STATUS = {"proposed", "active", "paused", "shipped"}
REQUIRED_TAGS = ("files", "action", "verify", "done")

# Story-size signal (advisory only — does not fail the lint). A single task touching
# more than this many files is a "consider splitting" smell: plan-format.md's own
# examples keep tasks at 1–3 files. Override with PLAN_MAX_FILES_PER_TASK.
MAX_FILES_PER_TASK = int(os.environ.get("PLAN_MAX_FILES_PER_TASK", "4"))

_TASK_RE = re.compile(r"<task\b([^>]*)>(.*?)</task>", re.DOTALL)
_ID_RE = re.compile(r'id="([^"]*)"')
_WAVE_RE = re.compile(r'wave="([^"]*)"')


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a leading `---` fenced flat key: value block. Returns {} if absent."""
    if not text.startswith("---"):
        return {}
    # Body after the opening fence; find the closing `---` on its own line.
    rest = text[3:]
    end = re.search(r"^---\s*$", rest, re.MULTILINE)
    if not end:
        return {}
    block = rest[: end.start()]
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def _tag(body: str, tag: str) -> str | None:
    """Return the inner text of <tag>…</tag>, or None if the tag is absent."""
    m = re.search(rf"<{tag}>(.*?)</{tag}>", body, re.DOTALL)
    return m.group(1) if m else None


def extract_tasks(text: str) -> list[dict]:
    """Extract every <task> block. Works whether tasks are raw or inside fenced
    ```xml code blocks (regex sees the literal text either way)."""
    tasks: list[dict] = []
    for m in _TASK_RE.finditer(text):
        attrs, body = m.group(1), m.group(2)
        tid = _ID_RE.search(attrs)
        wave = _WAVE_RE.search(attrs)
        files_raw = _tag(body, "files")
        files = (
            [p.strip() for p in files_raw.split(",") if p.strip()]
            if files_raw is not None
            else None
        )
        tasks.append(
            {
                "id": tid.group(1) if tid else "(no id)",
                "wave": wave.group(1).strip() if wave else None,
                "files_raw": files_raw,
                "files": files,
                "action": _tag(body, "action"),
                "verify": _tag(body, "verify"),
                "done": _tag(body, "done"),
            }
        )
    return tasks


def check_plan(text: str) -> list[str]:
    """Return a list of human-readable violation messages (empty == valid)."""
    errors: list[str] = []

    fm = parse_frontmatter(text)
    if not fm:
        errors.append("frontmatter: missing or malformed `---` block")
    else:
        if "slug" not in fm:
            errors.append("frontmatter: missing `slug`")
        if "status" not in fm:
            errors.append("frontmatter: missing `status`")
        elif fm["status"] not in ALLOWED_STATUS:
            errors.append(
                f"frontmatter: `status: {fm['status']}` not in {sorted(ALLOWED_STATUS)}"
            )

    tasks = extract_tasks(text)
    if not tasks:
        errors.append("tasks: no <task> blocks found")

    for t in tasks:
        label = f"task {t['id']}"
        for tag in REQUIRED_TAGS:
            value = t["files_raw"] if tag == "files" else t[tag]
            if value is None:
                errors.append(f"{label}: missing <{tag}>")
            elif not value.strip():
                errors.append(f"{label}: empty <{tag}>")

        verify = t["verify"]
        if verify is not None and verify.strip():
            if len(verify.strip().splitlines()) > 1:
                errors.append(
                    f"{label}: <verify> must be a single shell command "
                    "(found multiple lines)"
                )

    # Same-wave file-overlap check.
    by_wave: dict[str, list[dict]] = {}
    for t in tasks:
        if t["wave"] and t["files"]:
            by_wave.setdefault(t["wave"], []).append(t)
    for wave, group in by_wave.items():
        if len(group) < 2:
            continue
        seen: dict[str, str] = {}  # file -> first task id that claimed it
        for t in group:
            for f in t["files"]:
                if f in seen and seen[f] != t["id"]:
                    errors.append(
                        f"wave {wave}: file `{f}` claimed by both "
                        f"task {seen[f]} and task {t['id']}"
                    )
                else:
                    seen.setdefault(f, t["id"])

    return errors


def story_size_warnings(text: str, max_files: int = MAX_FILES_PER_TASK) -> list[str]:
    """Advisory (non-failing) story-size signals: a task touching more than
    `max_files` files likely should be split. Returns human-readable warnings."""
    warnings: list[str] = []
    for t in extract_tasks(text):
        files = t["files"]
        if files and len(files) > max_files:
            warnings.append(
                f"task {t['id']}: touches {len(files)} files (> {max_files}) "
                "— consider splitting into smaller tasks"
            )
    return warnings


def check_file(path: Path) -> list[str]:
    if not path.is_file():
        return [f"{path}: not a file"]
    return check_plan(path.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    failed = False
    for arg in argv:
        path = Path(arg)
        errors = check_file(path)
        if errors:
            failed = True
            print(f"✗ {path} — {len(errors)} violation(s):")
            for e in errors:
                print(f"    - {e}")
        else:
            print(f"✓ {path}")
        # Advisory story-size signals — printed but never change the exit code.
        if path.is_file():
            for w in story_size_warnings(path.read_text(encoding="utf-8")):
                print(f"    ⚠ {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
