#!/bin/bash
# Unit tests for scripts/release.sh: the version bump, the CHANGELOG section built from merge
# commits, and the refusals. Each case works in a throwaway git repo; nothing touches the network.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/release.sh"
export RELEASE_DATE=2026-11-06

# make_fixture <version> → a clean repo with VERSION, plugin.json, CHANGELOG.md and one tag v<version>.
make_fixture() {
  local v="${1:-1.2.3}" d
  d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main 2>/dev/null || git -C "$d" init -q
  git -C "$d" config user.email test@test
  git -C "$d" config user.name test
  printf '%s\n' "$v" > "$d/VERSION"
  mkdir -p "$d/plugins/harness/.claude-plugin"
  printf '{\n  "name": "harness",\n  "version": "%s",\n  "description": "d, \\"version\\": x"\n}\n' "$v" > "$d/plugins/harness/.claude-plugin/plugin.json"
  printf '# Changelog\n\n## [Unreleased]\n\n## [%s] — 2026-01-01\n\n- seed\n' "$v" > "$d/CHANGELOG.md"
  git -C "$d" add -A && git -C "$d" commit -q -m init
  git -C "$d" tag -a "v$v" -m "v$v"
  echo "$d"
}

# merge_pr <repo> <n> <title> → a real merge commit "Merge pull request #n from o/b<n>" with the title as body.
merge_pr() {
  git -C "$1" checkout -q -b "b$2"
  echo "$2" > "$1/f$2.txt"; git -C "$1" add -A; git -C "$1" commit -q -m "work $2"
  git -C "$1" checkout -q main
  git -C "$1" merge -q --no-ff -m "Merge pull request #$2 from o/b$2" -m "$3" "b$2"
}

run() { OUT=$(bash "$SCRIPT" "$@" 2>&1); RC=$?; }

for pair in "patch 1.2.3 1.2.4" "minor 1.2.3 1.3.0" "major 1.2.3 2.0.0"; do
  # shellcheck disable=SC2086
  set -- $pair
  t "$1 bump turns $2 into $3 in VERSION and plugin.json"
  d=$(make_fixture "$2")
  merge_pr "$d" 1 "seed change"
  run "$1" --root "$d"
  if [ "$RC" -eq 0 ] && [ "$(cat "$d/VERSION")" = "$3" ] \
     && grep -q "^  \"version\": \"$3\",\$" "$d/plugins/harness/.claude-plugin/plugin.json" \
     && bash "$ROOT/scripts/check-plugin-version.sh" --root "$d" >/dev/null \
     && [ "$(printf '%s\n' "$OUT" | tail -1)" = "NEW_VERSION=$3" ]; then pass
  else fail "rc=$RC version=$(cat "$d/VERSION") out=$OUT"; fi
done

t "minor resets patch and major resets minor and patch"
d=$(make_fixture 3.4.5); merge_pr "$d" 1 "seed change"; run minor --root "$d"; a=$(cat "$d/VERSION")
d=$(make_fixture 3.4.5); merge_pr "$d" 1 "seed change"; run major --root "$d"; b=$(cat "$d/VERSION")
if [ "$a" = "3.5.0" ] && [ "$b" = "4.0.0" ]; then pass; else fail "minor=$a major=$b"; fi

t "plugin.json changes only on the version line"
d=$(make_fixture 1.2.3)
merge_pr "$d" 1 "seed change"
run patch --root "$d"
if [ "$(git -C "$d" diff -U0 -- plugins | grep -c '^[-+] ')" -eq 2 ]; then pass; else fail "$(git -C "$d" diff -- plugins)"; fi

t "CHANGELOG gets a dated section below [Unreleased] built from merge commits"
d=$(make_fixture 1.2.3)
merge_pr "$d" 5 "feat: first thing"
merge_pr "$d" 6 "fix: second thing"
run minor --root "$d"
cl="$d/CHANGELOG.md"
u=$(grep -n '^## \[Unreleased\]' "$cl" | cut -d: -f1); n=$(grep -n '^## \[1.3.0\] — 2026-11-06' "$cl" | cut -d: -f1); o=$(grep -n '^## \[1.2.3\]' "$cl" | cut -d: -f1)
if [ -n "$n" ] && [ "$u" -lt "$n" ] && [ "$n" -lt "$o" ] && grep -qx -- '- feat: first thing (PR #5)' "$cl" \
   && grep -qx -- '- fix: second thing (PR #6)' "$cl"; then pass; else fail "$(cat "$cl")"; fi

