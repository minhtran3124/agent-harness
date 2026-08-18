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

# Scope: the docs an agent actually loads. rules/*.md load via .claude/rules/ (always-on
# or path-scoped by `paths:` frontmatter), and agents/*.md is read by every execution subagent — so a dangling
# path there misleads exactly as much as one in CLAUDE.md. Both were unlinted until
# PR #119 found stale skills/xia2/PROJECT.md pointers surviving in agents/ precisely
# because this list did not reach them.
# nullglob so an empty rules/ or agents/ yields no entries instead of a literal glob
# that would then be reported as a missing doc.
shopt -s nullglob
DOCS=(CLAUDE.md README.md HARNESS.md skills/README.md agents/*.md rules/*.md)
shopt -u nullglob
KNOWN_ROOTS="skills rules hooks docs templates agents scripts tests xia2 .github .claude"
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

# ---- 4: consumer-side truth — lint the DERIVED tree, not just the source ----
# Checks 1-2 normalize `.claude/x` back to the root source it derives from, so they are blind to
# the failure that actually bites: a doc naming a helper that never deploys. Every `scripts/*`
# gate reference was dangling in every consuming repo for months while this lint reported exit 0,
# because it runs where scripts/ exists. A gate is only true when it runs in the environment it
# protects — so deploy into a scratch target and re-check the paths from there.
#
# Convention this enforces: a doc MAY cite a harness-repo-only path, but the citation must say so
# on the same line ("the harness repo's `scripts/check_manifest.py`"). Anything else must resolve
# in the consumer.
if [ "${SKIP_DERIVED_LINT:-0}" != "1" ] && command -v python3 >/dev/null 2>&1; then
  DERIVED_TGT=$(mktemp -d)
  trap 'rm -rf "$DERIVED_TGT"' EXIT
  if bash scripts/deploy-harness.sh --target "$DERIVED_TGT" --yes </dev/null >/dev/null 2>&1; then
    derived_out=$(python3 - "$DERIVED_TGT" <<'PYEOF'
import os, re, sys
tgt = sys.argv[1]; claude = os.path.join(tgt, ".claude")
ROOTS = ("skills/", "rules/", "hooks/", "agents/", "templates/", "runtime/", "scripts/", ".claude/")
# Paths a consumer legitimately does not have: illustrative examples, and artifacts made at run time.
SKIP = {"foo.py", "plan.md", "kb-embedding/voyage.md", "techstacks/conventions.md"}
SKIP_SUFFIX = (".plan-review.json", "break-glass-log.md", "review-receipt.json")
# Scan INSIDE each backtick span rather than only spans that are exactly a path: the highest-risk
# form is a command (python3 scripts/verify_summary.py --lane <slug>) inside a code span, which
# would miss entirely -- and an unshipped helper invoked that way is precisely the bug this checks.
BT = chr(96)   # literal backtick, built at runtime (see note above)
SPAN = re.compile(BT + "([^" + BT + "]+)" + BT)
PATH = re.compile(r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_.][A-Za-z0-9_./-]*\.(?:md|py|sh|json|ini|yml))")
bad = []
for dp, _, fs in os.walk(claude):
    for fn in fs:
        if not fn.endswith(".md") or ".harness-incoming" in fn or ".proposed" in fn:
            continue
        full = os.path.join(dp, fn)
        rel = os.path.relpath(full, claude)
        lines = open(full, encoding="utf-8", errors="ignore").read().split("\n")
        for i, line in enumerate(lines, 1):
            # A doc MAY cite a harness-only path if it says so -- but prose wraps, so the marker
            # is looked for across the neighbouring lines, not just this one.
            window = " ".join(lines[max(0, i - 2):i + 1])
            if "harness repo" in window or "harness checkout" in window:
                continue
            for span in SPAN.findall(line):
                for m in PATH.finditer(span):
                    path = m.group(1)
                    if not path.startswith(ROOTS) or "<" in path:
                        continue
                    if path in SKIP or path.endswith(SKIP_SUFFIX):
                        continue
                    cand = (os.path.join(tgt, path) if path.startswith(".claude/")
                            else os.path.join(claude, path))
                    if not os.path.exists(cand):
                        bad.append(f"{rel}:{i} -> {path}")
for b in sorted(set(bad)):
    print(b)
PYEOF
    )
    if [ -n "$derived_out" ]; then
      while IFS= read -r line; do
        err "derived tree: $line does not exist in a consuming repo (ship it via CONSUMER_SCRIPTS, or say 'harness repo' nearby)"
      done <<< "$derived_out"
    fi
  else
    echo "  ⚠ doc-truth: derived-tree check skipped — deploy-harness.sh failed on a scratch target" >&2
  fi
fi

if [ "$FAILED" -eq 0 ]; then
  echo "  ✓ doc-truth lint: source + derived paths exist; hook table matches settings.json"
  exit 0
fi
exit 1
