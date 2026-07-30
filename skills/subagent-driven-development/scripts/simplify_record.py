#!/usr/bin/env python3
"""Mechanical begin/finish recorder for the required Claude Code `/simplify` stage.

`begin()` refuses a dirty worktree and records the resolved base/pre-simplify
checkpoint SHAs plus the Claude Code capability in effect. `finish()` is
called after the real `/simplify` invocation (and any resulting commit); it
resolves the post-simplify commit and builds a validated `type: simplify`
review-receipt entry from the outcome, changed files, verification result,
and delta review verdict.

This module only records mechanical evidence: it never invokes `/simplify`
itself, and it does not decide whether a failing outcome should block a push
— `scripts/check_review_receipt.py --require-simplify-if` is the fail-closed
consumer that makes that call at receipt-validation time.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Repo root: this file lives at <root>/skills/subagent-driven-development/scripts/.
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"could not load {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Cross-directory reuse, loaded by explicit path (not a bare `import`) so this
# module works regardless of the caller's sys.path/cwd — see check_review_receipt.py
# for the identical convention used for its own same-directory sibling import.
check_claude_simplify = _load_module(
    "check_claude_simplify", _REPO_ROOT / "scripts" / "check_claude_simplify.py"
)
check_review_receipt = _load_module(
    "check_review_receipt", _REPO_ROOT / "scripts" / "check_review_receipt.py"
)


class SimplifyRecordError(Exception):
    """Raised when the worktree, git history, or supplied evidence is invalid."""


def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True)


def is_dirty(repo_root: Path) -> bool:
    """True if the worktree has any uncommitted change (tracked or untracked)."""
    proc = _run_git(repo_root, "status", "--porcelain")
    if proc.returncode != 0:
        raise SimplifyRecordError(f"git status failed: {proc.stderr.strip()}")
    return bool(proc.stdout.strip())


def resolve_sha(repo_root: Path, ref: str) -> str:
    """Resolve ref to a full lowercase 40-hex commit sha; raise if it cannot be."""
    proc = _run_git(repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if proc.returncode != 0:
        raise SimplifyRecordError(f"cannot resolve ref {ref!r}: {proc.stderr.strip()}")
    sha = proc.stdout.strip()
    if not _SHA_RE.fullmatch(sha):
        raise SimplifyRecordError(
            f"resolved sha for {ref!r} is not 40-hex lowercase: {sha!r}"
        )
    return sha


def is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    """True if ancestor is an ancestor of, or identical to, descendant."""
    result = check_review_receipt._is_ancestor(repo_root, ancestor, descendant)
    if result is None:
        raise SimplifyRecordError(
            f"cannot determine ancestry between {ancestor} and {descendant}"
        )
    return result


def begin(
    *,
    repo_root: Path,
    base_ref: str,
    target_ref: str = "HEAD",
    claude_code_version: str | None,
) -> dict[str, Any]:
    """Refuse a dirty worktree; resolve and record the base/pre checkpoint.

    Fails closed (raises `SimplifyRecordError`) on a dirty worktree, an
    unresolved base/target ref, a base and target resolving to the same
    commit, a base that is not an ancestor of the target, or a Claude Code
    version below the supported capability floor.
    """
    if is_dirty(repo_root):
        raise SimplifyRecordError(
            "dirty worktree: commit or stash pending changes before starting "
            "the simplify stage"
        )
    base_sha = resolve_sha(repo_root, base_ref)
    pre_sha = resolve_sha(repo_root, target_ref)
    if base_sha == pre_sha:
        raise SimplifyRecordError(
            f"base {base_sha} and target {pre_sha} resolve to the same commit; "
            f"there is no diff to simplify"
        )
    if not is_ancestor(repo_root, base_sha, pre_sha):
        raise SimplifyRecordError(
            f"base {base_sha} is not an ancestor of resolved target {pre_sha}"
        )
    capability = check_claude_simplify.capability_status(claude_code_version)
    if capability["status"] != "supported":
        raise SimplifyRecordError(
            f"Claude Code capability is {capability['status']} "
            f"(version={capability['version']!r}); minimum required is "
            f"{capability['minimum']}"
        )
    return {
        "base_sha": base_sha,
        "pre_sha": pre_sha,
        "claude_code_version": capability["version"],
    }


def finish(
    *,
    repo_root: Path,
    begin_state: dict[str, Any],
    target_ref: str = "HEAD",
    outcome: str,
    changed_files: list[str],
    reason: str,
    verification_result: str | None,
    delta_verdict: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve the post-simplify commit and build a validated `type: simplify` entry.

    Call after the real `/simplify` invocation (and any resulting commit).
    Raises `SimplifyRecordError` if the post-SHA does not descend from the
    recorded pre-SHA, or if the supplied evidence is not structurally valid
    (see `check_review_receipt.simplify_shape_error`: SHA format, version
    floor, bounded reason/outcome vocabulary, and changed/no_op evidence-shape
    consistency). A structurally valid but *failing* changed outcome (e.g.
    failing verification, or a non-passing delta verdict) is still returned
    with `result: "fail"` — deciding whether a failure blocks a push is not
    this helper's job; `check_review_receipt.py --require-simplify-if` does
    that at receipt-validation time.
    """
    post_sha = resolve_sha(repo_root, target_ref)
    if not is_ancestor(repo_root, begin_state["pre_sha"], post_sha):
        raise SimplifyRecordError(
            f"post-SHA {post_sha} is not a descendant of recorded pre-SHA "
            f"{begin_state['pre_sha']}"
        )

    entry: dict[str, Any] = {
        "type": "simplify",
        "result": "fail",  # placeholder — recomputed below once shape is confirmed
        "blocking_open": 0,
        "base_sha": begin_state["base_sha"],
        "pre_sha": begin_state["pre_sha"],
        "post_sha": post_sha,
        "claude_code_version": begin_state["claude_code_version"],
        "reason": reason,
        "outcome": outcome,
        "changed_files": sorted(changed_files),
        "verification_result": verification_result,
        "delta_verdict": delta_verdict,
    }
    shape_error = check_review_receipt.simplify_shape_error(entry)
    if shape_error is not None:
        raise SimplifyRecordError(shape_error)

    entry["result"] = (
        "pass" if check_review_receipt.simplify_entry_passes(entry) else "fail"
    )
    return entry


