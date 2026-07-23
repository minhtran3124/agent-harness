#!/usr/bin/env python3
"""Pin the gate-mode loosening decision (specs/simplify-gate-surface).

Exactly two detectable gates are warn-mode — `workflow-engine` and
`weakening-validation` (the measured-noise pair) — and the other seven block.
Any drift (silent re-tightening, or a new gate quietly shipped as warn) fails.
This is SC-4's re-runnable check; wired into scripts/run-tests.sh so CI runs it.

Exit 0 = modes match the decision. Exit 1 = drift (one line per problem).
Run: python3 scripts/check_gate_modes_smoke.py [--root DIR]
"""

import argparse
import json
import sys
from pathlib import Path

EXPECTED_WARN = {"workflow-engine", "weakening-validation"}


def check(root: Path) -> int:
    manifest_path = root / "harness-manifest.json"
    try:
        m = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"gate-modes: cannot read {manifest_path}: {e}", file=sys.stderr)
        return 1

    modes = {
        g["slug"]: g.get("mode", "block")
        for g in m.get("hard_gates", {}).get("detectable", [])
    }
    problems = []
    warn = {s for s, mode in modes.items() if mode == "warn"}
    for slug in EXPECTED_WARN - modes.keys():
        problems.append(
            f"gate-modes: expected warn gate '{slug}' missing from manifest"
        )
    for slug in EXPECTED_WARN & modes.keys() - warn:
        problems.append(
            f"gate-modes: '{slug}' re-tightened to block — if intended, update this check"
        )
    for slug in warn - EXPECTED_WARN:
        problems.append(
            f"gate-modes: '{slug}' is warn but not part of the recorded decision"
        )
    for slug, mode in modes.items():
        if mode not in ("block", "warn"):
            problems.append(f"gate-modes: '{slug}' has invalid mode '{mode}'")

    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        return 1
    blockers = len(modes) - len(warn)
    print(f"gate-modes: OK — {sorted(warn)} warn, {blockers} gates block")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--root", default=None, help="repo root (default: script's parent dir)"
    )
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    return check(root)


if __name__ == "__main__":
    sys.exit(main())
