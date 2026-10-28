#!/usr/bin/env bash
# Prints wired hooks, skill count, and the advisory drift audit.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETTINGS="$REPO_ROOT/.claude/settings.json"
SKILLS_DIR="$REPO_ROOT/skills"

# ── Wired Hooks ────────────────────────────────────────────────────────────────
echo "=== Wired Hooks ==="
if [[ ! -f "$SETTINGS" ]]; then
    echo "  [not found: $SETTINGS]"
else
    # Advisory: must never abort the report. open() runs before any in-heredoc try, so no
    # per-exception guard can catch an absent, unreadable, or non-UTF-8 settings file.
    python3 - "$SETTINGS" <<'PY' 2>/dev/null || echo "  [unreadable: $SETTINGS]"
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
for trigger, entries in d.get("hooks", {}).items():
    for entry in entries:
        matcher = entry.get("matcher", "*")
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "").replace("$CLAUDE_PROJECT_DIR/.claude/hooks/", "")
            print(f"  {trigger:<20} [{matcher:<16}]  {cmd}")
PY
fi

# ── Skill Count ────────────────────────────────────────────────────────────────
echo ""
echo "=== Skills ==="
if [[ ! -d "$SKILLS_DIR" ]]; then
    echo "  [not found: $SKILLS_DIR]"
else
    # `grep -c` exits 1 on zero matches — bound it, or an empty skills/ aborts the report.
    skill_dirs=$(find "$SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d ! -name '_archive' | sort)
    skill_count=$(echo "$skill_dirs" | grep -c . || true)
    echo "  Installed: $skill_count"
    if [[ -n "$skill_dirs" ]]; then
        echo "$skill_dirs" | while read -r d; do printf "    - %s\n" "$(basename "$d")"; done
    fi
fi

# ── Drift Audit (advisory) ──────────────────────────────────────────────────────
echo ""
if [[ -x "$REPO_ROOT/scripts/harness-audit.sh" ]]; then
    bash "$REPO_ROOT/scripts/harness-audit.sh" || true
fi
