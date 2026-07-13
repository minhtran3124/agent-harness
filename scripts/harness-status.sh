#!/usr/bin/env bash
# Prints wired hooks, skill count, and the last 5 trust-metrics rows.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETTINGS="$REPO_ROOT/.claude/settings.json"
SKILLS_DIR="$REPO_ROOT/skills"
TRUST_METRICS="$REPO_ROOT/docs/harness-experimental/trust-metrics.md"
AUDIT_TREND_LOG="$REPO_ROOT/docs/harness-experimental/audit-log.jsonl"

# ── Wired Hooks ────────────────────────────────────────────────────────────────
echo "=== Wired Hooks ==="
python3 - "$SETTINGS" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    d = json.load(f)
for trigger, entries in d.get("hooks", {}).items():
    for entry in entries:
        matcher = entry.get("matcher", "*")
        for hook in entry.get("hooks", []):
            cmd = hook["command"].replace("$CLAUDE_PROJECT_DIR/.claude/hooks/", "")
            print(f"  {trigger:<20} [{matcher:<16}]  {cmd}")
PY

# ── Skill Count ────────────────────────────────────────────────────────────────
echo ""
echo "=== Skills ==="
skill_dirs=$(find "$SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d ! -name '_archive' | sort)
skill_count=$(echo "$skill_dirs" | grep -c .)
echo "  Installed: $skill_count"
echo "$skill_dirs" | while read -r d; do printf "    - %s\n" "$(basename "$d")"; done

# ── Last 5 Trust-Metrics Rows ──────────────────────────────────────────────────
echo ""
echo "=== Last 5 Trust-Metrics Rows ==="
if [[ ! -f "$TRUST_METRICS" ]]; then
    echo "  [not found: $TRUST_METRICS]"
else
    # Extract data rows: lines whose first column looks like a date (YYYY-MM-DD)
    rows=$(grep "^| [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}" "$TRUST_METRICS")
    if [[ -z "$rows" ]]; then
        echo "  [no data rows found]"
    else
        echo "$rows" | tail -5 | while IFS= read -r row; do
            # Pull Date and Slug (columns 1 and 2)
            date_col=$(echo "$row" | awk -F'|' '{gsub(/ /,"",$2); print $2}')
            slug_col=$(echo "$row" | awk -F'|' '{gsub(/^ +| +$/,"",$3); print $3}')
            lane_col=$(echo "$row" | awk -F'|' '{gsub(/^ +| +$/,"",$5); print $5}')
            conf_col=$(echo "$row" | awk -F'|' '{gsub(/^ +| +$/,"",$7); print $7}')
            hook_col=$(echo "$row" | awk -F'|' '{gsub(/^ +| +$/,"",$9); print $9}')
            printf "  %-12s  %-35s  lane=%-10s  conf=%-6s  hook=%s\n" \
                "$date_col" "$slug_col" "$lane_col" "$conf_col" "$hook_col"
        done
    fi
fi

# ── Audit Trend (last 5 runs) ───────────────────────────────────────────────────
echo ""
echo "=== Audit Trend (last 5 runs) ==="
if [[ ! -f "$AUDIT_TREND_LOG" ]]; then
    echo "  [not found: $AUDIT_TREND_LOG]"
else
    # Advisory: must never abort the report. The `|| echo` closes the failure class at the
    # mechanism level — open() runs before any in-heredoc try, so no per-exception guard can
    # catch an unreadable or non-UTF-8 log.
    python3 - "$AUDIT_TREND_LOG" <<'PY' || echo "  [unreadable: $AUDIT_TREND_LOG]"
import json, sys
with open(sys.argv[1]) as f:
    lines = [l.strip() for l in f if l.strip()]
if not lines:
    print("  [no data rows found]")
for line in lines[-5:]:
    try:
        d = json.loads(line)
        print(f"  {d['date']}    findings={d['findings']}   band={d['band']}")
    except (json.JSONDecodeError, KeyError, TypeError):
        continue
PY
fi

# ── Drift Audit (advisory) ──────────────────────────────────────────────────────
echo ""
if [[ -x "$REPO_ROOT/scripts/harness-audit.sh" ]]; then
    bash "$REPO_ROOT/scripts/harness-audit.sh" || true
fi