t "bullets under [Unreleased] move into the new section and [Unreleased] is left empty"
d=$(make_fixture 1.2.3)
printf '# Changelog\n\n## [Unreleased]\n\n- feat: kept bullet\n  continued line\n\n## [1.2.3] — 2026-01-01\n\n- seed\n' > "$d/CHANGELOG.md"
git -C "$d" commit -q -am cl
merge_pr "$d" 7 "docs: from merge"
run patch --root "$d"
cl="$d/CHANGELOG.md"
between=$(sed -n '/^## \[Unreleased\]/,/^## \[1.2.4\]/p' "$cl" | grep -c 'kept bullet')
after=$(sed -n '/^## \[1.2.4\]/,/^## \[1.2.3\]/p' "$cl")
if [ "$between" -eq 0 ] && printf '%s\n' "$after" | grep -q 'kept bullet' && printf '%s\n' "$after" | grep -q '^  continued line' \
   && printf '%s\n' "$after" | grep -q 'docs: from merge (PR #7)'; then pass; else fail "$(cat "$cl")"; fi

t "bookkeeping and release merges are excluded"
d=$(make_fixture 1.2.3)
merge_pr "$d" 8 "chore(bookkeeping): record PR #7"
merge_pr "$d" 9 "chore(release): v1.2.3"
merge_pr "$d" 10 "feat: real one"
run patch --root "$d"
if grep -q 'real one (PR #10)' "$d/CHANGELOG.md" && ! grep -q 'PR #8)\|PR #9)' "$d/CHANGELOG.md"; then pass; else fail "$(cat "$d/CHANGELOG.md")"; fi

t "only merges after the last v tag are listed"
d=$(make_fixture 1.2.3)
merge_pr "$d" 11 "old: before tag"
printf '1.2.4\n' > "$d/VERSION"
sed 's/1\.2\.3/1.2.4/' "$d/plugins/harness/.claude-plugin/plugin.json" > "$d/p.tmp" && mv "$d/p.tmp" "$d/plugins/harness/.claude-plugin/plugin.json"
sed 's/^## \[1\.2\.3\]/## [1.2.4]/' "$d/CHANGELOG.md" > "$d/c.tmp" && mv "$d/c.tmp" "$d/CHANGELOG.md"
git -C "$d" commit -q -am bump; git -C "$d" tag -a v1.2.4 -m x
merge_pr "$d" 12 "new: after tag"
run patch --root "$d"
if [ "$RC" -eq 0 ] && grep -q 'after tag (PR #12)' "$d/CHANGELOG.md" && ! grep -q 'before tag' "$d/CHANGELOG.md"; then pass; else fail "$OUT $(cat "$d/CHANGELOG.md")"; fi

t "a title with CR, LF or tab collapses to one line and forges no heading"
d=$(make_fixture 1.2.3)
merge_pr "$d" 13 'evil'
git -C "$d" commit -q --amend -m "Merge pull request #13 from o/b13" -m "$(printf 'bad\tone\r## [9.9.9] — hijack')"
run patch --root "$d"
if ! grep -qE '^## \[9\.9\.9\]' "$d/CHANGELOG.md" && grep -q 'PR #13)' "$d/CHANGELOG.md"; then pass; else fail "$(cat "$d/CHANGELOG.md")"; fi

t "refuses a dirty working tree and changes nothing"
d=$(make_fixture 1.2.3)
echo x > "$d/stray.txt"
run patch --root "$d"
if [ "$RC" -ne 0 ] && [ "$(cat "$d/VERSION")" = "1.2.3" ]; then pass; else fail "rc=$RC"; fi

