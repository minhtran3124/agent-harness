#!/usr/bin/env bash
# harness-audit.sh — advisory drift detector for governance artifacts.
#
# Surfaces drift that the existing nets do NOT already cover. Out of scope here
# (already mechanized elsewhere):
#   - phantom path references + hook-table ↔ settings.json  →  scripts/lint-doc-truth.sh
#   - orphan untracked .py                                  →  hooks/check-untracked-py.sh
#
# In scope (the "verify the docs" gap, OpenAI harness engineering #4):
#   1. specs/*/SUMMARY.md missing a `### Verify` section (proof was never recorded)
#   2. specs/*/PLAN.md with `status: active` whose newest date is stale (> STALE_DAYS)
#   3. docs/solutions/**/*.md with `confirmed_at` older than CONFIRMED_DAYS
#   4. specs/*/SUMMARY.md `### Verify` commands that reference a path never re-run
#      outside intake (not present in scripts/run-tests.sh or any workflow file)
#   5. docs/harness-experimental/improvement-backlog.md `open` rows gone stale
#   6. harness-manifest.json degraded (scripts/check_manifest.py reports drift)
#   7. contract surfaces dirty in the working tree → reminder to verify consumers
#      (advisory only, via scripts/check-contract-impact.sh; never counted as drift)
#
# Advisory by default (exit 0, never blocks). `--strict` exits 1 when any drift is
# found — for opt-in CI use. `--root DIR` points the audit at another tree (tests).
# `--json` prints one machine-readable line instead of the human-readable report.
# Banded health summary + raw finding count are both printed in the human-readable path.
set -u

ROOT="$(dirname "$0")/.."
STRICT=0
JSON=0
while [ $# -gt 0 ]; do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --json)   JSON=1; shift ;;
    --root)   ROOT="$2"; shift 2 ;;
    *) echo "harness-audit: unknown arg: $1" >&2; exit 2 ;;
  esac
done

cd "$ROOT" || exit 1
ROOT="$(pwd)"

STALE_DAYS="${HARNESS_AUDIT_STALE_DAYS:-30}"
CONFIRMED_DAYS="${HARNESS_AUDIT_CONFIRMED_DAYS:-30}"
BACKLOG_DAYS="${HARNESS_AUDIT_BACKLOG_DAYS:-14}"

FINDINGS=0
VERIFY_MISSING=0
PLAN_STALE=0
VERIFY_NEVER_RERUN=0
BACKLOG_STALE=0
MANIFEST_DEGRADED=0
SOLUTIONS_STALE=0
CONTRACT_IMPACT=0

note() {
  [ "$JSON" -eq 1 ] || printf '  ⚠ %s\n' "$1"
  FINDINGS=$((FINDINGS + 1))
}

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

[ "$JSON" -eq 1 ] || echo "=== Harness Audit (advisory) ==="

