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
if [[ ! -f "$SETTINGS" ]]; then
    echo "  [not found: $SETTINGS]"
else
    # Advisory: must never abort the report. Same boundary as Audit Trend below —
    # open() runs before any in-heredoc try, so no per-exception guard can catch an
    # absent, unreadable, or non-UTF-8 settings file.
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

# ── Last 5 Trust-Metrics Rows ──────────────────────────────────────────────────
echo ""
echo "=== Last 5 Trust-Metrics Rows ==="
if [[ ! -f "$TRUST_METRICS" ]]; then
    echo "  [not found: $TRUST_METRICS]"
else
    # Extract data rows: lines whose first column looks like a date (YYYY-MM-DD)
    # `|| true` is load-bearing: grep exits 1 on zero matches, which under `set -e` would
    # abort the report before the `-z` branch below could ever run.
    rows=$(grep "^| [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}" "$TRUST_METRICS" || true)
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
    python3 - "$AUDIT_TREND_LOG" <<'PY' 2>/dev/null || echo "  [unreadable: $AUDIT_TREND_LOG]"
import json, sys
with open(sys.argv[1]) as f:
    lines = [l.strip() for l in f if l.strip()]
rendered = 0
for line in lines[-5:]:
    try:
        d = json.loads(line)
        print(f"  {d['date']}    findings={d['findings']}   band={d['band']}")
        rendered += 1
    except (json.JSONDecodeError, KeyError, TypeError):
        continue
if not rendered:
    print("  [no data rows found]")
PY
fi

# ── Active Runs (Phase C, GitHub issue #129) ────────────────────────────────────
echo ""
echo "=== Active Runs ==="
RUN_STATE="$REPO_ROOT/runtime/run_state.py"
if [[ ! -f "$RUN_STATE" ]]; then
    echo "  [not found: $RUN_STATE]"
elif ! command -v python3 >/dev/null 2>&1; then
    echo "  [python3 not available]"
else
    _active_runs_out=$( (cd "$REPO_ROOT" && python3 "$RUN_STATE" list --active) 2>/dev/null ) || true
    if [[ -z "$_active_runs_out" ]]; then
        echo "  [no active runs]"
    else
        echo "$_active_runs_out" | sed 's/^/  /'
    fi
fi

# ── Drift Audit (advisory) ──────────────────────────────────────────────────────
echo ""
if [[ -x "$REPO_ROOT/scripts/harness-audit.sh" ]]; then
    bash "$REPO_ROOT/scripts/harness-audit.sh" || true
fi
