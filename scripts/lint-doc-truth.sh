#!/bin/bash
# Doc-truth lint: the core docs must not reference paths that do not exist, and the
# CLAUDE.md hook table must agree with settings.json registration. Mechanizes the
# manual docs-vs-code audit (PR #9 and PR #10 were both drift-repair PRs — this makes
# the third drift a CI failure instead of a human re-audit).
#
# What is checked
#   1. Markdown link targets `](path)` in the core docs — always checked unless a URL.
#   2. Backticked tokens containing `/` whose first segment is a known repo root —
#      prose mentions of paths. Unknown roots (example paths, upstream repo slugs) are
#      out of scope. Placeholders (<>, *, [], {}, $) and specs/ (gitignored by design)
#      are skipped. `.claude/...` maps to the root source it is derived from.
#      A path not found at the root is also tried as skills/<path> and skills/*/<path>
#      (per-skill docs reference their own files relative to the skill dir).
#   3. CLAUDE.md hook table: every `hook.sh` row exists in hooks/; ✅ rows are
#      registered in settings.json, ⬜ rows are not; every hooks/*.sh appears in the
#      table; every command in settings.json exists on disk.
#
# Known limitations: bare tokens without a slash (e.g. `.mcp.json`) are only caught
# when written as markdown links; code-block contents are scanned like prose.
set -u
cd "$(dirname "$0")/.." || exit 1

DOCS=(CLAUDE.md README.md HARNESS.md skills/README.md)
KNOWN_ROOTS="skills rules hooks docs templates agents scripts tests agent-memory xia2 .github .claude"
FAILED=0
err() { printf '  ✗ %s\n' "$1"; FAILED=1; }

check_path() { # check_path <doc> <raw-path>
  local doc="$1" p="$2"
  p="${p#./}"
  case "$p" in
    ''|http://*|https://*|mailto:*|'~'*) return ;;
    *'<'*|*'>'*|*'*'*|*'{'*|*'['*|*'$'*|*'…'*) return ;;   # placeholders / globs / vars
    specs/*) return ;;                                      # local-only by design
    .claude/*) p="${p#.claude/}" ;;                         # derived from the root source
  esac
  [ -e "$p" ] && return
  [ -e "skills/$p" ] && return
  compgen -G "skills/*/$p" >/dev/null 2>&1 && return
  err "$doc references missing path: $p"
}

# ---- 1+2: path references in core docs ----
for doc in "${DOCS[@]}"; do
  [ -f "$doc" ] || { err "core doc missing: $doc"; continue; }

  # markdown link targets — checked regardless of shape (minus URLs/anchors)
  while IFS= read -r p; do
    case "$p" in '#'*) continue ;; esac
    check_path "$doc" "$p"
  done < <(grep -oE '\]\([^)]+\)' "$doc" | sed -E 's/^\]\(//; s/\)$//' | sort -u)

  # backticked slash-tokens — only when the first segment is a known repo root
  while IFS= read -r p; do
    local_first="${p%%/*}"
    case " $KNOWN_ROOTS " in
      *" $local_first "*) check_path "$doc" "$p" ;;
    esac
  done < <(grep -oE '`[^` ]*/[^` ]*`' "$doc" | tr -d '`' | sort -u)
done

# ---- 3: CLAUDE.md hook table vs hooks/ vs settings.json ----
TABLE_HOOKS=$(grep -oE '^\| `[a-z0-9_-]+\.sh`' CLAUDE.md | tr -d '|` ')
for h in $TABLE_HOOKS; do
  [ -f "hooks/$h" ] || err "CLAUDE.md hook table references missing hooks/$h"
  row=$(grep -E "^\| \`$h\`" CLAUDE.md)
  if echo "$row" | grep -q '✅'; then
    grep -q "hooks/$h" settings.json || err "hook table says '$h' is wired but it is not in settings.json"
  else
    grep -q "hooks/$h" settings.json && err "hook table says '$h' is dormant but settings.json registers it"
  fi
done
for f in hooks/*.sh; do
  h=$(basename "$f")
  echo "$TABLE_HOOKS" | grep -qx "$h" || err "hooks/$h exists but is missing from the CLAUDE.md hook table"
done
while IFS= read -r cmd; do
  case "$cmd" in
    '$CLAUDE_PROJECT_DIR/'*) cmd="${cmd#\$CLAUDE_PROJECT_DIR/}"; cmd="${cmd#.claude/}" ;;
  esac
  [ -f "$cmd" ] || err "settings.json registers a command that does not exist: $cmd"
done < <(jq -r '.hooks[]?[]?.hooks[]?.command // empty' settings.json)

if [ "$FAILED" -eq 0 ]; then
  echo "  ✓ doc-truth lint: all referenced paths exist; hook table matches settings.json"
  exit 0
fi
exit 1
