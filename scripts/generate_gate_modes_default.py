#!/usr/bin/env python3
"""Regenerate hooks/lib/gate-modes-default.sh from harness-manifest.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    manifest = root / "harness-manifest.json"
    out = root / "hooks" / "lib" / "gate-modes-default.sh"
    m = json.loads(manifest.read_text(encoding="utf-8"))
    lines = [
        "#!/bin/bash",
        "# GENERATED from harness-manifest.json hard_gates.detectable — do not hand-edit.",
        "# Regenerate: python3 scripts/generate_gate_modes_default.py",
        "# Sourced by risk-corroboration when no index/root/.claude manifest is available.",
        "hook_lib_default_gate_modes() {",
        "  cat <<'EOF'",
    ]
    for g in m["hard_gates"]["detectable"]:
        lines.append(f"{g['slug']}={g.get('mode', 'block')}")
    lines += ["EOF", "}", ""]
    text = "\n".join(lines)
    if "--check" in sys.argv:
        if not out.is_file() or out.read_text(encoding="utf-8") != text:
            print("gate-modes-default: drift — run python3 scripts/generate_gate_modes_default.py", file=sys.stderr)
            return 1
        print("gate-modes-default: ok")
        return 0
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