# ── 1. SUMMARY.md missing ### Verify ────────────────────────────────────────────
if compgen -G "specs/*/SUMMARY.md" >/dev/null 2>&1; then
  for s in specs/*/SUMMARY.md; do
    if ! grep -qE '^###[[:space:]]+Verify[[:space:]]*$' "$s"; then
      note "SUMMARY missing '### Verify' section: $s"
      VERIFY_MISSING=$((VERIFY_MISSING + 1))
    fi
  done
fi

# ── 2. Active PLAN.md gone stale ────────────────────────────────────────────────
if compgen -G "specs/*/PLAN.md" >/dev/null 2>&1; then
  for p in specs/*/PLAN.md; do
    # frontmatter status: active (anywhere in the file's status field)
    grep -qiE '^status:[[:space:]]*active' "$p" || continue
    newest=$(grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' "$p" | sort | tail -1)
    if [ -z "$newest" ]; then
      note "active PLAN has no dated entries: $p"
      PLAN_STALE=$((PLAN_STALE + 1))
      continue
    fi
    age=$(days_since "$newest")
    if [ -n "$age" ] && [ "$age" -gt "$STALE_DAYS" ]; then
      note "active PLAN stale (${age}d > ${STALE_DAYS}d, newest $newest): $p"
      PLAN_STALE=$((PLAN_STALE + 1))
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
      SOLUTIONS_STALE=$((SOLUTIONS_STALE + 1))
    fi
  done < <(find docs/solutions -name '*.md' -type f 2>/dev/null)
fi

# ── 4. SUMMARY.md ### Verify commands never re-run outside intake ───────────────
if compgen -G "specs/*/SUMMARY.md" >/dev/null 2>&1; then
  _vnr_files=()
  [ -f scripts/run-tests.sh ] && _vnr_files+=("scripts/run-tests.sh")
  if compgen -G ".github/workflows/*.yml" >/dev/null 2>&1; then
    _vnr_files+=(.github/workflows/*.yml)
  fi
  for s in specs/*/SUMMARY.md; do
    grep -qE '^###[[:space:]]+Verify[[:space:]]*$' "$s" || continue
    stale=0
    offending_cmd=""
    while IFS= read -r row; do
      [ -n "$row" ] || continue
      check_cell=$(awk -F'|' '{print $2}' <<< "$row" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
      check_cell_lc=$(printf '%s' "$check_cell" | tr '[:upper:]' '[:lower:]')
      [ "$check_cell_lc" = "check" ] && continue
      if [[ "$check_cell" =~ ^-+$ ]]; then continue; fi
      cmd=$(awk -F'|' '{print $3}' <<< "$row" | tr -d '`')
      cmd=$(printf '%s' "$cmd" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
      case "$cmd" in
        ''|'<command>'|'-'|'—'|'–') continue ;;
      esac
      has_path=0
      matched=0
      for tok in $cmd; do
        [[ "$tok" == */* ]] || continue
        has_path=1
        for f in "${_vnr_files[@]+"${_vnr_files[@]}"}"; do
          [ -f "$f" ] || continue
          grep -qF -- "$tok" "$f" 2>/dev/null && { matched=1; break; }
        done
        [ "$matched" -eq 1 ] && break
      done
      if [ "$has_path" -eq 1 ] && [ "$matched" -eq 0 ]; then
        stale=1
        [ -n "$offending_cmd" ] || offending_cmd="$cmd"
      fi
    done < <(awk '/^### Verify[[:space:]]*$/{f=1;next} f && /^#/{f=0} f' "$s" | grep -E '^\|')
    if [ "$stale" -eq 1 ]; then
      note "verify command never re-run outside intake: $s -> $offending_cmd"
      VERIFY_NEVER_RERUN=$((VERIFY_NEVER_RERUN + 1))
    fi
  done
fi

# ── 5. improvement-backlog.md: open entries gone stale ───────────────────────────
BACKLOG_FILE="docs/harness-experimental/improvement-backlog.md"
if [ -f "$BACKLOG_FILE" ]; then
  while IFS= read -r row; do
    [ -n "$row" ] || continue
    date_cell=$(awk -F'|' '{print $2}' <<< "$row" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
    date_cell_lc=$(printf '%s' "$date_cell" | tr '[:upper:]' '[:lower:]')
    [ "$date_cell_lc" = "date" ] && continue
    if [[ "$date_cell" =~ ^-+$ ]]; then continue; fi
    slug_cell=$(awk -F'|' '{print $3}' <<< "$row" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
    status_cell=$(awk -F'|' '{print $6}' <<< "$row" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
    [ "$status_cell" = "open" ] || continue
    age=$(days_since "$date_cell")
    if [ -n "$age" ] && [ "$age" -gt "$BACKLOG_DAYS" ]; then
      note "backlog entry open ${age}d > ${BACKLOG_DAYS}d: $slug_cell (opened $date_cell)"
      BACKLOG_STALE=$((BACKLOG_STALE + 1))
    fi
  done < <(grep -E '^\|' "$BACKLOG_FILE")
fi

# ── 6. harness-manifest.json degraded (check_manifest.py reports drift) ─────────
if [ -f harness-manifest.json ] && [ -f scripts/check_manifest.py ] && command -v python3 >/dev/null 2>&1; then
  if ! python3 scripts/check_manifest.py --root "$ROOT" >/dev/null 2>&1; then
    MANIFEST_DEGRADED=1
    note "harness-manifest.json degraded (check_manifest.py reported drift)"
  fi
fi

# ── 7. contract surfaces dirty in working tree → remind consumers ───────────────
if [ -f scripts/check-contract-impact.sh ]; then
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    [ "$JSON" -eq 1 ] || printf '  ↳ %s\n' "$line"
    CONTRACT_IMPACT=$((CONTRACT_IMPACT + 1))
  done < <(bash scripts/check-contract-impact.sh --changed --root "$ROOT")
fi

# ── Banded health summary ───────────────────────────────────────────────────────
if [ "$FINDINGS" -eq 0 ]; then
  band="healthy"
elif [ "$FINDINGS" -le 3 ]; then
  band="minor drift"
else
  band="needs attention"
fi

if [ "$JSON" -eq 1 ]; then
  python3 -c '
import json, sys

date, findings, band, vm, ps, vnr, bs, md, ss, ci = sys.argv[1:11]
print(json.dumps({
    "date": date,
    "findings": int(findings),
    "band": band,
    "checks": {
        "verify_missing": int(vm),
        "plan_stale": int(ps),
        "verify_never_rerun": int(vnr),
        "backlog_stale": int(bs),
        "manifest_degraded": int(md),
        "solutions_stale": int(ss),
        "contract_impact": int(ci),
    },
}))
' "$(date +%F)" "$FINDINGS" "$band" "$VERIFY_MISSING" "$PLAN_STALE" "$VERIFY_NEVER_RERUN" "$BACKLOG_STALE" "$MANIFEST_DEGRADED" "$SOLUTIONS_STALE" "$CONTRACT_IMPACT"
else
  echo ""
  echo "  Drift findings: $FINDINGS  ($band)"
  [ "$CONTRACT_IMPACT" -eq 0 ] || echo "  Contract-impact reminders: $CONTRACT_IMPACT"
fi

if [ "$STRICT" -eq 1 ] && [ "$FINDINGS" -gt 0 ]; then
  exit 1
fi
exit 0
