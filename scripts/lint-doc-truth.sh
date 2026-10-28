#!/bin/bash
# Doc-truth lint: the core docs must not reference paths that do not exist, and the
# CLAUDE.md hook table must agree with plugins/harness/hooks/hooks.json. Mechanizes the
# manual docs-vs-code audit (PR #9 and PR #10 were both drift-repair PRs — this makes
# the third drift a CI failure instead of a human re-audit).
#
# What is checked
#   1. Markdown link targets `](path)` in the core docs — always checked unless a URL.
#   2. Backticked tokens containing `/` whose first segment is a known repo root —
#      prose mentions of paths. Unknown roots (example paths, upstream repo slugs) are
#      out of scope. Placeholders (<>, *, [], {}, $) and specs/ (gitignored by design)
#      are skipped. `.claude/...` is a consumer's own folder and is stripped.
#      A path not found at the root is also tried under plugins/harness/, as skills/<path>
#      and as skills/*/<path>
#      (per-skill docs reference their own files relative to the skill dir).
#   3. CLAUDE.md hook table: every `hook.sh` row exists in plugins/harness/hooks/; ✅ rows
#      are registered in hooks/hooks.json, ⬜ rows are not; every hooks/*.sh appears in the
#      table; every script hooks.json registers exists; the repo's settings.json wires no hooks.
#   4. Plugin docs: each backticked path in plugins/harness/**/*.md resolves inside the plugin.
#
# Known limitations: bare tokens without a slash (e.g. `.mcp.json`) are only caught
# when written as markdown links; code-block contents are scanned like prose.
set -u
cd "$(dirname "$0")/.." || exit 1