def _read_json_arg(raw: str | None) -> Any:
    if raw is None:
        return None
    return json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mechanical begin/finish recorder for the required Claude Code /simplify stage."
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    sub = parser.add_subparsers(dest="command", required=True)

    begin_parser = sub.add_parser("begin", help="record the pre-simplify checkpoint")
    begin_parser.add_argument("--base", required=True, metavar="BASE_REF")
    begin_parser.add_argument("--target", default="HEAD", metavar="TARGET_REF")
    begin_parser.add_argument("--claude-code-version", default=None)
    begin_parser.add_argument("--output", type=Path)

    finish_parser = sub.add_parser("finish", help="record the post-simplify outcome")
    finish_parser.add_argument(
        "--begin-state", type=Path, required=True, help="path to begin()'s JSON output"
    )
    finish_parser.add_argument("--target", default="HEAD", metavar="TARGET_REF")
    finish_parser.add_argument("--outcome", required=True, choices=("changed", "no_op"))
    finish_parser.add_argument("--changed-files", nargs="*", default=[])
    finish_parser.add_argument("--reason", required=True)
    finish_parser.add_argument(
        "--verification-result", default=None, choices=(None, "pass", "fail")
    )
    finish_parser.add_argument(
        "--delta-verdict",
        default=None,
        help='JSON object, e.g. {"spec_verdict":"pass","quality_verdict":"approved"}',
    )
    finish_parser.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    try:
        if args.command == "begin":
            result = begin(
                repo_root=repo_root,
                base_ref=args.base,
                target_ref=args.target,
                claude_code_version=args.claude_code_version,
            )
        else:
            begin_state = json.loads(args.begin_state.read_text(encoding="utf-8"))
            result = finish(
                repo_root=repo_root,
                begin_state=begin_state,
                target_ref=args.target,
                outcome=args.outcome,
                changed_files=list(args.changed_files),
                reason=args.reason,
                verification_result=args.verification_result,
                delta_verdict=_read_json_arg(args.delta_verdict),
            )
    except SimplifyRecordError as error:
        print(f"simplify-record: {error}", file=sys.stderr)
        return 1

    payload = json.dumps(result, sort_keys=True)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
