#!/bin/bash
# Unit tests for scripts/release-tag.sh: tag creation, the refusals, and the release step.
# Each case works in a throwaway repo with a bare repo as `origin` and a stub gh; no network.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/release-tag.sh"

# A stub gh. It logs every call; `release view` succeeds only after a `release create` ran.
STUB_DIR=$(mktemp -d); _CLEANUP_DIRS+=("$STUB_DIR")
cat > "$STUB_DIR/gh" <<'STUB'
#!/bin/bash
echo "$*" >> "$GH_LOG"
case "$1 $2" in
  "release view") [ -f "$GH_LOG.created" ] ;;
  "release create")
    : > "$GH_LOG.created"
    while [ $# -gt 0 ]; do
      [ "$1" = "--notes-file" ] && cp "$2" "$GH_LOG.notes"
      shift
    done ;;
  *) exit 0 ;;
esac
STUB
chmod +x "$STUB_DIR/gh"

# make_fixture <version> → echoes a repo dir; origin is <dir>.git, GH_LOG is <dir>.gh.log.
make_fixture() {
  local v="${1:-2.0.0}" d
  d=$(mktemp -d); _CLEANUP_DIRS+=("$d" "$d.git")
  git init -q --bare "$d.git"
  git -C "$d" init -q -b main 2>/dev/null || git -C "$d" init -q
  git -C "$d" config user.email test@test
  git -C "$d" config user.name test
  printf '%s\n' "$v" > "$d/VERSION"
  mkdir -p "$d/plugins/harness/.claude-plugin" "$d/scripts"
  printf '{\n  "version": "%s"\n}\n' "$v" > "$d/plugins/harness/.claude-plugin/plugin.json"
  cp "$ROOT/scripts/check-plugin-version.sh" "$d/scripts/"
  printf '# Changelog\n\n## [Unreleased]\n\n## [%s] — 2026-11-06\n\n- feat: first (PR #1)\n- fix: second (PR #2)\n\n## [0.1.0] — 2026-01-01\n\n- old\n' "$v" > "$d/CHANGELOG.md"
  git -C "$d" add -A && git -C "$d" commit -q -m "release $v"
  git -C "$d" remote add origin "$d.git"
  git -C "$d" push -q origin main 2>/dev/null
  echo "$d"
}

# run <repo> [args...] → OUT, RC, with the stub gh and a per-repo call log.
run() {
  local d="$1"; shift
  OUT=$(cd "$d" && GH_BIN="$STUB_DIR/gh" GH_LOG="$d.gh.log" bash "$SCRIPT" "$@" 2>&1); RC=$?
}
gh_calls() { cat "$1.gh.log" 2>/dev/null; }

t "creates an annotated tag at HEAD and pushes only that tag to origin"
d=$(make_fixture 2.0.0)
run "$d"
head=$(git -C "$d" rev-parse HEAD)
if [ "$RC" -eq 0 ] && [ "$(git -C "$d" cat-file -t refs/tags/v2.0.0)" = tag ] \
   && [ "$(git -C "$d" rev-parse 'v2.0.0^{commit}')" = "$head" ] \
   && [ "$(git -C "$d.git" rev-parse 'refs/tags/v2.0.0^{commit}')" = "$head" ]; then pass
else fail "rc=$RC out=$OUT"; fi

t "creates the GitHub release with the CHANGELOG section as notes and --verify-tag"
if grep -q '^release create v2.0.0 --title v2.0.0 --notes-file .* --verify-tag' "$d.gh.log" \
   && [ "$(cat "$d.gh.log.notes")" = "$(printf -- '- feat: first (PR #1)\n- fix: second (PR #2)')" ]; then pass
else fail "calls: $(gh_calls "$d") notes: $(cat "$d.gh.log.notes" 2>/dev/null)"; fi

t "marks the release --latest when the version is above every existing tag"
if grep -q -- ' --latest\( \|$\)' "$d.gh.log" && ! grep -q -- '--latest=false' "$d.gh.log"; then pass; else fail "calls: $(gh_calls "$d")"; fi

