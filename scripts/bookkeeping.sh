#!/usr/bin/env bash
# Event-sourced harness bookkeeping.
#
# Given a MERGED PR's metadata, record it three ways so the trust record can never
# again decay from missed manual appends (v0.3 Phase 1):
#   1. append a row to docs/harness-experimental/trust-metrics.md
#   2. insert a dated `## [x.y.z]` section into CHANGELOG.md
#   3. bump root VERSION (minor if a contract path changed, else patch)
#
# This is pure + idempotent so it can be unit-tested offline — the GitHub Action
# (.github/workflows/post-merge-maintenance.yml) is only a thin wrapper that gathers
# PR metadata and calls this. Untrusted input (PR title) is only ever written to
# files via printf/awk variables — never eval'd.
#
# Usage:
#   scripts/bookkeeping.sh --pr N --title "T" --sha SHA --files "$(printf 'a\nb')" \
#     [--date YYYY-MM-DD] [--root DIR]
set -euo pipefail

PR="" TITLE="" SHA="" FILES="" DATE="" ROOT="."
while [ $# -gt 0 ]; do
  case "$1" in
    --pr)    PR="$2"; shift 2 ;;
    --title) TITLE="$2"; shift 2 ;;
    --sha)   SHA="$2"; shift 2 ;;
    --files) FILES="$2"; shift 2 ;;
    --date)  DATE="$2"; shift 2 ;;
    --root)  ROOT="$2"; shift 2 ;;
    *) echo "bookkeeping: unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -n "$PR" ] || { echo "bookkeeping: --pr is required" >&2; exit 2; }
[ -n "$DATE" ] || DATE=$(date +%F)   # caller may pin the date (tests / reproducibility)

cd "$ROOT"

LEDGER="docs/harness-experimental/trust-metrics.md"
CHANGELOG="CHANGELOG.md"
VERSION_FILE="VERSION"

# 1. Idempotency — never record the same PR twice (guards re-runs + version double-bump).
# Anchor to the outcome-column marker, NOT the whole line: a free-text note like
# "revert PR #8 broke things" must not make PR #8 a permanent no-op (silent data loss).
if [ -f "$LEDGER" ] && grep -qF "shipped (PR #${PR}, " "$LEDGER"; then
  echo "bookkeeping: PR #${PR} already recorded — no-op"
  exit 0
fi

# 2. Resolve slug + lane fields from the SUMMARY the merged PR added (if any).
# _field tolerates plain `Lane:` and bold `**Lane:**`, and strips a trailing CR (CRLF SUMMARY).
_field() {
  grep -m1 -iE "^\*{0,2}$1:" "$s" 2>/dev/null \
    | sed -E "s/^\*{0,2}$1:\*{0,2}[[:space:]]*//; s/[[:space:]]*$//; s/$(printf '\r')//" \
    || true
}
slug=$(printf '%s\n' "$FILES" | grep -oE 'specs/[^/]+/SUMMARY\.md' | head -1 | cut -d/ -f2 || true)
lane="-"; conf="-"; flags="-"; affects="-"
if [ -n "$slug" ] && [ -f "specs/$slug/SUMMARY.md" ]; then
  s="specs/$slug/SUMMARY.md"
  lane=$(_field Lane); conf=$(_field Confidence); flags=$(_field Flags); affects=$(_field Affects)
fi
[ -n "$slug" ] || slug="pr-${PR}"
[ -n "$lane" ] || lane="-"; [ -n "$conf" ] || conf="-"
[ -n "$flags" ] || flags="-"; [ -n "$affects" ] || affects="-"

# Sanitize the UNTRUSTED PR title to a single clean line before it touches any file.
# tr collapses real CR/LF/tab (blocks CHANGELOG heading injection via a real newline).
TITLE=$(printf '%s' "$TITLE" | tr '\r\n\t' '   ')
[ -n "$TITLE" ] || TITLE="(no title)"
# Ledger cell: escape pipes so a title can't add markdown-table columns.
TITLE_LEDGER=$(printf '%s' "$TITLE" | sed 's/|/\\|/g')

# 3. Version bump: minor when a contract path changed, else patch.
bump="patch"
if printf '%s\n' "$FILES" | grep -qE '^(hooks/|settings\.json|skills/)'; then
  bump="minor"
fi
cur=$(tr -d '[:space:]' < "$VERSION_FILE")
IFS=. read -r MA MI PA <<EOF
$cur
EOF
: "${MA:=0}"; : "${MI:=0}"; : "${PA:=0}"
if [ "$bump" = "minor" ]; then MI=$((MI + 1)); PA=0; else PA=$((PA + 1)); fi
new="${MA}.${MI}.${PA}"
printf '%s\n' "$new" > "$VERSION_FILE"

# 4. Insert a dated version section before the first NON-[Unreleased] `## [` heading (so it lands
# below [Unreleased] but above the previous version). If there is no such heading, the END block
# appends it — never a silent drop. The entry is passed via ENVIRON, NOT `awk -v`: `-v` expands
# backslash escapes (a title with a literal `\n` would forge a new heading); ENVIRON does not.
BK_ENTRY="- ${TITLE} (PR #${PR})" \
awk -v ver="$new" -v date="$DATE" '
  /^## \[/ && $0 !~ /^## \[Unreleased\]/ && !done {
    printf "## [%s] — %s\n\n%s\n\n", ver, date, ENVIRON["BK_ENTRY"]
    done = 1
  }
  { print }
  END { if (!done) printf "\n## [%s] — %s\n\n%s\n", ver, date, ENVIRON["BK_ENTRY"] }
' "$CHANGELOG" > "$CHANGELOG.tmp" && mv "$CHANGELOG.tmp" "$CHANGELOG"

# 5. Append the ledger row (pipe-escaped title so it can't add table columns).
printf '| %s | %s | %s | %s | %s | %s | %s | %s | %s |\n' \
  "$DATE" "$slug" "$lane" "$affects" "$conf" "$flags" "-" "shipped (PR #${PR}, \`${SHA}\`)" "$TITLE_LEDGER" \
  >> "$LEDGER"

# 6. Append one JSONL trend row (drift-audit snapshot + this PR number) so the advisory
# finding count becomes a trend instead of a single sample. No extra idempotency logic
# needed here — a re-run for an already-recorded PR exits at step 1, before this line.
TREND_LOG="docs/harness-experimental/audit-log.jsonl"
bash "$(dirname "$0")/harness-audit.sh" --root "$ROOT" --json | python3 -c '
import json, sys

d = json.loads(sys.stdin.read())
d["pr"] = int(sys.argv[1])
print(json.dumps(d))
' "$PR" >> "$TREND_LOG"

echo "bookkeeping: recorded PR #${PR} — VERSION ${cur} -> ${new} (${bump}); ledger + CHANGELOG updated; trend line appended"
