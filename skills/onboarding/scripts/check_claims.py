#!/usr/bin/env python3
"""Check the grounded claims of one OpenWiki page, or the drift of the wiki from HEAD.

Run from the repository root. Paths are relative to the current directory.

  check_claims.py <page>    <page> is relative to openwiki/, for example quickstart.md.
  check_claims.py --status  Compare the wiki gitHead to HEAD.

Verifies:
  - For each claim, each evidence item hash: repo-lines-v1 is sha256 of lines a..b joined with
    a newline plus a trailing newline; repo-file-v1 is sha256 of the raw file bytes.
  - That the gitHead in openwiki/.last-update.json is HEAD or an ancestor of HEAD, and the count
    of commits between them.

Does not verify:
  - That a claim statement is true of the cited lines. A matching hash shows only that the cited
    source did not change since the wiki was written.
  - The base64 context metadata of repo-lines-v1. A moved block reads as stale.
  - Evidence in any other format (result unknown), or source outside the cited ranges.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

WIKI = Path("openwiki")
RANK = {"ok": 0, "stale": 1, "unknown": 2, "missing": 3}
LINES_RE = re.compile(r"^(?P<path>.+)#L(?P<a>\d+)-L(?P<b>\d+)$")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def check_evidence(item: dict) -> tuple[str, str]:
    """Return (result, display path) for one evidence item."""
    resource = str(item.get("resource", ""))
    version = str(item.get("version", ""))
    target = resource.removeprefix("repo://")
    parts = version.split(":")
    if not resource.startswith("repo://") or len(parts) < 3 or parts[1] != "sha256":
        return "unknown", target
    match = LINES_RE.match(target)
    if parts[0] == "repo-lines-v1" and match:
        path = Path(match["path"])
        if not path.is_file():
            return "missing", target
        lines = path.read_bytes().split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
        a, b = int(match["a"]), int(match["b"])
        if a < 1 or b < a or b > len(lines):
            return "missing", target
        data = b"\n".join(lines[a - 1:b]) + b"\n"
    elif parts[0] == "repo-file-v1" and not match:
        path = Path(target)
        if not path.is_file():
            return "missing", target
        data = path.read_bytes()
    else:
        return "unknown", target
    return ("ok" if hashlib.sha256(data).hexdigest() == parts[2] else "stale"), target


def page_rows(page: str) -> tuple[int, str, list[tuple[str, str, str]]]:
    """Return (exit code, message, rows); rows are (result, target, statement) for codes 0 and 1."""
    if not WIKI.is_dir():
        return 2, f"no-wiki {WIKI}/", []
    page_path = WIKI / page
    if not page_path.is_file():
        return 4, f"page-missing {page_path}", []
    claims_path = (WIKI / ".claims" / page).with_suffix(".json")
    if not claims_path.is_file():
        return 3, f"no-claims {claims_path}", []
    try:
        claims = json.loads(claims_path.read_text(encoding="utf-8"))["claims"]
    except (ValueError, KeyError, TypeError):
        return 3, f"no-claims {claims_path} (unparseable)", []
    rows = []
    for claim in claims:
        results = [check_evidence(item) for item in claim.get("evidence") or []]
        result, target = max(results, key=lambda r: RANK[r[0]]) if results else ("unknown", "-")
        rows.append((result, target, claim.get("statement", "")))
    return (0 if all(r[0] == "ok" for r in rows) else 1), "", rows


def check_page(page: str) -> int:
    code, message, rows = page_rows(page)
    if message:
        print(message)
    for result, target, statement in rows:
        print(f"{result} {target} {statement}")
    return code


def check_status() -> int:
    if not WIKI.is_dir():
        print("no-wiki")
        return 2
    try:
        record = json.loads((WIKI / ".last-update.json").read_text(encoding="utf-8"))
        wiki_head = str(record["gitHead"])
        status = record.get("status")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print("unknown-drift .last-update.json absent or unparseable")
        return 3
    if status != "complete":
        print(f"unknown-drift wiki status is {status}")
        return 3
    head = git("rev-parse", "HEAD").stdout.strip()
    if wiki_head == head:
        print("current")
        return 0
    if git("merge-base", "--is-ancestor", wiki_head, "HEAD").returncode != 0:
        print(f"unknown-drift gitHead {wiki_head} is not an ancestor of HEAD")
        return 3
    count = git("rev-list", "--count", f"{wiki_head}..HEAD").stdout.strip()
    print(f"behind {count}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("page", nargs="?", help="page path relative to openwiki/")
    group.add_argument("--status", action="store_true", help="report wiki drift from HEAD")
    args = parser.parse_args()
    return check_status() if args.status else check_page(args.page)


if __name__ == "__main__":
    sys.exit(main())
