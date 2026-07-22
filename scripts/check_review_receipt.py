#!/usr/bin/env python3
"""Validate a spec's review receipt against the exact reviewed HEAD.

A review receipt (`specs/<slug>/.review-receipt.json`) records that a review
passed at a specific commit. It is only valid while HEAD still points at that
commit: a fix committed after the review advances HEAD, makes the receipt stale,
and this checker fails — so a stale review can never silently authorize a newer
HEAD.

Usage:
    python3 scripts/check_review_receipt.py <specs/slug-dir> [--require type1,type2]

    <specs/slug-dir>   Directory holding the receipt (e.g. specs/gh-143-...).
                       The receipt is <that-dir>/.review-receipt.json.
    --require t1,t2    Comma-separated review `type` values that must each be
                       present with result `pass`.

The reviewed HEAD is resolved with `git rev-parse HEAD` run in the repo that
contains the slug dir.

Exit codes:
    0  Receipt valid, and (if --require given) all required types present & pass.
    1  Any check failed — one line to stderr naming the failing check
       (missing / malformed / stale-sha / review-failed / blocking-open /
       missing-required-type).
    2  Bad invocation.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RECEIPT_NAME = ".review-receipt.json"

# reviewed_head_sha MUST be a resolved full commit sha. A symbolic ref (e.g. the
# literal "HEAD", "@", or a branch name) would make `git diff <ref>..<HEAD>`
# resolve the ref to the current commit and diff the repo against itself —
# always empty — silently defeating the stale-sha gate. Require 40 hex chars.
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _git_head(slug_dir: Path) -> str | None:
    """Return the current HEAD sha of the repo containing slug_dir, or None."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=slug_dir,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _changed_files(slug_dir: Path, a: str, b: str) -> list[str] | None:
    """File paths changed between commits a and b, or None if the range is undiffable.

    Used to distinguish a review-neutral bookkeeping advance (the plan-`shipped`
    commit only touches `specs/`) from an unreviewed code change after review.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"{a}..{b}"],
            cwd=slug_dir,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return [line for line in proc.stdout.splitlines() if line.strip()]


def check_receipt(slug_dir: Path, require: list[str]) -> str | None:
    """Validate the receipt. Return a one-line failure reason, or None if valid."""
    receipt_path = slug_dir / RECEIPT_NAME
    if not receipt_path.is_file():
        return f"missing: no review receipt at {receipt_path}"

    try:
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return f"malformed: {receipt_path} is not valid JSON ({exc})"

    if not isinstance(data, dict):
        return f"malformed: {receipt_path} is not a JSON object"

    reviewed = data.get("reviewed_head_sha")
    if not isinstance(reviewed, str) or not reviewed.strip():
        return f"malformed: {receipt_path} has no reviewed_head_sha"
    if not _SHA_RE.match(reviewed.strip()):
        return (
            f"malformed: reviewed_head_sha {reviewed.strip()!r} is not a resolved "
            f"40-char hex commit sha (symbolic refs like 'HEAD' are rejected)"
        )

    head = _git_head(slug_dir)
    if head is None:
        return f"stale-sha: cannot resolve git HEAD for {slug_dir}"
    reviewed = reviewed.strip()
    if reviewed != head:
        # HEAD moved since review. Tolerate a review-neutral bookkeeping advance —
        # the plan-`shipped` transition (finishing-a-development-branch Step 4)
        # commits only `specs/`, carries no reviewable code, and must not stale a
        # valid receipt. Any change OUTSIDE specs/ since the review is unreviewed
        # code and stays fatal.
        changed = _changed_files(slug_dir, reviewed, head)
        if changed is None:
            return (
                f"stale-sha: receipt reviewed {reviewed[:12]} but HEAD is "
                f"{head[:12]} and the range is undiffable — re-review at current HEAD"
            )
        unreviewed = [p for p in changed if not p.startswith("specs/")]
        if unreviewed:
            return (
                f"stale-sha: receipt reviewed {reviewed[:12]} but HEAD {head[:12]} "
                f"adds unreviewed changes outside specs/ (e.g. {unreviewed[0]}) — "
                f"re-review at current HEAD"
            )
        # else: specs/-only advance (bookkeeping) — receipt remains valid.

    reviews = data.get("reviews")
    if not isinstance(reviews, list):
        return f"malformed: {receipt_path} has no reviews list"

    for review in reviews:
        if not isinstance(review, dict):
            return f"malformed: {receipt_path} has a non-object review entry"
        rtype = review.get("type", "<unknown>")
        if review.get("result") == "fail":
            return f"review-failed: review '{rtype}' has result: fail"
        blocking = review.get("blocking_open", 0)
        if isinstance(blocking, bool) or not isinstance(blocking, int):
            return f"malformed: review '{rtype}' has non-integer blocking_open"
        if blocking > 0:
            return f"blocking-open: review '{rtype}' has {blocking} blocking open"

    passed_types = {
        r.get("type")
        for r in reviews
        if isinstance(r, dict) and r.get("result") == "pass"
    }
    for req in require:
        if req not in passed_types:
            return f"missing-required-type: required review '{req}' not present with result pass"

    return None


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="check_review_receipt.py", add_help=True)
    parser.add_argument("slug_dir")
    parser.add_argument("--require", default="")
    args = parser.parse_args(argv)

    require = [t.strip() for t in args.require.split(",") if t.strip()]

    slug_dir = Path(args.slug_dir)
    if not slug_dir.is_dir():
        print(f"missing: {slug_dir} is not a directory", file=sys.stderr)
        return 1

    reason = check_receipt(slug_dir, require)
    if reason is not None:
        print(reason, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
