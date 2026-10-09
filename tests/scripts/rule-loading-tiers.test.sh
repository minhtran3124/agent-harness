#!/usr/bin/env bash
source "$(dirname "$0")/../lib.sh"

has_paths_frontmatter() {
  awk '
    NR == 1 && $0 == "---" { frontmatter = 1; next }
    frontmatter && $0 == "---" { exit }
    frontmatter && /^paths:/ { found = 1 }
    END { exit !found }
  ' "$1"
}

always=""
contextual=""
for rule in "$ROOT"/rules/*.md; do
  name=${rule##*/}
  if has_paths_frontmatter "$rule"; then
    contextual="$contextual $name"
  else
    always="$always $name"
  fi
done

t "source rules resolve to the documented five always-on files"
if [ "$always" = " architecture.md behavior.md guidelines.md orchestration.md research-depth.md" ]; then pass
else fail "unexpected always-on inventory:$always"; fi

t "source rules resolve to four contextual files, including terminology.md"
if [ "$contextual" = " auto-correct-scope.md plan-format.md terminology.md wave-parallelism.md" ]; then pass
else fail "unexpected contextual inventory:$contextual"; fi

t "CLAUDE.md documents the source-derived tier counts"
if grep -q 'five always-on files' "$ROOT/CLAUDE.md" && grep -q 'four path-scoped ones' "$ROOT/CLAUDE.md"; then pass
else fail "CLAUDE.md does not document the current 5/4 rule-loading tiers"; fi

t "Codex AGENTS.md block inlines exactly the always-on rule tier"
codex_out=$(mktemp -d); _CLEANUP_DIRS+=("$codex_out")
expected="$always"
if python3 "$ROOT/scripts/render_codex_adapter.py" --root "$ROOT" --output "$codex_out" >/dev/null; then
  rendered=""
  while IFS= read -r line; do
    rendered="$rendered ${line##*/}"
  done <<EOF
$(grep '^Source: \.codex/\.agent-harness/payload/rules/' "$codex_out/agents-block.md")
EOF
  missing=""; extra=""
  for name in $expected; do
    case "$rendered " in *" $name "*) ;; *) missing="$missing $name" ;; esac
  done
  for name in $rendered; do
    case "$expected " in *" $name "*) ;; *) extra="$extra $name" ;; esac
  done
  if [ -n "$rendered" ] && [ -z "$missing" ] && [ -z "$extra" ]; then pass
  else fail "Codex block rule inventory drifted; missing:${missing:- none} extra:${extra:- none}"; fi
else
  fail "render_codex_adapter.py failed"
fi

finish
