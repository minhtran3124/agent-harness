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
import subprocess
import sys
from pathlib import Path

RECEIPT_NAME = ".review-receipt.json"


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

    head = _git_head(slug_dir)
    if head is None:
        return f"stale-sha: cannot resolve git HEAD for {slug_dir}"
    if reviewed.strip() != head:
        return (
            f"stale-sha: receipt reviewed {reviewed.strip()[:12]} "
            f"but HEAD is {head[:12]} — re-review at current HEAD"
        )

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
