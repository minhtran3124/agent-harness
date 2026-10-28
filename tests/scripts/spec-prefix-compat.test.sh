#!/bin/bash
# Regression tests for issue #121 (scripts half): bookkeeping resolves
# ticket-prefixed slugs (gh-/lin-) exactly like plain ones.
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

finish
