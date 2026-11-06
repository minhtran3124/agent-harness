#!/usr/bin/env bash
# Tag the commit that carries a new VERSION, and publish the GitHub release for it.
#
# Steps:
#   1. read VERSION and check plugin.json matches it (scripts/check-plugin-version.sh)
#   2. if tag v<VERSION> exists (locally or on origin), it must point at a commit whose VERSION
#      file is <VERSION>; else exit 1. A tag is never moved, deleted or overwritten.
#   3. otherwise create an annotated tag at HEAD and push only that tag
#   4. unless --no-release: create the GitHub release from the `## [<VERSION>]` section of
#      CHANGELOG.md; skip it when `gh release view` says it already exists. Pass --latest when
#      <VERSION> is above every existing v* tag, and --latest=false otherwise (never leave it automatic).
#
# A re-run is safe: with the tag and the release in place it changes nothing.
#
# Usage: scripts/release-tag.sh [--no-release] [--root DIR]
# Env:   GH_BIN overrides the gh binary (tests stub it). GH_TOKEN is read by gh itself.
set -euo pipefail

NO_RELEASE=0 ROOT="."
while [ $# -gt 0 ]; do
  case "$1" in
    --no-release) NO_RELEASE=1; shift ;;
    --root) [ $# -ge 2 ] || { echo "release-tag: --root needs a dir" >&2; exit 2; }; ROOT="$2"; shift 2 ;;
    *) echo "release-tag: unknown argument: $1" >&2; exit 2 ;;
  esac
done
GH="${GH_BIN:-gh}"

cd "$ROOT"
[ -f VERSION ] || { echo "release-tag: VERSION not found" >&2; exit 1; }
VERSION=$(tr -d '[:space:]' < VERSION)
semver_re='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
[[ $VERSION =~ $semver_re ]] || { echo "release-tag: VERSION is not x.y.z: $VERSION" >&2; exit 1; }
TAG="v${VERSION}"

bash scripts/check-plugin-version.sh || { echo "release-tag: plugin.json and VERSION differ; no tag made" >&2; exit 1; }

# The notes come first, so a missing section stops the run before any tag is made.
NOTES=""
if [ "$NO_RELEASE" -eq 0 ]; then
  NOTES=$(mktemp); trap 'rm -f "$NOTES"' EXIT
  [ -f CHANGELOG.md ] || { echo "release-tag: CHANGELOG.md not found" >&2; exit 1; }
  HEAD_PREFIX="## [${VERSION}]" awk '
    index($0, ENVIRON["HEAD_PREFIX"]) == 1 { on = 1; next }
    /^## \[/ { on = 0 }
    on { lines[++n] = $0 }
    END {
      s = 1; e = n
      while (s <= e && lines[s] ~ /^[[:space:]]*$/) s++
      while (e >= s && lines[e] ~ /^[[:space:]]*$/) e--
      for (i = s; i <= e; i++) print lines[i]
    }
  ' CHANGELOG.md > "$NOTES"
  if [ ! -s "$NOTES" ]; then
    echo "release-tag: CHANGELOG.md has no non-empty '## [${VERSION}]' section; no tag made" >&2
    exit 1
  fi
fi

has_origin=0
git remote get-url origin >/dev/null 2>&1 && has_origin=1

# Check where the tag exists. A tag found only on origin is fetched so its commit can be read.
local_tag=0 remote_tag=0
git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null && local_tag=1
if [ "$has_origin" -eq 1 ] && [ -n "$(git ls-remote --tags origin "refs/tags/${TAG}")" ]; then
  remote_tag=1
  if [ "$local_tag" -eq 0 ]; then
    git fetch -q origin "refs/tags/${TAG}:refs/tags/${TAG}"
    local_tag=1
    fetched_only=1
  fi
fi

if [ "$local_tag" -eq 1 ]; then
  tag_version=$(git show "${TAG}^{commit}:VERSION" 2>/dev/null | tr -d '[:space:]' || true)
  if [ "$tag_version" != "$VERSION" ]; then
    echo "release-tag: tag ${TAG} exists but its commit has VERSION '${tag_version:-<none>}', not '${VERSION}'." >&2
    echo "release-tag: refusing to touch an existing tag; fix it by hand if it is wrong." >&2
    [ "${fetched_only:-0}" -eq 1 ] && git tag -d "${TAG}" >/dev/null
    exit 1
  fi
  echo "release-tag: tag ${TAG} already exists at the right commit"
  if [ "$remote_tag" -eq 0 ] && [ "$has_origin" -eq 1 ]; then
    git push origin "refs/tags/${TAG}"
  fi
else
  git tag -a "${TAG}" -m "Release ${TAG}"
  echo "release-tag: created tag ${TAG} at $(git rev-parse --short HEAD)"
  [ "$has_origin" -eq 1 ] || { echo "release-tag: no origin remote to push to" >&2; exit 1; }
  git push origin "refs/tags/${TAG}"
fi

[ "$NO_RELEASE" -eq 1 ] && exit 0

if "$GH" release view "${TAG}" >/dev/null 2>&1; then
  echo "release-tag: GitHub release ${TAG} already exists; nothing to do"
  exit 0
fi

# --latest when this version is above every v* tag that exists (local and origin), else --latest=false.
latest_args=(--latest=false)
highest=$({ git tag --list 'v[0-9]*'; git ls-remote --tags origin 'refs/tags/v[0-9]*' 2>/dev/null \
  | sed -n 's|.*refs/tags/\(v[0-9][^^]*\)$|\1|p'; } | sort -V | tail -1)
[ "$highest" = "$TAG" ] && latest_args=(--latest)

"$GH" release create "${TAG}" --title "${TAG}" --notes-file "$NOTES" --verify-tag "${latest_args[@]}"
echo "release-tag: created GitHub release ${TAG}"
