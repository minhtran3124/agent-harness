#!/bin/bash
# Fail on a dead relative link in tracked markdown.
#
# Checks `[text](target)` links in every git-tracked *.md file, except docs/solutions/
# (dated records may cite deleted files), CHANGELOG.md (history) and templates/ dirs (their
# links are placeholders or point into the consumer repo). A target is skipped when
# it is empty, an anchor only (#x), or has a URL scheme (http:, https:, mailto:, ...). A
# `#fragment` or `?query` is stripped before the file check; a leading `/` means repo root.
# Links inside fenced code blocks are examples, not links, and are skipped.
#
# The living top-level docs (README.md HARNESS.md AGENTS.md CLAUDE.md skills/README.md
# docs/hooks.md) also get a path check on backticked file paths such as `hooks/commit-gate.sh`:
# a path with a "/" and a known extension must exist (from the repo root or the file's dir).
# Paths under .claude/ (installed in consumer repos), placeholders (<>*${}) and `specs/` are skipped.
#
# Usage: scripts/check-md-links.sh [repo-root]    (default: the git toplevel of the cwd)
# Portable: bash 3.2, BSD awk/sed.
set -u

ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$ROOT" || { echo "check-md-links: cannot cd to $ROOT" >&2; exit 2; }

dead=0
checked=0

# Print "target" for every inline link outside fenced code, one per line.
extract() {
  awk '
    /^[ \t]*(```|~~~)/ { fence = !fence; next }
    fence { next }
    {
      line = $0
      while (match(line, /\]\([^)]*\)/)) {
        t = substr(line, RSTART + 2, RLENGTH - 3)
        print t
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$1"
}

# Print backticked file paths (one per line) outside fenced code.
extract_paths() {
  awk '
    /^[ \t]*(```|~~~)/ { fence = !fence; next }
    fence { next }
    {
      line = $0
      while (match(line, /`[A-Za-z0-9_.\/-]+\/[A-Za-z0-9_.-]+\.(md|sh|json|py|yml|yaml)`/)) {
        print substr(line, RSTART + 1, RLENGTH - 2)
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$1"
}

LIVING=" README.md HARNESS.md AGENTS.md CLAUDE.md plugins/harness/skills/README.md docs/hooks.md "

while IFS= read -r file; do
  case "$file" in
    docs/solutions/*|CHANGELOG.md|templates/*|*/templates/*) continue ;;
  esac
  [ -f "$file" ] || continue
  dir=$(dirname "$file")
  n=0
  while IFS= read -r target; do
    n=$((n + 1))
    t="${target# }"
    case "$t" in "<"*">"*) t="${t#<}"; t="${t%%>*}" ;; *) t="${t%% *}" ;; esac
    t="${t%%#*}"; t="${t%%\?*}"
    [ -z "$t" ] && continue
    case "$t" in
      [A-Za-z]*:*) continue ;;   # http:, https:, mailto:, ...
    esac
    case "$t" in
      /*) path="$ROOT$t" ;;
      *)  path="$dir/$t" ;;
    esac
    checked=$((checked + 1))
    if [ ! -e "$path" ]; then
      echo "DEAD  $file: ($target)"
      dead=$((dead + 1))
    fi
  done < <(extract "$file")
  case "$LIVING" in
    *" $file "*)
      while IFS= read -r p; do
        case "$p" in .claude/*|specs/*|/*) continue ;; esac
        checked=$((checked + 1))
        if [ ! -e "$ROOT/$p" ] && [ ! -e "$dir/$p" ] && [ ! -e "$ROOT/plugins/harness/$p" ]; then
          echo "DEAD  $file: \`$p\`"
          dead=$((dead + 1))
        fi
      done < <(extract_paths "$file")
      ;;
  esac
done < <(git ls-files '*.md')

echo "check-md-links: $checked links checked, $dead dead"
[ "$dead" -eq 0 ]