# Scope: the docs an agent actually loads. The plugin's rules/*.md and agents/*.md reach every
# execution subagent, so a dangling path there misleads exactly as much as one in CLAUDE.md. The
# repo's own agents/*.md (README, PROJECT.md) are linted too.
# nullglob so an empty folder yields no entries instead of a literal glob that would then be
# reported as a missing doc.
PLUGIN=plugins/harness
shopt -s nullglob
DOCS=(CLAUDE.md docs/hooks.md README.md HARNESS.md $PLUGIN/skills/README.md agents/*.md $PLUGIN/agents/*.md $PLUGIN/rules/*.md)
shopt -u nullglob
KNOWN_ROOTS="plugins skills rules hooks docs templates agents scripts tests xia2 .github .claude"
FAILED=0
err() { printf '  ✗ %s\n' "$1"; FAILED=1; }

check_path() { # check_path <doc> <raw-path>
  local doc="$1" p="$2"
  p="${p#./}"
  case "$p" in
    ''|http://*|https://*|mailto:*|'~'*) return ;;
    *'<'*|*'>'*|*'*'*|*'{'*|*'['*|*'$'*|*'…'*) return ;;   # placeholders / globs / vars
    specs/*) return ;;                                      # local-only by design
    .claude/*) p="${p#.claude/}" ;;                         # a consumer's own .claude/ folder
  esac
  [ -e "$p" ] && return
  # Docs inside the plugin cite plugin paths relative to the plugin root or a skill dir.
  [ -e "$PLUGIN/$p" ] && return
  [ -e "$PLUGIN/skills/$p" ] && return
  compgen -G "$PLUGIN/skills/*/$p" >/dev/null 2>&1 && return
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

# ---- 3: CLAUDE.md hook table vs the plugin's hooks/ vs hooks/hooks.json ----
HOOKS_JSON=$PLUGIN/hooks/hooks.json
REGISTERED=""
if [ -f "$HOOKS_JSON" ]; then
  # Script names the plugin registers: every ".sh" word in a hook command or its args.
  REGISTERED=$(jq -r '.hooks[]?[]?.hooks[]? | (.command // empty), (.args[]? // empty)' "$HOOKS_JSON" 2>/dev/null \
    | grep -oE '[A-Za-z0-9_./${}-]+\.sh' | sed -E 's#.*/##' | sort -u)
else
  err "$HOOKS_JSON is missing"
fi
TABLE_HOOKS=$(grep -oE '^\| `[a-z0-9_-]+\.sh`' CLAUDE.md | tr -d '|` ')
for h in $TABLE_HOOKS; do
  [ -f "$PLUGIN/hooks/$h" ] || err "CLAUDE.md hook table references missing $PLUGIN/hooks/$h"
  row=$(grep -E "^\| \`$h\`" CLAUDE.md)
  if echo "$row" | grep -q '✅'; then
    echo "$REGISTERED" | grep -qx "$h" || err "hook table says '$h' is wired but it is not in $HOOKS_JSON"
  else
    echo "$REGISTERED" | grep -qx "$h" && err "hook table says '$h' is dormant but $HOOKS_JSON registers it"
  fi
done
for f in $PLUGIN/hooks/*.sh; do
  [ -f "$f" ] || continue
  h=$(basename "$f")
  echo "$TABLE_HOOKS" | grep -qx "$h" || err "$PLUGIN/hooks/$h exists but is missing from the CLAUDE.md hook table"
done
for h in $REGISTERED; do
  [ -f "$PLUGIN/hooks/$h" ] || err "$HOOKS_JSON registers a script that does not exist: $h"
done
# A hook wired in both the plugin and the repo's settings.json would run twice.
if [ -f settings.json ] && jq -e '(.hooks // {}) | length > 0' settings.json >/dev/null 2>&1; then
  err "settings.json wires hooks; the plugin's hooks.json already does, so each would run twice"
fi

# ---- 4: plugin-side truth — lint the plugin tree, which is what a consumer receives ----
# Checks 1-2 resolve a path against the whole repo, so a plugin doc naming a file that exists
# only in the repo (scripts/run-tests.sh, docs/...) would pass while it is dangling in every
# consuming repo. Here each plugin doc is checked against the plugin tree alone.
# `${CLAUDE_PLUGIN_ROOT}/x` resolves from the plugin root and `${CLAUDE_SKILL_DIR}/x` from the
# skill's own folder. A doc MAY cite a repo-only path if the citation says "harness repo" or
# "harness checkout" within a line of it.
if [ "${SKIP_PLUGIN_LINT:-0}" != "1" ] && [ -d "$PLUGIN" ] && command -v python3 >/dev/null 2>&1; then
  plugin_out=$(python3 - "$PLUGIN" <<'PYEOF'
import os, re, sys
plug = sys.argv[1]
ROOTS = ("skills/", "rules/", "hooks/", "agents/", "templates/", "workflows/", "scripts/")
# Paths a consumer legitimately does not have: illustrative examples, run-time artifacts, and the
# consumer's own files (agents/PROJECT.md is created by the setup skill).
SKIP = {"foo.py", "plan.md", "kb-embedding/voyage.md", "techstacks/conventions.md", "agents/PROJECT.md"}
BT = chr(96)   # literal backtick, built at runtime
SPAN = re.compile(BT + "([^" + BT + "]+)" + BT)
PATH = re.compile(r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_.][A-Za-z0-9_./-]*\.(?:md|py|sh|json|ini|yml))")
bad = []
for dp, _, fs in os.walk(plug):
    for fn in fs:
        if not fn.endswith(".md") or "tests" in dp.split(os.sep):
            continue   # skills/*/tests/ hold dev fixtures, not instructions
        full = os.path.join(dp, fn)
        rel = os.path.relpath(full, plug)
        parts = rel.split(os.sep)
        skill_rel = "/".join(parts[:2]) if parts[0] == "skills" and len(parts) > 2 else None
        lines = open(full, encoding="utf-8", errors="ignore").read().split("\n")
        for i, line in enumerate(lines, 1):
            window = " ".join(lines[max(0, i - 2):i + 1])
            if "harness repo" in window or "harness checkout" in window:
                continue
            for span in SPAN.findall(line):
                span = span.replace("${CLAUDE_PLUGIN_ROOT}/", "")
                if "${CLAUDE_SKILL_DIR}/" in span:
                    if skill_rel is None:
                        continue
                    span = span.replace("${CLAUDE_SKILL_DIR}/", skill_rel + "/")
                for m in PATH.finditer(span):
                    path = m.group(1)
                    if not path.startswith(ROOTS) or "<" in path or path in SKIP:
                        continue
                    if not os.path.exists(os.path.join(plug, path)):
                        bad.append(f"{rel}:{i} -> {path}")
for b in sorted(set(bad)):
    print(b)
PYEOF
  )
  if [ -n "$plugin_out" ]; then
    while IFS= read -r line; do
      err "plugin tree: $line does not exist in the plugin (a consuming repo would not have it; say 'harness repo' nearby if it is repo-only)"
    done <<< "$plugin_out"
  fi
fi

if [ "$FAILED" -eq 0 ]; then
  echo "  ✓ doc-truth lint: doc paths exist; plugin docs resolve inside the plugin; hook table matches hooks.json"
  exit 0
fi
exit 1
