#!/usr/bin/env bash
# SessionStart hook: load knowledge base (INDEX + critical-patterns) into session context.
# Emits hookSpecificOutput.additionalContext when the store has entries; silent exit 0 otherwise.
# NEVER blocks: every branch exits 0 — follows the defensive pattern of state-breadcrumb.sh.
# JSON shape follows scope-gate.sh (jq -cn with additionalContext).
#
# Overridable for tests:
#   SESSION_KNOWLEDGE_DIR=/path/to/fixture/docs/solutions  bash hooks/session-knowledge.sh

set +e
set +u
set +o pipefail
exec 2>/dev/null

# Resolve the knowledge-base root.
# Default: docs/solutions relative to the repo root (same dir as the hook's parent).
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
KB_DIR="${SESSION_KNOWLEDGE_DIR:-$REPO_ROOT/docs/solutions}"

INDEX="$KB_DIR/INDEX.md"
CRITICAL="$KB_DIR/critical-patterns.md"

# --- Guard: jq required ---
if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

# --- Guard: INDEX must exist ---
if [ ! -f "$INDEX" ]; then
    exit 0
fi

# --- Detect empty store ---
# Format 1 (bootstrap): table contains only the placeholder row "_(empty...)_"
# Format 2 (rebuild/compound): "0 total entries" in the header line
_index_content=$(cat "$INDEX" 2>/dev/null)

# Format 2: "0 total entries" in a header/comment line
if printf '%s\n' "$_index_content" | grep -qE '0 total entries' 2>/dev/null; then
    exit 0
fi

# Format 1 (bootstrap placeholder): extract data rows from the table.
# Data rows = pipe-starting lines that are NOT the separator (|---|) or column header (| File |).
# Separator lines: consist only of |, -, and spaces.
# Header lines: start with "| File " or "| file " (case-insensitive).
_data_rows=$(printf '%s\n' "$_index_content" \
    | grep -E '^[|]' \
    | grep -v '^[|][-| ]*$' \
    | grep -iv '^[|][[:space:]]*File[[:space:]]*[|]')

if [ -z "$_data_rows" ]; then
    # No data rows at all — treat as empty
    exit 0
fi

# Check if all data rows are placeholder (contain "_(empty" or "_(")
_non_placeholder=$(printf '%s\n' "$_data_rows" | grep -v '_(' 2>/dev/null)
if [ -z "$_non_placeholder" ]; then
    exit 0
fi

# --- Store has entries: build additionalContext ---

# Take first 30 lines of INDEX
_index_section=$(head -n 30 "$INDEX" 2>/dev/null)

# Build critical-patterns section: 40 lines max; if file is longer, only headings
_critical_section=""
if [ -f "$CRITICAL" ]; then
    _line_count=$(wc -l < "$CRITICAL" 2>/dev/null | tr -d ' ')
    if [ "${_line_count:-0}" -le 40 ]; then
        _critical_section=$(cat "$CRITICAL" 2>/dev/null)
    else
        # Only heading lines (lines starting with #) when file exceeds 40 lines
        _critical_section=$(grep -E '^#' "$CRITICAL" 2>/dev/null)
    fi
fi

# Assemble full context string using python3 for safe JSON encoding
_source_line="[session-knowledge] docs/solutions/ — read full file when relevant"

_context=$(printf '%s\n\n---\n\n%s\n\n%s' \
    "$_index_section" \
    "$_critical_section" \
    "$_source_line")

# Encode as a JSON string safely via python3 (handles newlines, backticks, quotes, pipes)
_json_str=$(printf '%s' "$_context" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null)

if [ -z "$_json_str" ]; then
    exit 0
fi

# Emit the Claude Code hook JSON (same shape as scope-gate.sh)
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' "$_json_str"

exit 0