t "refuses an unknown bump word and a missing one"
d=$(make_fixture 1.2.3)
run bogus --root "$d"; rc1=$RC
run --root "$d"; rc2=$RC
if [ "$rc1" -ne 0 ] && [ "$rc2" -ne 0 ] && [ "$(cat "$d/VERSION")" = "1.2.3" ]; then pass; else fail "rc1=$rc1 rc2=$rc2"; fi

t "refuses when the new version heading already exists"
d=$(make_fixture 1.2.3)
printf '# Changelog\n\n## [Unreleased]\n\n## [1.2.4] — 2026-02-02\n\n- x\n\n## [1.2.3] — 2026-01-01\n\n- seed\n' > "$d/CHANGELOG.md"
git -C "$d" commit -q -am cl
run patch --root "$d"
if [ "$RC" -ne 0 ] && [ "$(cat "$d/VERSION")" = "1.2.3" ] && echo "$OUT" | grep -q '1.2.4'; then pass; else fail "rc=$RC out=$OUT"; fi

t "--dry-run changes nothing, even on a dirty tree, and still prints NEW_VERSION"
d=$(make_fixture 1.2.3)
merge_pr "$d" 14 "feat: x"
echo x > "$d/stray.txt"
run minor --dry-run --root "$d"
if [ "$RC" -eq 0 ] && [ "$(cat "$d/VERSION")" = "1.2.3" ] && ! grep -q '1.3.0' "$d/CHANGELOG.md" \
   && [ "$(git -C "$d" status --porcelain)" = "?? stray.txt" ] && [ "$(printf '%s\n' "$OUT" | tail -1)" = "NEW_VERSION=1.3.0" ]; then pass
else fail "rc=$RC out=$OUT"; fi

t "works with no tag at all (whole history)"
d=$(make_fixture 1.2.3)
git -C "$d" tag -d v1.2.3 >/dev/null
merge_pr "$d" 15 "feat: no tag"
run patch --root "$d"
if [ "$RC" -eq 0 ] && grep -q 'no tag (PR #15)' "$d/CHANGELOG.md"; then pass; else fail "rc=$RC out=$OUT"; fi

t "a VERSION with a shell payload runs nothing and is refused"
d=$(make_fixture 1.2.3)
printf '1.a[$(touch CANARY)].2.3\n' > "$d/VERSION"
git -C "$d" commit -q -am payload
run patch --root "$d"
if [ "$RC" -ne 0 ] && [ ! -e "$d/CANARY" ]; then pass; else fail "rc=$RC canary=$(ls "$d/CANARY" 2>&1) out=$OUT"; fi

for bad in 1.2 1.2.3.4 v1.2.3 1.0.0-x 01.2.3; do
  t "a VERSION of $bad is refused"
  d=$(make_fixture 1.2.3)
  printf '%s\n' "$bad" > "$d/VERSION"
  git -C "$d" commit -q -am bad
  run patch --root "$d"
  if [ "$RC" -ne 0 ] && echo "$OUT" | grep -q 'VERSION is not x.y.z'; then pass; else fail "rc=$RC out=$OUT"; fi
done

t "a VERSION of 5.10.0 is accepted"
d=$(make_fixture 5.10.0); merge_pr "$d" 1 "seed change"; run patch --root "$d"
if [ "$RC" -eq 0 ] && [ "$(cat "$d/VERSION")" = "5.10.1" ]; then pass; else fail "rc=$RC out=$OUT"; fi

# snap <repo> → a checksum of the three files a release would write.
snap() { (cd "$1" && cat VERSION plugins/harness/.claude-plugin/plugin.json CHANGELOG.md | cksum); }

