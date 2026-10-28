#!/usr/bin/env bash
# v5 keeps exactly one rule, rules/behavior.md. It has no `paths:` frontmatter, so Claude Code
# auto-loads it every session from .claude/rules/. This test pins that inventory exactly.
source "$(dirname "$0")/../lib.sh"

has_paths_frontmatter() {
  awk '
    NR == 1 && $0 == "---" { frontmatter = 1; next }
    frontmatter && $0 == "---" { exit }
    frontmatter && /^paths:/ { found = 1 }
    END { exit !found }
  ' "$1"
}

all=""
always=""
contextual=""
for rule in "$ROOT"/rules/*.md; do
  name=${rule##*/}
  all="$all $name"
  if has_paths_frontmatter "$rule"; then
    contextual="$contextual $name"
  else
    always="$always $name"
  fi
done

t "rules/ holds exactly one file, behavior.md"
if [ "$all" = " behavior.md" ] && [ -z "$(ls "$ROOT/rules" | grep -v '^behavior\.md$')" ]; then pass
else fail "unexpected rules/ inventory:$all (ls: $(ls "$ROOT/rules" | tr '\n' ' '))"; fi

t "behavior.md is the only always-on rule"
if [ "$always" = " behavior.md" ]; then pass
else fail "unexpected always-on inventory:$always"; fi

t "no rule is path-scoped"
if [ -z "$contextual" ]; then pass
else fail "unexpected contextual inventory:$contextual"; fi

t "docs/hooks.md documents the one-rule inventory"
if grep -q "one always-on file" "$ROOT/docs/hooks.md" \
   && grep -q "no path-scoped ones" "$ROOT/docs/hooks.md"; then pass
else fail "docs/hooks.md does not document one always-on file and no path-scoped ones"; fi

finish
