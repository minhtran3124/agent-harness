#!/bin/bash
# Unit tests for scripts/resolve-base-ref.sh.
#
# The bug these pin: run-tests.sh used to hardcode `origin/main` as the base for its
# changed-files scope. That ref resolved neither locally (this repo's only remote is
# `github`) nor in CI (the `test` job checked out shallow), so the verify-row lint
# skipped on 100% of runs since the day it shipped while still reporting green.
#
# Two properties matter and both are asserted here:
#   1. a declared base is honoured, in priority order;
#   2. an undeclared or unresolvable base FAILS LOUDLY instead of falling back to a
#      guess. Guessing `main` when a PR targets another integration branch widened the
#      diff from this branch's own files to 36, un-grandfathering 7 pre-existing
#      violations in shipped specs — wrong-and-wide is worse than skipping.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/resolve-base-ref.sh"

# A throwaway repo with two commits on `main` and a detached feature branch, so
# @{upstream} is genuinely unset unless a test sets it.
make_repo() {
  local d
  d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main
  git -C "$d" config user.email t@t.t
  git -C "$d" config user.name t
  echo seed > "$d/f"
  git -C "$d" add f
  git -C "$d" commit -qm seed
  git -C "$d" checkout -q -b feature
  echo more > "$d/f"
  git -C "$d" commit -qam more
  echo "$d"
}

# Run the script inside repo $1 with a clean env — the ambient shell may itself be
# running under GitHub Actions, which would leak GITHUB_BASE_REF into every case.
run_in() {
  local d="$1"; shift
  ( cd "$d" && env -u VERIFY_ROWS_BASE -u GITHUB_BASE_REF "$@" bash "$SCRIPT" 2>&1 )
}

# ── 1. VERIFY_ROWS_BASE wins and is printed verbatim ─────────────────────────
t "VERIFY_ROWS_BASE is honoured when it resolves"
d=$(make_repo)
out=$(run_in "$d" VERIFY_ROWS_BASE=main); rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "main" ]; then pass; else fail "rc=$rc out='$out' (want rc=0 out='main')"; fi

# ── 2. VERIFY_ROWS_BASE outranks GITHUB_BASE_REF ─────────────────────────────
t "VERIFY_ROWS_BASE takes priority over GITHUB_BASE_REF"
d=$(make_repo)
git -C "$d" branch -q other main
out=$(run_in "$d" VERIFY_ROWS_BASE=other GITHUB_BASE_REF=main); rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "other" ]; then pass; else fail "rc=$rc out='$out' (want 'other')"; fi

# ── 3. GITHUB_BASE_REF is read as origin/<ref> — the CI pull-request shape ───
t "GITHUB_BASE_REF resolves as origin/<ref>"
d=$(make_repo)
# Simulate what actions/checkout leaves behind: a remote-tracking ref for the PR base.
git -C "$d" update-ref refs/remotes/origin/main "$(git -C "$d" rev-parse main)"
out=$(run_in "$d" GITHUB_BASE_REF=main); rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "origin/main" ]; then pass; else fail "rc=$rc out='$out' (want 'origin/main')"; fi

# ── 4. THE ORIGINAL BUG: GITHUB_BASE_REF set but the ref absent (shallow CI) ──
t "GITHUB_BASE_REF whose origin/<ref> is missing fails loudly, not silently"
d=$(make_repo)   # deliberately NO refs/remotes/origin/main — the shallow-checkout case
out=$(run_in "$d" GITHUB_BASE_REF=main); rc=$?
if [ "$rc" -ne 0 ] && echo "$out" | grep -q "does not resolve"; then pass
else fail "rc=$rc out='$out' (want nonzero + 'does not resolve')"; fi

# ── 5. Branch upstream is used when nothing is declared ──────────────────────
t "branch upstream is used when no env var is set"
d=$(make_repo)
git -C "$d" branch -q --set-upstream-to=main feature
out=$(run_in "$d"); rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "main" ]; then pass; else fail "rc=$rc out='$out' (want 'main')"; fi

# ── 5b. THE REAL-WORLD UPSTREAM SHAPE: `git push -u` tracks the branch's OWN remote copy ──
# Case 5 above sets upstream to a DIFFERENT branch, which `git push -u` never produces. In
# this repo every tracked branch maps to github/<its-own-name>. Diffing against that yields
# only unpushed edits — nothing once pushed — and the caller then prints "compared and found
# nothing", the very skip-looks-like-pass ambiguity this script exists to remove. Refusing is
# the only honest answer, so this case pins the refusal.
t "an upstream tracking this same branch is skipped, and the real base is derived instead"
d=$(make_repo)
# `git remote add` is required: without a configured remote git refuses to record the
# upstream at all, and the case would silently degrade into the "no upstream" path — a
# green test that never reaches the guard it is meant to pin.
git -C "$d" remote add github /dev/null
git -C "$d" update-ref refs/remotes/github/feature "$(git -C "$d" rev-parse feature)"
git -C "$d" branch -q --set-upstream-to=github/feature feature
out=$(run_in "$d"); rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "main" ]; then pass
else fail "rc=$rc out='$out' (want 'main': a self-tracking upstream is not a base, but the branch still has one)"; fi

