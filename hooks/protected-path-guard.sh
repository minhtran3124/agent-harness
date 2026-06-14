#!/bin/bash
# PreToolUse hook (DORMANT — not registered in settings.json): hard-block an Edit/Write
# to a high-blast-radius file unless a break-glass reason is pre-registered.
#
# Rule 4 of rules/auto-correct-scope.md names these files "STOP — needs architectural
# judgment"; today that is prompt-enforced. This hook makes the block STRUCTURAL at write
# time: a write to a protected path is DENIED unless PROTECTED_PATH_REASON is set — in
# which case the write is allowed and the reason is appended to a break-glass audit log
# (turning an override into a record). Mirrors the comparison research's R02/R03 pattern.
#
# Dormant by design: wiring this into settings.json (PreToolUse, matcher Edit|Write) is
# itself a Rule-4 change requiring human confirmation. Until registered, it never runs.
# It overlaps with the commit-time net (risk-corroboration.sh) and CI (ci-strict-gate.sh);
# its added value is catching the edit EARLIER and forcing an auditable override.
set -u

INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""')
[ -z "$FILE" ] && exit 0

# Repo-relative path (strip the project-dir prefix when the tool passed an absolute path).
REL="${FILE#"${CLAUDE_PROJECT_DIR:-$PWD}/"}"

# High-blast set: settings.json, any hook script, the plan-render engine, the test entry
# point, and the machine-read SUMMARY schema (rules/auto-correct-scope.md Rule 4 + the
# xia2/PROJECT.md High-Blast-Radius Files list).
# `^hooks/` is anchored at the repo root (paths are project-relative) so it does NOT
# match tests/hooks/ — the documented false-positive class that risk-corroboration.sh
# also excludes this way.
PROTECTED_RE='(^|/)settings\.json$|^hooks/[^/]+\.sh$|(^|/)render_plan\.py$|(^|/)run-tests\.sh$|(^|/)templates/SUMMARY\.template\.md$'

echo "$REL" | grep -qE "$PROTECTED_RE" || exit 0   # not a protected path → allow silently

REASON="${PROTECTED_PATH_REASON:-}"
if [ -n "$REASON" ]; then
  # Break-glass: allow the write, but record the override so it is an audit trail.
  LOG="${CLAUDE_PROJECT_DIR:-$PWD}/docs/harness-experimental/break-glass-log.md"
  mkdir -p "$(dirname "$LOG")" 2>/dev/null
  printf -- '- %s — `%s` — %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$REL" "$REASON" >> "$LOG" 2>/dev/null || true
  echo "[PROTECTED-PATH] break-glass override for $REL (reason recorded to break-glass-log.md)" >&2
  exit 0
fi

jq -cn --arg f "$REL" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ("High-blast-radius file (Rule 4, rules/auto-correct-scope.md): " + $f + "\nThis is a STOP — it needs architectural judgment and human confirmation.\nTo override after confirming: set PROTECTED_PATH_REASON=\"<why>\" (recorded to the break-glass log).")
  }
}'