t "an empty release (no [Unreleased] bullets, no PR since the tag) is refused and writes nothing"
d=$(make_fixture 1.2.3); before=$(snap "$d")
run patch --root "$d"
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'nothing to release' && echo "$OUT" | grep -q 'v1.2.3' \
   && [ "$(snap "$d")" = "$before" ] && [ -z "$(git -C "$d" status --porcelain)" ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "an empty release with --dry-run is refused too and writes nothing"
d=$(make_fixture 1.2.3); before=$(snap "$d")
run patch --dry-run --root "$d"
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'nothing to release' && [ "$(snap "$d")" = "$before" ] \
   && [ -z "$(git -C "$d" status --porcelain)" ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "only [Unreleased] bullets and no PR is a valid release"
d=$(make_fixture 1.2.3)
printf '# Changelog\n\n## [Unreleased]\n\n- feat: only bullet\n\n## [1.2.3] — 2026-01-01\n\n- seed\n' > "$d/CHANGELOG.md"
git -C "$d" commit -q -am cl
run patch --root "$d"
sec=$(sed -n '/^## \[1.2.4\]/,/^## \[1.2.3\]/p' "$d/CHANGELOG.md")
if [ "$RC" -eq 0 ] && printf '%s\n' "$sec" | grep -qx -- '- feat: only bullet'; then pass; else fail "rc=$RC out=$OUT $(cat "$d/CHANGELOG.md")"; fi

t "only a merged PR and an empty [Unreleased] is a valid release"
d=$(make_fixture 1.2.3)
merge_pr "$d" 30 "feat: only pr"
run patch --root "$d"
if [ "$RC" -eq 0 ] && grep -qx -- '- feat: only pr (PR #30)' "$d/CHANGELOG.md"; then pass; else fail "rc=$RC out=$OUT"; fi

t "with no tag the empty-release message says since the start"
d=$(make_fixture 1.2.3); git -C "$d" tag -d v1.2.3 >/dev/null
run patch --root "$d"
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'since the start'; then pass; else fail "rc=$RC out=$OUT"; fi

# squash_pr <repo> <subject> → a plain one-parent commit on main, as a squash or rebase leaves.
squash_pr() {
  echo "$2" > "$1/sq$RANDOM.txt"; git -C "$1" add -A; git -C "$1" commit -q -m "$2"
}

t "squash-style and merge-commit PRs both appear, in first-parent order"
d=$(make_fixture 1.2.3)
squash_pr "$d" "feat: x (#12)"
merge_pr "$d" 13 "fix: via merge commit"
run patch --root "$d"
a=$(grep -n -- '- feat: x (PR #12)' "$d/CHANGELOG.md" | cut -d: -f1); b=$(grep -n -- '- fix: via merge commit (PR #13)' "$d/CHANGELOG.md" | cut -d: -f1)
if [ "$RC" -eq 0 ] && [ -n "$a" ] && [ -n "$b" ] && [ "$a" -lt "$b" ] && ! grep -q '(#12)' "$d/CHANGELOG.md"; then pass; else fail "rc=$RC $(cat "$d/CHANGELOG.md")"; fi

t "a branch commit ending (#N) that came in through a merge commit makes no bullet"
d=$(make_fixture 1.2.3)
git -C "$d" checkout -q -b side
echo s > "$d/side.txt"; git -C "$d" add -A; git -C "$d" commit -q -m "fix: y (#99)"
git -C "$d" checkout -q main
git -C "$d" merge -q --no-ff -m "Merge pull request #20 from o/side" -m "fix: the titled one" side
run patch --root "$d"
if [ "$RC" -eq 0 ] && grep -q 'the titled one (PR #20)' "$d/CHANGELOG.md" && ! grep -q '#99' "$d/CHANGELOG.md"; then pass; else fail "rc=$RC $(cat "$d/CHANGELOG.md")"; fi

t "a squash subject chore(release) or chore(bookkeeping) is skipped"
d=$(make_fixture 1.2.3)
squash_pr "$d" "chore(release): v1.2.3 (#14)"
squash_pr "$d" "chore(bookkeeping): record PR #14 (#15)"
squash_pr "$d" "feat: kept (#16)"
run patch --root "$d"
if [ "$RC" -eq 0 ] && grep -q 'kept (PR #16)' "$d/CHANGELOG.md" && ! grep -q 'PR #14)\|PR #15)' "$d/CHANGELOG.md"; then pass; else fail "rc=$RC $(cat "$d/CHANGELOG.md")"; fi

finish
