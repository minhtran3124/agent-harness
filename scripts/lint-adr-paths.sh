#!/bin/bash
# ADR path lint: every repo path an ADR cites must resolve in a fresh clone, or be followed by
# a '(historical)' mark on the same line. ADRs are records, so a path that was later removed stays in the text;
# the mark tells a reader (and this lint) that the dangling path is deliberate.
#
# What is checked
#   Every docs/adr/*.md except README.md and TEMPLATE.md (a glob, no list of ADR numbers).
#   Tokens inside backtick spans that contain `/`, split on whitespace, quotes, parentheses and
#   commas, and whose first segment is a known repo root. Bare prose mentions are out of scope
#   (the same rule as lint-doc-truth.sh). Placeholders (<>, *, {}, [], $, ellipsis), URLs
#   and `~` paths are skipped. A leading `./` is stripped; a `.claude/` path is tried as written first, then without `.claude/`.
#   Unlike lint-doc-truth.sh, specs/ (gitignored, absent in a fresh clone) and the removed
#   agents/PROJECT.md are NOT exempt: where cited they need '(historical)'.
#   A path is found at the repo root, under plugins/harness/, as skills/<path>, or as
#   skills/*/<path>.
#
# ADR_LINT_ROOT overrides the repo root (default: the parent of this script's folder).
set -u
cd "${ADR_LINT_ROOT:-$(dirname "$0")/..}" || exit 1

PLUGIN=plugins/harness
KNOWN_ROOTS="plugins skills rules hooks docs templates agents scripts tests specs xia2 .github .claude"
FAILED=0

resolves() { # resolves <path>
  local p="$1"
  [ -e "$p" ] && return 0
  [ -e "$PLUGIN/$p" ] && return 0
  [ -e "$PLUGIN/skills/$p" ] && return 0
  compgen -G "$PLUGIN/skills/*/$p" >/dev/null 2>&1 && return 0
  return 1
}

shopt -s nullglob
for f in docs/adr/*.md; do
  case "$(basename "$f")" in README.md|TEMPLATE.md) continue ;; esac
  n=0
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    # A '(historical)' marker excuses the paths cited before it on its line; a path cited after
    # the last marker is still checked.
    case "$line" in *'(historical)'*) line="${line##*'(historical)'}" ;; esac
    while IFS= read -r p; do
      [ -n "$p" ] || continue
      # strip trailing punctuation, an anchor, and a :line suffix
      while :; do
        case "$p" in *[.,\;:]) p="${p%?}" ;; *) break ;; esac
      done
      p="${p%%#*}"
      p="${p%%:[0-9]*}"
      p="${p#./}"
      case "$p" in
        ''|http://*|https://*|mailto:*|'~'*) continue ;;
        *'<'*|*'>'*|*'*'*|*'{'*|*'['*|*'$'*|*'…'*|*'...'*) continue ;;
        .claude/*) resolves "${p%/}" && continue; p="${p#.claude/}" ;;
      esac
      case "$p" in */*) ;; *) continue ;; esac
      case " $KNOWN_ROOTS " in *" ${p%%/*} "*) ;; *) continue ;; esac
      resolves "${p%/}" && continue
      printf '  ✗ %s:%s missing path: %s\n' "$f" "$n" "$p"
      FAILED=1
    done < <(printf '%s\n' "$line" | grep -oE "\`[^\`]+\`" | tr -s ' \t`"'"'"'(),' '\n')
  done < "$f"
done

if [ "$FAILED" -eq 0 ]; then
  echo "  ✓ adr-paths lint: every cited path exists or is marked (historical)"
  exit 0
fi
echo "  Mark a path that no longer exists with '(historical)' on its line."
exit 1
