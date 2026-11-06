#!/bin/bash
# Unit tests for scripts/release-guard.sh: it refuses while a release PR is open or a release/vX.Y.Z
# branch has no tag vX.Y.Z yet, and fails closed when gh or git ls-remote fails. A release is
# finished when its tag exists on origin, whatever merge method closed the PR. Each case uses a
# throwaway repo with a bare repo as `origin` and a stub gh that prints canned output; no network.
# The real gh applies the `-q` jq filter itself, so the stub prints what that filter would print:
# one "#<n> <branch>" line per open release PR, and nothing for a PR with another head.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/release-guard.sh"

# The stub logs its arguments to $GH_LOG, prints $GH_OUT_FILE, and exits with $GH_RC (default 0).
STUB_DIR=$(mktemp -d); _CLEANUP_DIRS+=("$STUB_DIR")
cat > "$STUB_DIR/gh" <<'STUB'
#!/bin/bash
echo "$*" >> "$GH_LOG"
[ -n "${GH_OUT_FILE:-}" ] && cat "$GH_OUT_FILE"
exit "${GH_RC:-0}"
STUB
chmod +x "$STUB_DIR/gh"

# make_fixture → echoes a repo dir; origin is <dir>.git; <dir>.out is the canned gh output.
make_fixture() {
  local d
  d=$(mktemp -d); _CLEANUP_DIRS+=("$d" "$d.git" "$d.out" "$d.gh.log")
  git init -q --bare "$d.git"
  git -C "$d" init -q -b main 2>/dev/null || git -C "$d" init -q
  git -C "$d" config user.email test@test
  git -C "$d" config user.name test
  echo x > "$d/f"
  git -C "$d" add -A && git -C "$d" commit -q -m init
  git -C "$d" remote add origin "$d.git"
  git -C "$d" push -q origin main 2>/dev/null
  : > "$d.out"
  echo "$d"
}

# push_branch <repo> <name> → a branch on origin that carries a commit main does not have, as the
# branch of a release PR closed by a squash or rebase leaves behind.
push_branch() {
  local b="side-$RANDOM"
  git -C "$1" checkout -q -b "$b"
  echo "$2" > "$1/b-$RANDOM.txt"; git -C "$1" add -A; git -C "$1" commit -q -m "work $2"
  git -C "$1" push -q origin "$b:refs/heads/$2" 2>/dev/null
  git -C "$1" checkout -q main
}

# push_tag <repo> <tag> → an annotated tag on origin, as release-tag.sh leaves it.
push_tag() {
  git -C "$1" tag -a "$2" -m "$2"
  git -C "$1" push -q origin "refs/tags/$2" 2>/dev/null
}

# run <repo> [args...] → OUT, RC. Runs from the repo dir.
run() {
  local d="$1"; shift
  OUT=$(cd "$d" && GH_BIN="$STUB_DIR/gh" GH_LOG="$d.gh.log" GH_OUT_FILE="$d.out" GH_RC="${GH_RC:-0}" bash "$SCRIPT" "$@" 2>&1); RC=$?
}

t "no release PR and no release branch: exit 0"
d=$(make_fixture)
run "$d"
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "asks gh for open PRs only, and for more than its default 30"
if grep -q -- 'pr list --state open' "$d.gh.log" && grep -q -- '--limit 200' "$d.gh.log"; then pass
else fail "calls: $(cat "$d.gh.log" 2>/dev/null)"; fi

t "an open PR with a release/ head: exit 1 and the output names the PR and its branch"
d=$(make_fixture)
printf '#601 release/v1.2.4\n' > "$d.out"
run "$d"
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q '#601' && printf '%s' "$OUT" | grep -q 'release/v1.2.4'; then pass
else fail "rc=$RC out=$OUT"; fi

t "every open release PR is named"
printf '#601 release/v1.2.4\n#602 release/v1.3.0\n' > "$d.out"
run "$d"
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q '#601' && printf '%s' "$OUT" | grep -q '#602' \
   && printf '%s' "$OUT" | grep -q 'release/v1.3.0'; then pass
else fail "rc=$RC out=$OUT"; fi

t "the message says how to recover"
if printf '%s' "$OUT" | grep -q 'git push origin --delete' && printf '%s' "$OUT" | grep -qi 'run the workflow again'; then pass
else fail "out=$OUT"; fi

t "a release/vX.Y.Z branch with no tag vX.Y.Z (an unfinished release) and no PR: exit 1, names the branch"
d=$(make_fixture)
push_branch "$d" release/v1.2.4
run "$d"
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'release/v1.2.4'; then pass
else fail "rc=$RC out=$OUT"; fi

t "a release branch whose tag exists on origin (a finished release) does not block"
d=$(make_fixture)
push_branch "$d" release/v1.2.3
push_tag "$d" v1.2.3
run "$d"
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a finished release is not judged by merge ancestry: a branch main does not contain, with its tag, does not block"
d=$(make_fixture)
push_branch "$d" release/v2.0.0
push_tag "$d" v2.0.0
git -C "$d" fetch -q origin 2>/dev/null
if git -C "$d" merge-base --is-ancestor "origin/release/v2.0.0" origin/main 2>/dev/null; then fail "fixture error: the branch is already in main"
else
  run "$d"
  if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi
fi

t "a finished and an unfinished release branch: only the unfinished one is named"
d=$(make_fixture)
push_branch "$d" release/v1.2.3
push_tag "$d" v1.2.3
push_branch "$d" release/v1.2.4
run "$d"
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'release/v1.2.4' && ! printf '%s' "$OUT" | grep -q 'release/v1.2.3'; then pass
else fail "rc=$RC out=$OUT"; fi

t "a release/ branch not named release/vX.Y.Z cannot be shown finished: exit 1"
d=$(make_fixture)
push_branch "$d" release/hotfix
run "$d"
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'release/hotfix'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a branch that only ends in release/... (docs/release/notes) is not a release branch: exit 0"
d=$(make_fixture)
push_branch "$d" docs/release/notes
run "$d"
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "an open PR with a non-release head and no release branch: exit 0"
d=$(make_fixture)
push_branch "$d" feat/x
: > "$d.out"   # gh's filter drops feat/x, so it prints nothing
run "$d"
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a gh that exits 1 fails closed: exit 2, never 0"
d=$(make_fixture)
GH_RC=1 run "$d"
if [ "$RC" -eq 2 ] && printf '%s' "$OUT" | grep -q 'release-guard'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a gh that prints a PR but then exits 1 still fails closed"
printf '#601 release/v1.2.4\n' > "$d.out"
GH_RC=1 run "$d"
if [ "$RC" -eq 2 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "an origin that cannot be listed fails closed: exit 2, never 0"
d=$(make_fixture)
git -C "$d" remote set-url origin "$d.does-not-exist.git"
run "$d"
if [ "$RC" -eq 2 ] && printf '%s' "$OUT" | grep -q 'release-guard'; then pass; else fail "rc=$RC out=$OUT"; fi

t "--root works from another directory"
d=$(make_fixture)
printf '#9 release/v2.0.0\n' > "$d.out"
OUT=$(cd "$STUB_DIR" && GH_BIN="$STUB_DIR/gh" GH_LOG="$d.gh.log" GH_OUT_FILE="$d.out" bash "$SCRIPT" --root "$d" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q '#9'; then pass; else fail "rc=$RC out=$OUT"; fi

t "an unknown argument exits 2"
run "$d" --nope
if [ "$RC" -eq 2 ]; then pass; else fail "rc=$RC out=$OUT"; fi

finish
