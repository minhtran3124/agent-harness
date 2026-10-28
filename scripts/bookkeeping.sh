#!/usr/bin/env bash
# Event-sourced harness bookkeeping.
#
# Given a MERGED PR's metadata, record it two ways so the release record can never
# decay from missed manual appends:
#   1. insert a dated `## [x.y.z]` section into CHANGELOG.md
#   2. bump root VERSION (minor if a contract path changed, else patch)
#
# This is pure + idempotent so it can be unit-tested offline — the GitHub Action
# (.github/workflows/post-merge-maintenance.yml) is only a thin wrapper that gathers
# PR metadata and calls this. Untrusted input (PR title) is only ever written to
# files via printf/awk variables — never eval'd.
#
# Usage:
#   scripts/bookkeeping.sh --pr N --title "T" --files "$(printf 'a\nb')" \
#     [--date YYYY-MM-DD] [--root DIR]
set -euo pipefail

PR="" TITLE="" FILES="" DATE="" ROOT="."
while [ $# -gt 0 ]; do
  case "$1" in
    --pr)    PR="$2"; shift 2 ;;
    --title) TITLE="$2"; shift 2 ;;
    --files) FILES="$2"; shift 2 ;;
    --date)  DATE="$2"; shift 2 ;;
    --root)  ROOT="$2"; shift 2 ;;
    *) echo "bookkeeping: unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -n "$PR" ] || { echo "bookkeeping: --pr is required" >&2; exit 2; }
[ -n "$DATE" ] || DATE=$(date +%F)   # caller may pin the date (tests / reproducibility)

cd "$ROOT"

CHANGELOG="CHANGELOG.md"
VERSION_FILE="VERSION"

# 1. Idempotency — never record the same PR twice (guards re-runs + version double-bump).
# Anchor to the end of an entry line ("- <title> (PR #N)"), NOT the whole file: a title that
# merely mentions "PR #8" must not make PR #8 a permanent no-op (silent data loss).
if [ -f "$CHANGELOG" ] && grep -qE "^- .*\\(PR #${PR}\\)\$" "$CHANGELOG"; then
  echo "bookkeeping: PR #${PR} already recorded — no-op"
  exit 0
fi

# Sanitize the UNTRUSTED PR title to a single clean line before it touches any file.
# tr collapses real CR/LF/tab (blocks CHANGELOG heading injection via a real newline).
TITLE=$(printf '%s' "$TITLE" | tr '\r\n\t' '   ')
[ -n "$TITLE" ] || TITLE="(no title)"

# 2. Version bump: minor when a contract path changed, else patch.
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

# 3. Insert a dated version section before the first NON-[Unreleased] `## [` heading (so it lands
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

echo "bookkeeping: recorded PR #${PR} — VERSION ${cur} -> ${new} (${bump}); CHANGELOG updated"
