#!/bin/bash
# PostToolUse(Edit|Write): flag edits to files outside the active PLAN.md <files> set.
#
# Catches in-flight scope creep (a wave touching files it never declared). Default is
# WARN (non-blocking additionalContext). BLAST_RADIUS_STRICT=1 makes it exit 2 so the
# model must address the violation.
#
# No-op (silent) when: no active PLAN.md exists, the plan declares no <files>, or the
# edited file is bookkeeping (specs/, docs/, *.md). This keeps it quiet outside of
# active plan execution. Exits 0 unless STRICT + out-of-scope.

INPUT=$(cat /dev/stdin)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$FILE" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_DIR" ] && REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Canonicalize both so the repo-prefix strip is reliable (handles symlinked roots)
REPO_DIR="$(cd "$REPO_DIR" 2>/dev/null && pwd -P)"
if [ -e "$FILE" ]; then
  FILE="$(cd "$(dirname "$FILE")" 2>/dev/null && pwd -P)/$(basename "$FILE")"
fi
REL="${FILE#"$REPO_DIR"/}"

# Skip bookkeeping / non-implementation files
case "$REL" in
  specs/*|docs/*|*.md) exit 0 ;;
esac

# Find the active PLAN.md. `status: active` is the ONLY thing that arms this hook — there is
# deliberately no "else most recent" fallback. A shipped plan's <files> set is a record of what
# that work touched, not a scope constraint on everything that comes after it; falling back to it
# made every long-finished plan police every future edit, forever.
PLAN=""
for p in $(ls -t "$REPO_DIR"/specs/*/PLAN.md 2>/dev/null); do
  if grep -qiE '^status:[[:space:]]*active' "$p"; then PLAN="$p"; break; fi
done
[ -z "$PLAN" ] && exit 0   # no plan in flight → no scope to creep out of

# Declared files from <files>...</files> (comma-separated)
DECLARED=$(grep -oE '<files>[^<]*</files>' "$PLAN" 2>/dev/null \
  | sed -E 's#</?files>##g' | tr ',' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | grep -v '^$')
[ -z "$DECLARED" ] && exit 0

# In-scope? exact path, suffix path, or matching basename (lenient — advisory)
INSCOPE=0
bREL=$(basename "$REL")
while IFS= read -r d; do
  [ -z "$d" ] && continue
  [ "$REL" = "$d" ] && INSCOPE=1 && break
  case "$REL" in */"$d") INSCOPE=1; break ;; esac
  [ "$bREL" = "$(basename "$d")" ] && INSCOPE=1 && break
done <<EOF
$DECLARED
EOF
[ "$INSCOPE" -eq 1 ] && exit 0

# Out of scope
if [ "${BLAST_RADIUS_STRICT:-0}" = "1" ]; then
  echo "[BLAST RADIUS] $REL is outside the active plan's <files> set (${PLAN#"$REPO_DIR"/})." >&2
  echo "  Scope creep — escalate, or add the file to the plan." >&2
  exit 2
fi
jq -cn --arg f "$REL" --arg p "${PLAN#"$REPO_DIR"/}" '{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: ("blast-radius: edited " + $f + " which is NOT in the active plan <files> set (" + $p + "). If intentional, add it to the plan; otherwise treat as scope creep and consider escalating per rules/orchestration.md.")
  }
}'
exit 0
