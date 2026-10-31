#!/bin/bash
# Check that each release tag v5.1.0 and later points at a commit whose VERSION file matches
# the tag name.
#
# Verifies:        for every tag vX.Y.Z at or above v5.1.0, `git show <tag>:VERSION` (trimmed)
#                  equals the tag name without the leading v.
# Does not verify: tags below v5.1.0 (v1 to v4 fail this rule by design: v4.0.0 points at
#                  VERSION 2.28.0 and v5.0.0 was never tagged), or that a tag is the right release.
# Reads tags only. It never creates, moves, deletes or pushes a tag.
# Env: REQUIRE_TAGS=1 turns the no-tag skip and a failing `git tag` into a failure (CI sets it).
# Usage: bash scripts/check-tag-version.sh [--root DIR]
set -u
ROOT="."
[ "${1:-}" = "--root" ] && ROOT="${2:?--root needs a dir}"
cd "$ROOT" || exit 1
git rev-parse --git-dir >/dev/null 2>&1 || { echo "  ✗ tag version: $ROOT is not a git repo" >&2; exit 1; }
FIRST="5.1.0"
bad=0; checked=0
if ! tags=$(git tag --list 2>&1); then
  echo "  ✗ tag version: git tag --list failed: $tags" >&2
  [ "${REQUIRE_TAGS:-}" = 1 ] && exit 1
  echo "  skip — cannot list tags"; exit 0
fi
while IFS= read -r tag; do
  case "$tag" in v[0-9]*.[0-9]*.[0-9]*) ;; *) continue ;; esac
  ver="${tag#v}"
  case "$ver" in *[!0-9.]*) continue ;; esac
  # Skip tags below FIRST: under version sort, FIRST must come first.
  [ "$(printf '%s\n%s\n' "$FIRST" "$ver" | sort -t. -k1,1n -k2,2n -k3,3n | head -1)" = "$FIRST" ] || continue
  checked=$((checked + 1))
  have=$(git show "$tag:VERSION" 2>/dev/null | tr -d '[:space:]')
  if [ "$have" = "$ver" ]; then
    echo "  ✓ $tag VERSION $have"
  else
    echo "  ✗ $tag has VERSION '${have:-<none>}', want '$ver'" >&2
    bad=1
  fi
done <<EOF
$tags
EOF
if [ "$checked" -eq 0 ]; then
  if [ "${REQUIRE_TAGS:-}" = 1 ]; then
    echo "  ✗ tag version: no tag at or above v$FIRST and REQUIRE_TAGS=1" >&2
    exit 1
  fi
  echo "  skip — no tag at or above v$FIRST here (shallow clone without tags?)"
fi
exit "$bad"
