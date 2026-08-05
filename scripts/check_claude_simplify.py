#!/usr/bin/env python3
"""Resolve the capability and signal policy for Claude Code's `/simplify`.

The checker is intentionally independent of the current Git branch. Callers
must resolve and supply BASE, HEAD, changed paths, and Git numstat explicitly.
The resulting JSON is suitable for orchestration and durable review evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


MINIMUM_VERSION = (2, 1, 154)
TINY_SOURCE_LINE_THRESHOLD = 150
LANES = frozenset({"tiny", "normal", "high-risk"})
POLICY_REASONS = frozenset(
    {
        "no_changes",
        "documentation_only",
        "specs_bookkeeping_only",
        "evaluation_only",
        "vendor_only",
        "generated_only",
        "excluded_only",
        "tiny_source_change",
        "oversized_tiny_source_change",
        "non_tiny_source_change",
    }
)

_VERSION = re.compile(r"(?<![\d.])v?(\d+)\.(\d+)\.(\d+)(?![\d.]|[-+])", re.IGNORECASE)
_FULL_SHA = re.compile(r"[0-9a-f]{40}")
_DOCUMENT_NAMES = frozenset(
    {
        "license",
        "license.txt",
        "notice",
        "notice.txt",
        "readme",
        "changelog",
        "authors",
        "contributors",
    }
)
_DOCUMENT_SUFFIXES = frozenset({".md", ".mdx", ".rst", ".adoc"})
_VENDOR_PARTS = frozenset(
    {"vendor", "vendors", "third_party", "third-party", "node_modules"}
)
_ROOT_GENERATED_DIRS = frozenset(
    {
        "dist",
        "build",
        "coverage",
        "out",
    }
)
_UNAMBIGUOUS_GENERATED_PARTS = frozenset({".claude", "generated", "__pycache__"})
# Roots whose Markdown is executable program text, not prose (E006). Portable:
# a repository without these directories simply never matches. `templates/` is
# deliberately absent — it ships forms for consumers to fill in.
_PROGRAM_TEXT_ROOTS = frozenset({"skills", "agents", "rules"})
_GENERATED_NAMES = frozenset(
    {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "cargo.lock",
        "go.sum",
        "plan.html",
        ".coverage",
    }
)


def parse_version(raw: str | None) -> tuple[int, int, int] | None:
    """Parse exactly one stable semantic version from Claude Code output."""
    if raw is None or not raw.strip():
        return None
    matches = _VERSION.findall(raw.strip())
    if len(matches) != 1:
        return None
    return tuple(int(part) for part in matches[0])  # type: ignore[return-value]


def capability_status(raw: str | None) -> dict[str, Any]:
    """Return a bounded capability status without deciding policy."""
    parsed = parse_version(raw)
    minimum = ".".join(str(part) for part in MINIMUM_VERSION)
    if raw is None or not raw.strip():
        return {"status": "missing", "version": None, "minimum": minimum}
    if parsed is None:
        return {"status": "malformed", "version": None, "minimum": minimum}
    normalized = ".".join(str(part) for part in parsed)
    status = "supported" if parsed >= MINIMUM_VERSION else "too_old"
    return {"status": status, "version": normalized, "minimum": minimum}


def _normalized_path(raw: str) -> str:
    if not raw:
        raise ValueError("changed paths must not contain blank entries")
    if raw != raw.strip():
        raise ValueError(f"changed path has unsafe surrounding whitespace: {raw!r}")
    if len(raw) > 1 and raw.startswith('"') and raw.endswith('"'):
        raise ValueError(
            f"changed path is Git-quoted: {raw!r} — re-run the producer command "
            f"with `git -c core.quotePath=false ...` (`--numstat` has no `-z`)"
        )
    if "\\" in raw:
        raise ValueError(f"changed path uses unsupported backslash spelling: {raw!r}")
    parsed = PurePosixPath(raw)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise ValueError(f"changed path must be repository-relative: {raw!r}")
    normalized = str(parsed)
    if not parsed.parts or normalized != raw:
        raise ValueError(f"changed path must use canonical POSIX spelling: {raw!r}")
    return normalized


def _has_directory_subtree(parts: tuple[str, ...], authorities: frozenset[str]) -> bool:
    """Return true only when an authority token has a child path component."""
    return any(
        part in authorities and index < len(parts) - 1
        for index, part in enumerate(parts)
    )


def classify_path(raw: str) -> str:
    """Classify a path as one permitted exclusion or reviewable source.

    Directory authorities are matched **exact-case**: on a case-sensitive
    filesystem `Docs/` is a different directory from `docs/`, so folding case
    there would exempt real source from the stage on a case-variant spelling.
    File names and suffixes still fold case — `README`, `.MD`, and `PLAN.html`
    are the same file whatever the shell caps look like.
    """
    path = _normalized_path(raw)
    parsed = PurePosixPath(path)
    parts = parsed.parts
    lowered_name = parsed.name.lower()

    # More specific directory authorities take precedence over file suffixes.
    if _has_directory_subtree(parts, frozenset({".claude"})):
        return "generated"
    if len(parts) > 1 and parts[0] == "specs":
        return "specs_bookkeeping"
    if (
        len(parts) > 2
        and parts[0] == "evals"
        and any(
            part in {"results", "result", "raw", "transcripts"} for part in parts[1:-1]
        )
    ):
        return "evaluation"
    if _has_directory_subtree(parts, _VENDOR_PARTS):
        return "vendor"
    if (len(parts) > 1 and parts[0] in _ROOT_GENERATED_DIRS) or _has_directory_subtree(
        parts, _UNAMBIGUOUS_GENERATED_PARTS
    ):
        return "generated"
    if (
        lowered_name in _GENERATED_NAMES
        or ".generated." in lowered_name
        or lowered_name.endswith((".min.js", ".min.css", ".map"))
    ):
        return "generated"
    # Program text that happens to be Markdown. In a prompt-driven harness a
    # SKILL.md, an agent definition, a rule, a reference, or a prompt fragment
    # IS the program — editing one changes runtime behavior. Classifying those
    # as documentation excluded the highest-risk change class from the stage
    # (ESCALATIONS.md E006). Prose ABOUT the surface stays excluded: README.md
    # is a human-facing index, and `*.template.md` is a template a consumer
    # fills in, not an instruction any agent executes.
    # Matched case-INSENSITIVELY, unlike the exclusion authorities above. That
    # rule exists so a case variant can never shrink coverage; here folding case
    # only ever grows it, so `Skills/foo/SKILL.md` stays reviewable too.
    if (
        len(parts) > 1
        and parts[0].lower() in _PROGRAM_TEXT_ROOTS
        and parsed.suffix.lower() in _DOCUMENT_SUFFIXES
        and lowered_name != "readme.md"
        and not lowered_name.endswith(".template.md")
    ):
        return "reviewable"
    if (
        (len(parts) > 1 and parts[0] in {"doc", "docs", "documentation"})
        or lowered_name in _DOCUMENT_NAMES
        or parsed.suffix.lower() in _DOCUMENT_SUFFIXES
    ):
        return "documentation"
    return "reviewable"


def _rename_destination(raw: str) -> str:
    """Normalize Git's human-readable numstat rename notation to its new path.

    The new-mid segment may be EMPTY: moving a file up a level inside a shared
    prefix spells as `a/{b/c => }/deep.c`, which rebuilds to `a//deep.c` and
    must collapse to `a/deep.c`. Requiring at least one character there sent
    that spelling to the unbraced `rsplit` branch, which returned the fragment
    `}/deep.c` and made the whole policy decision fail as malformed input.
    Git only uses the braced form when a common prefix exists, so the rebuilt
    path can never start with the collapsed separator.
    """
    path = raw
    braced = re.search(r"\{[^{}]*? => ([^{}]*)\}", path)
    if braced:
        rebuilt = path[: braced.start()] + braced.group(1) + path[braced.end() :]
        return re.sub(r"/{2,}", "/", rebuilt)
    if " => " in path:
        return path.rsplit(" => ", 1)[1]
    return path


def parse_numstat(raw: str) -> dict[str, int]:
    """Parse `git diff --numstat`, counting additions plus deletions.

    Binary rows are retained with a zero count. Malformed rows are rejected so
    an oversized tiny diff cannot silently become advisory.
    """
    counts: dict[str, int] = {}
    for line_number, line in enumerate(raw.split("\n"), 1):
        if not line:
            continue
        fields = line.split("\t", 2)
        if len(fields) != 3:
            raise ValueError(f"malformed numstat line {line_number}")
        added, deleted, raw_path = fields
        path = _normalized_path(_rename_destination(raw_path))
        if (added, deleted) == ("-", "-"):
            count = 0
        elif added.isdigit() and deleted.isdigit():
            count = int(added) + int(deleted)
        else:
            raise ValueError(f"malformed numstat counts on line {line_number}")
        counts[path] = counts.get(path, 0) + count
    return counts


def _excluded_reason(categories: set[str]) -> str:
    if not categories:
        return "no_changes"
    if len(categories) == 1:
        only = next(iter(categories))
        return {
            "documentation": "documentation_only",
            "specs_bookkeeping": "specs_bookkeeping_only",
            "evaluation": "evaluation_only",
            "vendor": "vendor_only",
            "generated": "generated_only",
        }[only]
    return "excluded_only"


def evaluate_policy(
    *,
    lane: str,
    base: str,
    head: str,
    changed_paths: Iterable[str],
    numstat: str,
    version: str | None,
) -> dict[str, Any]:
    """Return the deterministic simplify policy and capability decision."""
    if lane not in LANES:
        raise ValueError(f"unsupported lane: {lane!r}")
    if not _FULL_SHA.fullmatch(base or "") or not _FULL_SHA.fullmatch(head or ""):
        raise ValueError("base and head must each be a resolved lowercase 40-hex SHA")
    if base == head:
        raise ValueError("base and head must identify a non-empty target range")

    paths = sorted(set(_normalized_path(path) for path in changed_paths))
    categories = {path: classify_path(path) for path in paths}
    reviewable = sorted(
        path for path, category in categories.items() if category == "reviewable"
    )
    excluded_categories = {
        category for category in categories.values() if category != "reviewable"
    }
    counts = parse_numstat(numstat)
    if set(counts) != set(paths):
        missing = sorted(set(paths) - set(counts))
        unexpected = sorted(set(counts) - set(paths))
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unexpected:
            details.append("unexpected: " + ", ".join(unexpected))
        raise ValueError(
            "changed paths and numstat disagree (" + "; ".join(details) + ")"
        )
    changed_source_lines = sum(counts[path] for path in reviewable)

    if not reviewable:
        required = False
        reason = _excluded_reason(excluded_categories)
    elif lane == "tiny" and changed_source_lines <= TINY_SOURCE_LINE_THRESHOLD:
        required = False
        reason = "tiny_source_change"
    elif lane == "tiny":
        required = True
        reason = "oversized_tiny_source_change"
    else:
        required = True
        reason = "non_tiny_source_change"

    if reason not in POLICY_REASONS:  # Defensive assertion for future policy edits.
        raise AssertionError(f"unbounded policy reason: {reason}")
    capability = capability_status(version)
    ok = not required or capability["status"] == "supported"
    result: dict[str, Any] = {
        "required": required,
        "reason": reason,
        "capability": capability,
        "target": f"{base}..{head}",
        "base": base,
        "head": head,
        "reviewable_paths": reviewable,
        "excluded_paths": sorted(
            path for path, category in categories.items() if category != "reviewable"
        ),
        "changed_source_lines": changed_source_lines,
        "ok": ok,
    }
    if not ok:
        result["error"] = "required_capability_unavailable"
    return result


def _read_changed_paths(path: Path) -> list[str]:
    return [line for line in path.read_bytes().decode("utf-8").split("\n") if line]


def _self_test_policy() -> int:
    base = "a" * 40
    head = "b" * 40
    source = evaluate_policy(
        lane="normal",
        base=base,
        head=head,
        changed_paths=["src/main.py"],
        numstat="1\t0\tsrc/main.py\n",
        version="2.1.154",
    )
    tiny_boundary = evaluate_policy(
        lane="tiny",
        base=base,
        head=head,
        changed_paths=["src/main.py"],
        numstat="100\t50\tsrc/main.py\n",
        version="2.1.154",
    )
    excluded = evaluate_policy(
        lane="high-risk",
        base=base,
        head=head,
        changed_paths=["docs/guide.md"],
        numstat="999\t0\tdocs/guide.md\n",
        version=None,
    )
    old = evaluate_policy(
        lane="normal",
        base=base,
        head=head,
        changed_paths=["src/main.py"],
        numstat="1\t0\tsrc/main.py\n",
        version="2.1.153",
    )
    passed = (
        source["required"]
        and source["ok"]
        and not tiny_boundary["required"]
        and excluded["reason"] == "documentation_only"
        and not excluded["required"]
        and old["required"]
        and not old["ok"]
    )
    if not passed:
        print("simplify-policy: self-test failed", file=sys.stderr)
        return 1
    print("simplify-policy: self-test passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve whether Claude Code /simplify is required for an explicit diff."
    )
    parser.add_argument("--lane", choices=sorted(LANES))
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--changed-paths-file", type=Path)
    parser.add_argument("--numstat-file", type=Path)
    parser.add_argument("--claude-code-version")
    parser.add_argument("--self-test-policy", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test_policy:
        return _self_test_policy()
    missing = [
        option
        for option, value in (
            ("--lane", args.lane),
            ("--base", args.base),
            ("--head", args.head),
            ("--changed-paths-file", args.changed_paths_file),
            ("--numstat-file", args.numstat_file),
        )
        if value is None
    ]
    if missing:
        parser.error("required arguments: " + ", ".join(missing))
    try:
        result = evaluate_policy(
            lane=args.lane,
            base=args.base,
            head=args.head,
            changed_paths=_read_changed_paths(args.changed_paths_file),
            numstat=args.numstat_file.read_bytes().decode("utf-8"),
            version=args.claude_code_version,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
