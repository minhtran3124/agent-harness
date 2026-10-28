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

t "source rules resolve to five contextual files, including terminology.md and review-policy.md"
if [ "$contextual" = " auto-correct-scope.md plan-format.md review-policy.md terminology.md wave-parallelism.md" ]; then pass
else fail "unexpected contextual inventory:$contextual"; fi

spell() { case "$1" in 0) echo zero;; 1) echo one;; 2) echo two;; 3) echo three;; 4) echo four;; 5) echo five;; 6) echo six;; 7) echo seven;; 8) echo eight;; 9) echo nine;; 10) echo ten;; *) echo "$1";; esac; }
n_always=$(set -- $always; echo $#)
n_contextual=$(set -- $contextual; echo $#)

t "docs/hooks.md documents the source-derived tier counts"
if grep -q "$(spell "$n_always") always-on files" "$ROOT/docs/hooks.md" \
   && grep -q "$(spell "$n_contextual") path-scoped ones" "$ROOT/docs/hooks.md"; then pass
else fail "docs/hooks.md does not document the current $n_always/$n_contextual rule-loading tiers"; fi

finish