t "a second run is a no-op: same tag, no second release"
before=$(git -C "$d" rev-parse refs/tags/v2.0.0); n1=$(grep -c '^release create' "$d.gh.log")
run "$d"
after=$(git -C "$d" rev-parse refs/tags/v2.0.0); n2=$(grep -c '^release create' "$d.gh.log")
if [ "$RC" -eq 0 ] && [ "$before" = "$after" ] && [ "$n1" = 1 ] && [ "$n2" = 1 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "refuses when the tag points at a commit whose VERSION differs, and leaves the tag alone"
d=$(make_fixture 2.0.0)
old=$(git -C "$d" rev-parse HEAD)
printf '2.1.0\n' > "$d/VERSION"
sed 's/2\.0\.0/2.1.0/' "$d/plugins/harness/.claude-plugin/plugin.json" > "$d/p.tmp" && mv "$d/p.tmp" "$d/plugins/harness/.claude-plugin/plugin.json"
git -C "$d" commit -q -am "bump"
git -C "$d" tag -a v2.1.0 "$old" -m "wrong place"
git -C "$d" push -q origin refs/tags/v2.1.0 2>/dev/null
run "$d"
if [ "$RC" -ne 0 ] && [ "$(git -C "$d" rev-parse 'v2.1.0^{commit}')" = "$old" ] \
   && [ "$(git -C "$d.git" rev-parse 'refs/tags/v2.1.0^{commit}')" = "$old" ] && [ -z "$(gh_calls "$d")" ]; then pass
else fail "rc=$RC out=$OUT"; fi

t "refuses when the tag exists only on origin and points at a commit with another VERSION"
d=$(make_fixture 2.0.0)
old=$(git -C "$d" rev-parse HEAD)
printf '2.1.0\n' > "$d/VERSION"
sed 's/2\.0\.0/2.1.0/' "$d/plugins/harness/.claude-plugin/plugin.json" > "$d/p.tmp" && mv "$d/p.tmp" "$d/plugins/harness/.claude-plugin/plugin.json"
git -C "$d" commit -q -am "bump"
git -C "$d" tag -a v2.1.0 "$old" -m "wrong place"
git -C "$d" push -q origin refs/tags/v2.1.0 2>/dev/null
git -C "$d" tag -d v2.1.0 >/dev/null
run "$d"
if [ "$RC" -ne 0 ] && [ "$(git -C "$d.git" rev-parse 'refs/tags/v2.1.0^{commit}')" = "$old" ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "refuses when plugin.json differs from VERSION, creates no tag"
d=$(make_fixture 2.0.0)
sed 's/2\.0\.0/1.9.9/' "$d/plugins/harness/.claude-plugin/plugin.json" > "$d/p.tmp" && mv "$d/p.tmp" "$d/plugins/harness/.claude-plugin/plugin.json"
git -C "$d" commit -q -am "drift"
run "$d"
if [ "$RC" -ne 0 ] && [ -z "$(git -C "$d" tag)" ] && [ -z "$(git -C "$d.git" tag)" ] && [ -z "$(gh_calls "$d")" ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "an older version than an existing tag gets --latest=false"
d=$(make_fixture 2.0.0)
git -C "$d" tag -a v3.0.0 -m "newer" && git -C "$d" push -q origin refs/tags/v3.0.0 2>/dev/null
run "$d"
if [ "$RC" -eq 0 ] && grep -q '^release create v2.0.0' "$d.gh.log" && grep -q -- ' --latest=false\( \|$\)' "$d.gh.log"; then pass; else fail "rc=$RC calls: $(gh_calls "$d")"; fi

t "--no-release creates and pushes the tag and never calls gh"
d=$(make_fixture 2.0.0)
run "$d" --no-release
if [ "$RC" -eq 0 ] && [ -n "$(git -C "$d.git" tag)" ] && [ -z "$(gh_calls "$d")" ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "skips release creation when gh release view succeeds"
d=$(make_fixture 2.0.0)
: > "$d.gh.log.created"
run "$d"
if [ "$RC" -eq 0 ] && ! grep -q '^release create' "$d.gh.log" && [ -n "$(git -C "$d.git" tag)" ]; then pass; else fail "rc=$RC calls: $(gh_calls "$d")"; fi

t "fails before tagging when the CHANGELOG section is missing"
d=$(make_fixture 2.0.0)
sed 's/^## \[2\.0\.0\].*/## [Unreleased-ish]/' "$d/CHANGELOG.md" > "$d/c.tmp" && mv "$d/c.tmp" "$d/CHANGELOG.md"
git -C "$d" commit -q -am "no section"
run "$d"
if [ "$RC" -ne 0 ] && [ -z "$(git -C "$d" tag)" ] && [ -z "$(git -C "$d.git" tag)" ]; then pass; else fail "rc=$RC out=$OUT tags=$(git -C "$d" tag)"; fi

t "fails when the CHANGELOG section is empty"
d=$(make_fixture 2.0.0)
printf '# Changelog\n\n## [2.0.0] — 2026-11-06\n\n## [0.1.0] — 2026-01-01\n\n- old\n' > "$d/CHANGELOG.md"
git -C "$d" commit -q -am "empty"
run "$d"
if [ "$RC" -ne 0 ] && [ -z "$(git -C "$d.git" tag)" ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a VERSION with a shell payload runs nothing and is refused"
d=$(make_fixture 2.0.0)
printf '1.a[$(touch CANARY)].2.3\n' > "$d/VERSION"
git -C "$d" commit -q -am payload
run "$d"
if [ "$RC" -ne 0 ] && [ ! -e "$d/CANARY" ] && [ -z "$(git -C "$d" tag)" ]; then pass; else fail "rc=$RC out=$OUT"; fi

for bad in 1.2 1.2.3.4 v1.2.3 1.0.0-x 01.2.3; do
  t "a VERSION of $bad is refused"
  d=$(make_fixture 2.0.0)
  printf '%s\n' "$bad" > "$d/VERSION"
  git -C "$d" commit -q -am bad
  run "$d"
  if [ "$RC" -ne 0 ] && echo "$OUT" | grep -q 'VERSION is not x.y.z' && [ -z "$(git -C "$d" tag)" ]; then pass; else fail "rc=$RC out=$OUT"; fi
done

finish
