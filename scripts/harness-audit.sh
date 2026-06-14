#!/usr/bin/env bash
# harness-audit.sh — advisory drift detector for governance artifacts.
#
# Surfaces drift that the existing nets do NOT already cover. Out of scope here
# (already mechanized elsewhere):
#   - phantom path references + hook-table ↔ settings.json  →  scripts/lint-doc-truth.sh
#   - orphan untracked .py                                  →  hooks/check-untracked-py.sh
#
# In scope (the remaining "verify the docs" gap, OpenAI harness engineering #4):
#   1. specs/*/SUMMARY.md missing a `### Verify` section (proof was never recorded)
#   2. specs/*/PLAN.md with `status: active` whose newest date is stale (> STALE_DAYS)
#   3. docs/solutions/**/*.md with `confirmed_at` older than CONFIRMED_DAYS
#
# Advisory by default (exit 0, never blocks). `--strict` exits 1 when any drift is
# found — for opt-in CI use. Banded health summary + raw finding count are both printed.
set -u
cd "$(dirname "$0")/.." || exit 1

STALE_DAYS="${HARNESS_AUDIT_STALE_DAYS:-14}"
CONFIRMED_DAYS="${HARNESS_AUDIT_CONFIRMED_DAYS:-30}"
STRICT=0
[ "${1:-}" = "--strict" ] && STRICT=1

FINDINGS=0
note() { printf '  ⚠ %s\n' "$1"; FINDINGS=$((FINDINGS + 1)); }

# days_since YYYY-MM-DD -> integer days on stdout (empty on parse failure).
days_since() {
  python3 - "$1" <<'PY' 2>/dev/null
import sys
from datetime import date
try:
    y, m, d = map(int, sys.argv[1].split("-"))
    print((date.today() - date(y, m, d)).days)
except Exception:
    pass
PY
}

echo "=== Harness Audit (advisory) ==="

# ── 1. SUMMARY.md missing ### Verify ────────────────────────────────────────────
if compgen -G "specs/*/SUMMARY.md" >/dev/null 2>&1; then
  for s in specs/*/SUMMARY.md; do
    grep -qE '^###[[:space:]]+Verify[[:space:]]*$' "$s" \
      || note "SUMMARY missing '### Verify' section: $s"
  done
fi

# ── 2. Active PLAN.md gone stale ────────────────────────────────────────────────
if compgen -G "specs/*/PLAN.md" >/dev/null 2>&1; then
  for p in specs/*/PLAN.md; do
    # frontmatter status: active (anywhere in the file's status field)
    grep -qiE '^status:[[:space:]]*active' "$p" || continue
    newest=$(grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' "$p" | sort | tail -1)
    [ -n "$newest" ] || { note "active PLAN has no dated entries: $p"; continue; }
    age=$(days_since "$newest")
    if [ -n "$age" ] && [ "$age" -gt "$STALE_DAYS" ]; then
      note "active PLAN stale (${age}d > ${STALE_DAYS}d, newest $newest): $p"
    fi
  done
fi

# ── 3. docs/solutions confirmed_at past freshness window ────────────────────────
if [ -d docs/solutions ]; then
  while IFS= read -r doc; do
    val=$(grep -m1 -E '^confirmed_at:' "$doc" | sed -E 's/^confirmed_at:[[:space:]]*//; s/[[:space:]]*$//')
    [ -n "$val" ] || continue
    age=$(days_since "$val")
    if [ -n "$age" ] && [ "$age" -gt "$CONFIRMED_DAYS" ]; then
      note "solution stale (${age}d > ${CONFIRMED_DAYS}d, confirmed_at $val): $doc"
    fi
  done < <(find docs/solutions -name '*.md' -type f 2>/dev/null)
fi

# ── Banded health summary ───────────────────────────────────────────────────────
echo ""
if [ "$FINDINGS" -eq 0 ]; then
  band="healthy"
elif [ "$FINDINGS" -le 3 ]; then
  band="minor drift"
else
  band="needs attention"
fi
echo "  Drift findings: $FINDINGS  ($band)"

if [ "$STRICT" -eq 1 ] && [ "$FINDINGS" -gt 0 ]; then
  exit 1
fi
exit 0
