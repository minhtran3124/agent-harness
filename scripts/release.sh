#!/usr/bin/env bash
# Prepare a release: bump VERSION and the plugin manifest version together, and add a dated
# `## [x.y.z]` section to CHANGELOG.md.
#
# The section holds the bullets that were under `## [Unreleased]` (moved, so [Unreleased] is left
# empty), then one bullet per merged PR since the last v* tag: `- <PR title> (PR #N)`. PR numbers
# and titles come from the merge commits (subject "Merge pull request #N from ...", title in the
# body), so the script needs no network and no gh. It runs on a plain checkout.
#
# Untrusted input (commit titles) is collapsed to one line and passed to awk through ENVIRON, never
# `awk -v` (which expands backslash escapes) and never eval'd.
#
# Usage: scripts/release.sh <patch|minor|major> [--dry-run] [--root DIR]
# Env:   RELEASE_DATE=YYYY-MM-DD overrides today's date (tests, reproducibility).
# Output: the last line of stdout is NEW_VERSION=x.y.z.
set -euo pipefail

usage() { echo "usage: release.sh <patch|minor|major> [--dry-run] [--root DIR]" >&2; }

BUMP="" DRY=0 ROOT="."
while [ $# -gt 0 ]; do
  case "$1" in
    patch|minor|major) BUMP="$1"; shift ;;
    --dry-run) DRY=1; shift ;;
    --root) [ $# -ge 2 ] || { usage; exit 2; }; ROOT="$2"; shift 2 ;;
    *) echo "release: unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done
[ -n "$BUMP" ] || { echo "release: a bump word (patch, minor or major) is required" >&2; usage; exit 2; }

DATE="${RELEASE_DATE:-$(date -u +%F)}"
case "$DATE" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
  *) echo "release: RELEASE_DATE must look like YYYY-MM-DD, got: $DATE" >&2; exit 2 ;;
esac

cd "$ROOT"
CHANGELOG="CHANGELOG.md"
MANIFEST="plugins/harness/.claude-plugin/plugin.json"

[ -f VERSION ] || { echo "release: VERSION not found" >&2; exit 1; }
[ -f "$CHANGELOG" ] || { echo "release: $CHANGELOG not found" >&2; exit 1; }
grep -q '^## \[Unreleased\]' "$CHANGELOG" || { echo "release: $CHANGELOG has no '## [Unreleased]' heading" >&2; exit 1; }

if [ "$DRY" -eq 0 ] && [ -n "$(git status --porcelain)" ]; then
  echo "release: the working tree is not clean; commit or stash first" >&2
  exit 1
fi

cur=$(tr -d '[:space:]' < VERSION)
# Strict check before any arithmetic: a glob would let `1.a[$(cmd)].2.3` reach $((MI + 1)).
semver_re='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
[[ $cur =~ $semver_re ]] || { echo "release: VERSION is not x.y.z: $cur" >&2; exit 1; }
IFS=. read -r MA MI PA <<EOF
$cur
EOF
case "$BUMP" in
  major) MA=$((MA + 1)); MI=0; PA=0 ;;
  minor) MI=$((MI + 1)); PA=0 ;;
  patch) PA=$((PA + 1)) ;;
esac
new="${MA}.${MI}.${PA}"

if grep -qF "## [${new}]" "$CHANGELOG"; then
  echo "release: $CHANGELOG already has a '## [${new}]' heading; nothing to do" >&2
  exit 1
fi

# One bullet per merged PR since the last v* tag (the whole history when there is none).
range="HEAD"
if last=$(git describe --tags --abbrev=0 --match 'v[0-9]*' 2>/dev/null); then range="${last}..HEAD"; fi
bullets=""
while IFS= read -r -d $'\x1e' rec || [ -n "$rec" ]; do
  rec=${rec#"${rec%%[![:space:]]*}"}   # git puts a newline between records
  subject=${rec%%$'\n'*}
  case "$subject" in
    *"Merge pull request #"*) ;;
    *) continue ;;
  esac
  num=${subject#*"Merge pull request #"}
  num=${num%% *}
  case "$num" in ''|*[!0-9]*) continue ;; esac
  # The PR title is the first non-empty line of the body.
  title=$(printf '%s\n' "${rec#*$'\n'}" | awk 'NF { print; exit }')
  title=$(printf '%s' "$title" | tr '\r\n\t' '   ')
  case "$title" in
    "chore(bookkeeping)"*|"chore(release)"*) continue ;;
  esac
  [ -n "${title//[[:space:]]/}" ] || title="(no title)"
  bullets="${bullets}- ${title} (PR #${num})"$'\n'
done < <(git log "$range" --merges --reverse --format='%s%n%b%x1e')

if [ "$DRY" -eq 1 ]; then
  echo "release: dry run, would bump ${cur} -> ${new} (${BUMP}); nothing written"
  printf '%s' "$bullets"
  echo "NEW_VERSION=${new}"
  exit 0
fi

# Insert the new section directly below [Unreleased]; the old [Unreleased] body moves into it.
REL_BULLETS="$bullets" awk -v ver="$new" -v date="$DATE" '
  function emit(   i, s, e) {
    s = 1; e = n
    while (s <= e && body[s] ~ /^[[:space:]]*$/) s++
    while (e >= s && body[e] ~ /^[[:space:]]*$/) e--
    printf "\n## [%s] — %s\n\n", ver, date
    for (i = s; i <= e; i++) print body[i]
    printf "%s", ENVIRON["REL_BULLETS"]
    print ""
  }
  /^## \[Unreleased\]/ { print; inun = 1; next }
  inun && /^## \[/ { emit(); inun = 0; print; next }
  inun { body[++n] = $0; next }
  { print }
  END { if (inun) emit() }
' "$CHANGELOG" > "$CHANGELOG.tmp" && mv "$CHANGELOG.tmp" "$CHANGELOG"

printf '%s\n' "$new" > VERSION

# Keep the plugin manifest in step (scripts/check-plugin-version.sh enforces equality). One sed on
# the single "version" line: jq may be absent, and BSD/GNU sed -i differ, so write a temp file.
if [ -f "$MANIFEST" ]; then
  sed "s/^\([[:space:]]*\"version\"[[:space:]]*:[[:space:]]*\"\)[^\"]*\(\".*\)\$/\1${new}\2/" "$MANIFEST" > "$MANIFEST.tmp" \
    && mv "$MANIFEST.tmp" "$MANIFEST"
fi

echo "release: VERSION ${cur} -> ${new} (${BUMP}); $CHANGELOG updated"
echo "NEW_VERSION=${new}"
