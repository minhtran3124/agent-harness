#!/usr/bin/env bash
# SessionStart hook: load knowledge base (INDEX + critical-patterns) into session context,
# AND report bounded active-run summaries from runtime/run_state.py (Phase C, GitHub issue
# #129). Emits hookSpecificOutput.additionalContext when either source has content; silent
# exit 0 when both are empty/missing. NEVER blocks: every branch exits 0 — follows the
# defensive pattern of state-breadcrumb.sh.
# JSON shape follows scope-gate.sh's additionalContext convention, encoded here via python3
# (no jq dependency).
#
# Overridable for tests:
#   SESSION_KNOWLEDGE_DIR=/path/to/fixture/docs/solutions  bash hooks/session-knowledge.sh
#   RUN_STATE_REPO_ROOT=/path/to/fixture/repo              bash hooks/session-knowledge.sh

set +e
set +u
set +o pipefail
exec 2>/dev/null

# Resolve the repo root the same way every sibling hook does (git worktree root), so it
# works from both hooks/ (source) and .claude/hooks/ (deployed).
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$HOOK_DIR" rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_ROOT" ] && REPO_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
KB_DIR="${SESSION_KNOWLEDGE_DIR:-$REPO_ROOT/docs/solutions}"
RUN_STATE_ROOT="${RUN_STATE_REPO_ROOT:-$REPO_ROOT}"

INDEX="$KB_DIR/INDEX.md"
CRITICAL="$KB_DIR/critical-patterns.md"

# --- Guard: python3 required to encode JSON output for either source ---
if ! command -v python3 >/dev/null 2>&1; then
    exit 0
fi

# ============================================================
# Source 1: knowledge base (docs/solutions/) — same logic as before, just no longer exits
# early so Source 2 below still gets evaluated.
# ============================================================
_kb_section=""
if [ -f "$INDEX" ]; then
    _index_content=$(cat "$INDEX" 2>/dev/null)
    _kb_has_data=1

    # Format 2: "0 total entries" in a header/comment line
    if printf '%s\n' "$_index_content" | grep -qE '0 total entries' 2>/dev/null; then
        _kb_has_data=0
    fi

    if [ "$_kb_has_data" = "1" ]; then
        _data_rows=$(printf '%s\n' "$_index_content" \
            | grep -E '^[|]' \
            | grep -v '^[|][-| ]*$' \
            | grep -iv '^[|][[:space:]]*File[[:space:]]*[|]')
        if [ -z "$_data_rows" ]; then
            _kb_has_data=0
        else
            _non_placeholder=$(printf '%s\n' "$_data_rows" | grep -v '_(' 2>/dev/null)
            [ -z "$_non_placeholder" ] && _kb_has_data=0
        fi
    fi

    if [ "$_kb_has_data" = "1" ]; then
        _index_section=$(head -n 30 "$INDEX" 2>/dev/null)
        _critical_section=""
        if [ -f "$CRITICAL" ]; then
            _line_count=$(wc -l < "$CRITICAL" 2>/dev/null | tr -d ' ')
            if [ "${_line_count:-0}" -le 40 ]; then
                _critical_section=$(cat "$CRITICAL" 2>/dev/null)
            else
                _critical_section=$(grep -E '^#' "$CRITICAL" 2>/dev/null)
            fi
        fi
        _kb_section=$(printf '%s\n\n---\n\n%s\n\n%s' \
            "$_index_section" \
            "$_critical_section" \
            "[session-knowledge] docs/solutions/ — read full file when relevant")
    fi
fi

# ============================================================
# Source 2: active runs (runtime/run_state.py list --active --json), bounded to 5.
# Absent/broken run_state.py is not an error — just no contribution from this source.
# ============================================================
_runs_section=""
_RS="$RUN_STATE_ROOT/runtime/run_state.py"
if [ -f "$_RS" ] && command -v python3 >/dev/null 2>&1; then
    _runs_json=$(cd "$RUN_STATE_ROOT" && python3 "$_RS" list --active --json 2>/dev/null)
    if [ -n "$_runs_json" ]; then
        _runs_section=$(printf '%s' "$_runs_json" | python3 -c '
import json, sys
try:
    runs = json.load(sys.stdin)
except Exception:
    runs = []
if runs:
    lines = ["[active runs] (showing up to 5 of %d)" % len(runs)]
    for r in runs[:5]:
        lines.append("  %s: %s (waiting_on=%s)" % (r.get("slug"), r.get("state"), r.get("waiting_on")))
    print("\n".join(lines))
' 2>/dev/null)
    fi
fi

# ============================================================
# Combine — emit only if at least one source has content.
# ============================================================
if [ -z "$_kb_section" ] && [ -z "$_runs_section" ]; then
    exit 0
fi

if [ -n "$_kb_section" ] && [ -n "$_runs_section" ]; then
    _context=$(printf '%s\n\n---\n\n%s' "$_kb_section" "$_runs_section")
elif [ -n "$_kb_section" ]; then
    _context="$_kb_section"
else
    _context="$_runs_section"
fi

_json_str=$(printf '%s' "$_context" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null)
if [ -z "$_json_str" ]; then
    exit 0
fi

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' "$_json_str"
exit 0
