#!/usr/bin/env python3
"""Aggregate consistency check for the required Claude Code `/simplify` stage.

Mirrors scripts/check_manifest.py's pattern: a stdlib-only `check(root) -> int` that collects
one "simplify-adoption: <category> drift: <detail>" line per problem. Exit 0 = consistent.
Exit 1 = drift.

Checks:
  A. policy       — rules/simplify-stage.md's stated version floor matches
                     scripts/check_claude_simplify.py's MINIMUM_VERSION.
  B. ordering     — skills/subagent-driven-development/SKILL.md hands off to
                     references/simplify-stage.md strictly before references/review-chain.md.
  C. receipt      — scripts/check_review_receipt.py still defines --require-simplify-if.
  D. finish-gate  — skills/finishing-a-development-branch/SKILL.md still requires
                     --require-simplify-if before push.
  E. hook         — hooks/risk-corroboration.sh's tiny-lane SIZE_THRESHOLD matches
                     scripts/check_claude_simplify.py's TINY_SOURCE_LINE_THRESHOLD.
  F. documentation — no stale claim that /simplify is optional on required scope or that it
                     owns correctness, in CLAUDE.md / HARNESS.md / skills/README.md / rules/*.md.
  G. deployed parity — when a deployed .claude/ mirror exists, the simplify-stage contract's
                     surface/consumer files under a synced top-level dir are not stale there.
                     No .claude/ mirror => skip this check with a note (pre-deploy is valid).

Run: python3 scripts/check_simplify_adoption.py [--root DIR]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

PREFIX = "simplify-adoption"

# Top-level dirs scripts/deploy-harness.sh mirrors whole into .claude/ (SYNCED_DIRS_RE there).
_DEPLOY_PREFIXES = ("skills/", "agents/", "hooks/", "rules/", "templates/", "runtime/")

_VERSION_FLOOR_RE = re.compile(
    r"supported by Claude Code \*\*(\d+\.\d+\.\d+) or newer\*\*"
)
_HOOK_TINY_THRESHOLD_RE = re.compile(r"tiny\)\s*SIZE_THRESHOLD=(\d+)")


def _load_check_claude_simplify(root: Path) -> ModuleType | None:
    """Import scripts/check_claude_simplify.py by path; None if unavailable.

    Reading its actual MINIMUM_VERSION/TINY_SOURCE_LINE_THRESHOLD constants this
    way, instead of regexing the source text, can't misparse and surfaces a
    renamed/removed constant as an AttributeError rather than a silent miss.
    """
    path = root / "scripts" / "check_claude_simplify.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("check_claude_simplify", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_STALE_DOC_PATTERNS = [
    re.compile(r"/simplify[^.\n]{0,80}\boptional\b", re.IGNORECASE),
    re.compile(r"\boptional\b[^.\n]{0,80}/simplify", re.IGNORECASE),
    re.compile(r"/simplify[^.\n]{0,80}\bowns?\s+correctness\b", re.IGNORECASE),
]

_DOC_STATIC_FILES = ("CLAUDE.md", "HARNESS.md", "skills/README.md")


def _problem(problems: list[str], kind: str, detail: str) -> None:
    problems.append(f"{PREFIX}: {kind} drift: {detail}")


def _check_version_floor(
    root: Path, problems: list[str], checker: ModuleType | None = None
) -> None:
    policy_path = root / "rules" / "simplify-stage.md"
    if checker is None:
        checker = _load_check_claude_simplify(root)
    if not policy_path.is_file() or checker is None:
        _problem(
            problems,
            "policy",
            f"missing {policy_path} or scripts/check_claude_simplify.py",
        )
        return

    m_policy = _VERSION_FLOOR_RE.search(policy_path.read_text(encoding="utf-8"))
    if not m_policy:
        _problem(
            problems,
            "policy",
            f"{policy_path} has no 'supported by Claude Code **X.Y.Z or newer**' statement",
        )
        return

    try:
        checker_version = ".".join(str(part) for part in checker.MINIMUM_VERSION)
    except AttributeError:
        _problem(
            problems,
            "policy",
            "check_claude_simplify.py has no MINIMUM_VERSION constant",
        )
        return

    policy_version = m_policy.group(1)
    if policy_version != checker_version:
        _problem(
            problems,
            "policy",
            f"rules/simplify-stage.md states {policy_version} but "
            f"check_claude_simplify.py MINIMUM_VERSION is {checker_version}",
        )


def _check_ordering(root: Path, problems: list[str]) -> None:
    skill_path = root / "skills" / "subagent-driven-development" / "SKILL.md"
    if not skill_path.is_file():
        _problem(problems, "ordering", f"{skill_path} not found")
        return

    text = skill_path.read_text(encoding="utf-8")
    simplify_idx = text.find("references/simplify-stage.md")
    chain_idx = text.find("references/review-chain.md")
    if simplify_idx == -1 or chain_idx == -1:
        _problem(
            problems,
            "ordering",
            "SKILL.md is missing a reference to references/simplify-stage.md "
            "or references/review-chain.md",
        )
        return

    if not simplify_idx < chain_idx:
        _problem(
            problems,
            "ordering",
            "SKILL.md does not place references/simplify-stage.md before "
            "references/review-chain.md",
        )


def _check_receipt_flag(root: Path, problems: list[str]) -> None:
    path = root / "scripts" / "check_review_receipt.py"
    if not path.is_file():
        _problem(problems, "receipt", f"{path} not found")
        return
    if '"--require-simplify-if"' not in path.read_text(encoding="utf-8"):
        _problem(problems, "receipt", f"{path} no longer defines --require-simplify-if")


def _check_finish_gate(root: Path, problems: list[str]) -> None:
    path = root / "skills" / "finishing-a-development-branch" / "SKILL.md"
    if not path.is_file():
        _problem(problems, "finish-gate", f"{path} not found")
        return
    if "--require-simplify-if" not in path.read_text(encoding="utf-8"):
        _problem(
            problems,
            "finish-gate",
            f"{path} no longer requires --require-simplify-if before push",
        )


def _check_hook_threshold(
    root: Path, problems: list[str], checker: ModuleType | None = None
) -> None:
    hook_path = root / "hooks" / "risk-corroboration.sh"
    if checker is None:
        checker = _load_check_claude_simplify(root)
    if not hook_path.is_file() or checker is None:
        _problem(
            problems, "hook", f"missing {hook_path} or scripts/check_claude_simplify.py"
        )
        return

    m_hook = _HOOK_TINY_THRESHOLD_RE.search(hook_path.read_text(encoding="utf-8"))
    if not m_hook:
        _problem(problems, "hook", f"{hook_path} has no tiny-lane SIZE_THRESHOLD")
        return

    try:
        checker_threshold = checker.TINY_SOURCE_LINE_THRESHOLD
    except AttributeError:
        _problem(
            problems,
            "hook",
            "check_claude_simplify.py has no TINY_SOURCE_LINE_THRESHOLD constant",
        )
        return

    if int(m_hook.group(1)) != checker_threshold:
        _problem(
            problems,
            "hook",
            f"hooks/risk-corroboration.sh tiny SIZE_THRESHOLD={m_hook.group(1)} but "
            f"check_claude_simplify.py TINY_SOURCE_LINE_THRESHOLD={checker_threshold}",
        )


def _check_documentation(root: Path, problems: list[str]) -> None:
    paths = [root / p for p in _DOC_STATIC_FILES]
    rules_dir = root / "rules"
    if rules_dir.is_dir():
        paths.extend(sorted(rules_dir.glob("*.md")))

    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in _STALE_DOC_PATTERNS:
            if pattern.search(text):
                try:
                    rel = path.relative_to(root)
                except ValueError:
                    rel = path
                _problem(
                    problems,
                    "documentation",
                    f"{rel} contains a stale claim matching {pattern.pattern!r}",
                )


def _deployed_targets(root: Path) -> list[str]:
    manifest_path = root / "harness-manifest.json"
    if not manifest_path.is_file():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    contract = manifest.get("contracts", {}).get("simplify-stage-contract")
    if not isinstance(contract, dict):
        return []

    paths = list(contract.get("surface", [])) + list(contract.get("consumers", []))
    return sorted(
        {p for p in paths if isinstance(p, str) and p.startswith(_DEPLOY_PREFIXES)}
    )


def _check_deployed_parity(root: Path, problems: list[str]) -> None:
    claude_dir = root / ".claude"
    if not claude_dir.is_dir():
        print(
            f"{PREFIX}: deployed-parity: no .claude/ mirror present — skipping "
            "(pre-deploy state; run scripts/deploy-harness.sh to populate it)",
            file=sys.stderr,
        )
        return

    for rel in _deployed_targets(root):
        src = root / rel
        if not src.is_file():
            # Missing on source is not this check's concern (covered elsewhere).
            continue
        dst = claude_dir / rel
        if not dst.is_file():
            _problem(
                problems, "deployed-parity", f"{rel} not deployed to .claude/{rel}"
            )
            continue
        if src.read_text(encoding="utf-8") != dst.read_text(encoding="utf-8"):
            _problem(
                problems, "deployed-parity", f".claude/{rel} is stale relative to {rel}"
            )


def check(root: Path) -> int:
    problems: list[str] = []  # local, not module-global — safe to call repeatedly

    # Load the policy module once; both consumers get the same instance.
    checker = _load_check_claude_simplify(root)
    _check_version_floor(root, problems, checker)
    _check_ordering(root, problems)
    _check_receipt_flag(root, problems)
    _check_finish_gate(root, problems)
    _check_hook_threshold(root, problems, checker)
    _check_documentation(root, problems)
    _check_deployed_parity(root, problems)

    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        print(f"\n{len(problems)} simplify-adoption drift problem(s).", file=sys.stderr)
        return 1

    print(
        "simplify-adoption: consistent — policy, ordering, receipt, hook, docs, and "
        "deployed harness (if present) all agree"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--root", default=None, help="repo root (default: script's parent dir)"
    )
    args = ap.parse_args(argv)
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    return check(root)


if __name__ == "__main__":
    sys.exit(main())