# ── TIER 4: derive the base from history rather than guessing a name ─────────
# A name chain (`origin/main` → `github/main` → `main`) picks `main` on a branch cut from
# another integration branch — a ref that is not even an ancestor of HEAD. Ordering
# candidates by NAME is the bug; the base is a fact about history.
t "the nearest ancestor is derived when nothing is declared"
d=$(make_repo)
out=$(run_in "$d"); rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "main" ]; then pass; else fail "rc=$rc out='$out' (want 'main')"; fi

t "a ref that is NOT an ancestor of HEAD is never chosen, however tempting its name"
d=$(make_repo)
# `release` diverges: it holds a commit HEAD does not, exactly like `main` relative to a
# branch cut from `simplify`. It must be disqualified outright, not merely outranked.
git -C "$d" checkout -q -b release main
echo diverged > "$d/g"; git -C "$d" add g; git -C "$d" commit -qm diverge
git -C "$d" checkout -q feature
out=$(run_in "$d"); rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "main" ]; then pass
else fail "rc=$rc out='$out' (want 'main'; 'release' is not an ancestor and must be excluded)"; fi

t "the branch's own remote copy is excluded even though it is an ancestor at distance 0"
d=$(make_repo)
git -C "$d" remote add github /dev/null
# After `git push`, <remote>/<branch> equals HEAD: an ancestor, distance 0, so it would win
# every ranking and produce an empty diff — the self-comparison this script exists to stop.
git -C "$d" update-ref refs/remotes/github/feature "$(git -C "$d" rev-parse feature)"
out=$(run_in "$d"); rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "main" ]; then pass
else fail "rc=$rc out='$out' (want 'main'; picking github/feature diffs the branch against itself)"; fi

t "a branch name containing slashes is still recognised as its own remote copy"
d=$(make_repo)
git -C "$d" checkout -q -b fix/nested-name   # cut from `feature`, so `feature` is its base
git -C "$d" remote add github /dev/null
git -C "$d" update-ref refs/remotes/github/fix/nested-name "$(git -C "$d" rev-parse HEAD)"
out=$(run_in "$d"); rc=$?
# Suffix-stripping (`${ref##*/}`) yields "nested-name" here, not "fix/nested-name", so a
# naive exclusion misses the self copy — which sits at distance 0 and would win, giving an
# empty diff. Expect `feature`: the real base of a branch cut from `feature`.
if [ "$rc" -eq 0 ] && [ "$out" = "feature" ]; then pass
else fail "rc=$rc out='$out' (want 'feature'; 'github/fix/nested-name' means the self-exclusion missed a slashed name)"; fi

# ── 5c. A non-commit object must not pass as a base ──────────────────────────
# `git rev-parse --verify <blob>` succeeds, but `git diff <blob> -- <pathspec>` dies with a
# fatal the caller swallows, surfacing as "compared and found nothing" instead of "bad base".
t "an object that is not a commit (blob sha) is refused"
d=$(make_repo)
blob=$(git -C "$d" rev-parse feature:f)
out=$(run_in "$d" VERIFY_ROWS_BASE="$blob"); rc=$?
if [ "$rc" -ne 0 ] && echo "$out" | grep -q "does not resolve to a commit"; then pass
else fail "rc=$rc out='$out' (want nonzero + 'does not resolve to a commit')"; fi

# ── 6. THE REGRESSION GUARD: with no candidate at all, refuse — never invent one ──
# `make_orphan` has no ref that is an ancestor of HEAD, so derivation legitimately finds
# nothing. That must be a loud refusal, not a fallback to whatever branch name exists.
make_orphan() {
  local d
  d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main
  git -C "$d" config user.email t@t.t
  git -C "$d" config user.name t
  echo seed > "$d/f"; git -C "$d" add f; git -C "$d" commit -qm seed
  # An orphan branch shares no history with main, so main is not an ancestor of HEAD.
  git -C "$d" checkout -q --orphan solo
  git -C "$d" rm -rq --cached . 2>/dev/null || true
  echo alone > "$d/h"; git -C "$d" add h; git -C "$d" commit -qm alone
  echo "$d"
}

t "no declared base and no ancestor candidate exits nonzero instead of inventing one"
d=$(make_orphan)   # `main` exists and is tempting — but it is not an ancestor
out=$(run_in "$d"); rc=$?
if [ "$rc" -ne 0 ] && echo "$out" | grep -q "could be declared or derived"; then pass
else fail "rc=$rc out='$out' (want nonzero; picking the unrelated 'main' is the bug)"; fi

# ── 7. Nothing is printed to stdout on failure — callers must not diff a reason ─
t "failure writes the reason to stderr, leaving stdout empty"
d=$(make_orphan)
out=$( cd "$d" && env -u VERIFY_ROWS_BASE -u GITHUB_BASE_REF bash "$SCRIPT" 2>/dev/null )
if [ -z "$out" ]; then pass; else fail "stdout was '$out', expected empty (a caller would diff against it)"; fi

# ── 8. An unresolvable explicit override is reported with its source ─────────
t "unresolvable VERIFY_ROWS_BASE names the ref and where it came from"
d=$(make_repo)
out=$(run_in "$d" VERIFY_ROWS_BASE=no/such/ref); rc=$?
if [ "$rc" -ne 0 ] && echo "$out" | grep -q "no/such/ref" && echo "$out" | grep -q "VERIFY_ROWS_BASE"; then pass
else fail "rc=$rc out='$out' (want nonzero naming both the ref and VERIFY_ROWS_BASE)"; fi

finish
