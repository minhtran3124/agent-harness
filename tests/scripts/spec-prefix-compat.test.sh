#!/bin/bash
# Regression tests for issue #121 (scripts half): bookkeeping and the
# python gate engines resolve ticket-prefixed slugs (gh-/lin-) exactly like plain ones.
source "$(dirname "$0")/../lib.sh"

GH="gh-999-fixture"

# ── bookkeeping.sh: slug extraction from a prefixed SUMMARY path ──
SCRIPT="$ROOT/scripts/bookkeeping.sh"

t "bookkeeping extracts the full prefixed folder name as the ledger slug"
d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
printf '0.2.0\n' > "$d/VERSION"
mkdir -p "$d/docs/harness-experimental"
printf '# Trust Metrics Ledger\n\n## Ledger\n\n| Date | Slug | Lane | Affects | Confidence | Flags | Escalated | Outcome | Notes |\n|---|---|---|---|---|---|---|---|---|\n| 2026-06-14 | old | normal | - | high | none | no | shipped | seed |\n' > "$d/docs/harness-experimental/trust-metrics.md"
printf '# Changelog\n\n## [Unreleased]\n\n## [0.2.0] — 2026-06-14\n\n### Changed\n- seed\n' > "$d/CHANGELOG.md"
mkdir -p "$d/specs/$GH"
printf 'Lane: high-risk\nConfidence: medium\nFlags: none\nAffects: hooks/foo.sh\n' > "$d/specs/$GH/SUMMARY.md"
bash "$SCRIPT" --pr 7 --title T --sha s --files "specs/$GH/SUMMARY.md" --date 2026-07-20 --root "$d" >/dev/null
row=$(tail -1 "$d/docs/harness-experimental/trust-metrics.md")
if echo "$row" | grep -q "$GH" && echo "$row" | grep -q 'high-risk'; then pass
else fail "ledger row missing prefixed slug/lane: $row"; fi

# ── python engines: prefixed slug → specs/<slug>/SUMMARY.md path join ──
if command -v python3 >/dev/null 2>&1; then
  t "verify_summary.py --lane resolves a prefixed slug via specs_root"
  d2=$(mktemp -d); _CLEANUP_DIRS+=("$d2")
  mkdir -p "$d2/specs/$GH"
  printf 'Lane: tiny\nConfidence: high\nReason: a real filled reason\n' > "$d2/specs/$GH/SUMMARY.md"
  OUT=$(python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '$ROOT/scripts')
from verify_summary import main
sys.exit(main(['--lane', '$GH'], specs_root=Path('$d2/specs')))
" 2>&1); RC=$?
  assert_rc 0

  t "verify_summary.py --lane fails a prefixed slug whose evidence is missing (resolution really happened)"
  d3=$(mktemp -d); _CLEANUP_DIRS+=("$d3")
  mkdir -p "$d3/specs/$GH"
  printf 'Lane: high-risk\nConfidence: medium\nReason: r\n' > "$d3/specs/$GH/SUMMARY.md"
  OUT=$(python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '$ROOT/scripts')
from verify_summary import main
sys.exit(main(['--lane', '$GH'], specs_root=Path('$d3/specs')))
" 2>&1); RC=$?
  assert_rc 1
else
  t "python engine cases"; skip "python3 unavailable"
fi

finish
