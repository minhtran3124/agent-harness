#!/usr/bin/env bash
# v5 keeps exactly one rule, plugins/harness/rules/behavior.md. A plugin has no rules component,
# so a SessionStart hook (hooks/session-rules.sh) delivers it as additionalContext. This test
# pins the inventory, and checks the delivery: valid JSON envelope, exact file content, fail-open.
source "$(dirname "$0")/../lib.sh"

RULES="$ROOT/plugins/harness/rules"
HOOK="$ROOT/plugins/harness/hooks/session-rules.sh"

has_paths_frontmatter() {
  awk '
    NR == 1 && $0 == "---" { frontmatter = 1; next }
    frontmatter && $0 == "---" { exit }
    frontmatter && /^paths:/ { found = 1 }
    END { exit !found }
  ' "$1"
}

all=""
contextual=""
for rule in "$RULES"/*.md; do
  name=${rule##*/}
  all="$all $name"
  if has_paths_frontmatter "$rule"; then contextual="$contextual $name"; fi
done

t "rules/ holds exactly one file, behavior.md"
if [ "$all" = " behavior.md" ] && [ -z "$(ls "$RULES" | grep -v '^behavior\.md$')" ]; then pass
else fail "unexpected rules/ inventory:$all (ls: $(ls "$RULES" | tr '\n' ' '))"; fi

t "no rule is path-scoped"
if [ -z "$contextual" ]; then pass
else fail "unexpected contextual inventory:$contextual"; fi

t "hooks.json registers session-rules.sh on SessionStart"
if jq -e '[.hooks.SessionStart[]?.hooks[]? | .args[]? | select(endswith("hooks/session-rules.sh"))] | length == 1' "$ROOT/plugins/harness/hooks/hooks.json" >/dev/null; then pass
else fail "SessionStart does not run session-rules.sh exactly once"; fi

t "session-rules.sh prints a SessionStart envelope whose additionalContext equals behavior.md"
if ! command -v python3 >/dev/null 2>&1; then skip "python3 is needed to compare the JSON text"
else
  OUT=$(CLAUDE_PLUGIN_ROOT="$ROOT/plugins/harness" bash "$HOOK" 2>&1); RC=$?
  if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | python3 -c '
import json, sys
d = json.load(sys.stdin)["hookSpecificOutput"]
assert d["hookEventName"] == "SessionStart"
assert d["additionalContext"] == open(sys.argv[1], encoding="utf-8").read()
' "$RULES/behavior.md"; then pass
  else fail "rc=$RC out: $(printf '%s' "$OUT" | head -c 200)"; fi
fi

t "session-rules.sh escapes quotes, backslashes and tabs"
d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); mkdir -p "$d/rules"
printf 'say "hi" \\ back\ttab\nline two\n' > "$d/rules/behavior.md"
if ! command -v python3 >/dev/null 2>&1; then skip "python3 is needed to parse the JSON"
else
  OUT=$(CLAUDE_PLUGIN_ROOT="$d" bash "$HOOK" 2>&1)
  if printf '%s' "$OUT" | python3 -c '
import json, sys
c = json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"]
assert c == "say \"hi\" \\ back\ttab\nline two\n", repr(c)
'; then pass; else fail "escaped output did not round-trip: $OUT"; fi
fi

t "session-rules.sh prints nothing and exits 0 when the rule file is missing (fail open)"
d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
OUT=$(CLAUDE_PLUGIN_ROOT="$d" bash "$HOOK" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && [ -z "$OUT" ]; then pass; else fail "rc=$RC out: $OUT"; fi

t "session-rules.sh is mode 100755 in the index"
mode=$(git -C "$ROOT" ls-files -s -- plugins/harness/hooks/session-rules.sh | awk '{print $1}')
if [ "$mode" = "100755" ]; then pass; else fail "tracked mode '$mode'"; fi

t "docs/hooks.md documents the one-rule inventory and the SessionStart delivery"
if grep -q "one always-on file" "$ROOT/docs/hooks.md" \
   && grep -q "no path-scoped ones" "$ROOT/docs/hooks.md" \
   && grep -q "session-rules.sh" "$ROOT/docs/hooks.md"; then pass
else fail "docs/hooks.md does not document one always-on file, no path-scoped ones, and session-rules.sh"; fi

finish
