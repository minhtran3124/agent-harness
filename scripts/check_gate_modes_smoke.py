#!/usr/bin/env python3
"""Pin the gate-mode loosening decision (specs/simplify-gate-surface).

Exactly two detectable gates are warn-mode — `workflow-engine` and
`weakening-validation` (the measured-noise pair) — and the other seven block.
Any drift (silent re-tightening, or a new gate quietly shipped as warn) fails.
This is SC-4's re-runnable check; wired into scripts/run-tests.sh so CI runs it.

SC-9: also asserts hooks/lib/gate-modes.default.sh (the embedded fallback used by
risk-corroboration.sh when no manifest is in the git index) is byte-consistent with
harness-manifest.json hard_gates.detectable — any drift fails.

Exit 0 = modes match the decision. Exit 1 = drift (one line per problem).
Run: python3 scripts/check_gate_modes_smoke.py [--root DIR]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

EXPECTED_WARN = {"workflow-engine", "weakening-validation"}


def load_default_modes(root: Path) -> dict:
    """Source hooks/lib/gate-modes.default.sh and parse its slug=mode map.

    Sourcing via bash is ground truth — the same value risk-corroboration.sh gets —
    rather than regex-parsing the shell file. The path is passed as $1 (not
    interpolated into the script) so a path with spaces cannot break parsing.
    """
    default_path = root / "hooks" / "lib" / "gate-modes.default.sh"
    proc = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1" && printf "%s\\n" "$GATE_MODES_DEFAULT"',
            "bash",
            str(default_path),
        ],
        capture_output=True,
        text=True,
    )
    modes = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        slug, mode = line.rsplit("=", 1)
        modes[slug] = mode
    return modes


def check(root: Path) -> int:
    manifest_path = root / "harness-manifest.json"
    try:
        m = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"gate-modes: cannot read {manifest_path}: {e}", file=sys.stderr)
        return 1

    problems = []
    modes = {}
    for g in m.get("hard_gates", {}).get("detectable", []):
        if not isinstance(g, dict) or not g.get("slug"):
            problems.append(
                f"gate-modes: malformed detectable entry (missing slug): {g!r}"
            )
            continue
        modes[g["slug"]] = g.get("mode", "block")
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

    # SC-9: the embedded fallback map must be byte-consistent with the manifest.
    default_modes = load_default_modes(root)
    for slug in modes.keys() | default_modes.keys():
        if modes.get(slug) != default_modes.get(slug):
            problems.append(
                "gate-modes: hooks/lib/gate-modes.default.sh drift for "
                f"'{slug}': manifest={modes.get(slug)!r} default={default_modes.get(slug)!r}"
            )

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
