#!/bin/bash
# Unit tests for scripts/release-guard.sh: it refuses while a release PR or a release/ branch is
# open, and fails closed when gh fails. Each case uses a throwaway repo with a bare repo as
# `origin` and a stub gh that prints canned output; no network.
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

# run <repo> [args...] → OUT, RC. Runs from the repo dir.
run() {
  local d="$1"; shift
  OUT=$(cd "$d" && GH_BIN="$STUB_DIR/gh" GH_LOG="$d.gh.log" GH_OUT_FILE="$d.out" GH_RC="${GH_RC:-0}" bash "$SCRIPT" "$@" 2>&1); RC=$?
}

t "no release PR and no release branch: exit 0"
d=$(make_fixture)
run "$d"
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "asks gh for open PRs only"
if grep -q -- 'pr list --state open' "$d.gh.log"; then pass; else fail "calls: $(cat "$d.gh.log" 2>/dev/null)"; fi

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

t "a leftover release/ branch on origin with no PR: exit 1 and the output names the branch"
d=$(make_fixture)
git -C "$d" push -q origin main:refs/heads/release/v1.2.4 2>/dev/null
run "$d"
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'release/v1.2.4'; then pass
else fail "rc=$RC out=$OUT"; fi

t "an open PR with a non-release head and no release branch: exit 0"
d=$(make_fixture)
git -C "$d" push -q origin main:refs/heads/feat/x 2>/dev/null
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

t "--root works from another directory"
d=$(make_fixture)
printf '#9 release/v2.0.0\n' > "$d.out"
OUT=$(cd "$STUB_DIR" && GH_BIN="$STUB_DIR/gh" GH_LOG="$d.gh.log" GH_OUT_FILE="$d.out" bash "$SCRIPT" --root "$d" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q '#9'; then pass; else fail "rc=$RC out=$OUT"; fi

t "an unknown argument exits 2"
run "$d" --nope
if [ "$RC" -eq 2 ]; then pass; else fail "rc=$RC out=$OUT"; fi

finish
