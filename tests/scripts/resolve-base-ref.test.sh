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

# ── 6. THE REGRESSION GUARD: no declared base must NOT guess ─────────────────
t "no declared base and no upstream exits nonzero without guessing a branch name"
d=$(make_repo)   # `main` exists and is tempting — the script must still refuse
out=$(run_in "$d"); rc=$?
if [ "$rc" -ne 0 ] && echo "$out" | grep -q "no base ref declared"; then pass
else fail "rc=$rc out='$out' (want nonzero + 'no base ref declared'; guessing 'main' is the bug)"; fi

# ── 7. Nothing is printed to stdout on failure — callers must not diff a reason ─
t "failure writes the reason to stderr, leaving stdout empty"
d=$(make_repo)
out=$( cd "$d" && env -u VERIFY_ROWS_BASE -u GITHUB_BASE_REF bash "$SCRIPT" 2>/dev/null )
if [ -z "$out" ]; then pass; else fail "stdout was '$out', expected empty (a caller would diff against it)"; fi

# ── 8. An unresolvable explicit override is reported with its source ─────────
t "unresolvable VERIFY_ROWS_BASE names the ref and where it came from"
d=$(make_repo)
out=$(run_in "$d" VERIFY_ROWS_BASE=no/such/ref); rc=$?
if [ "$rc" -ne 0 ] && echo "$out" | grep -q "no/such/ref" && echo "$out" | grep -q "VERIFY_ROWS_BASE"; then pass
else fail "rc=$rc out='$out' (want nonzero naming both the ref and VERIFY_ROWS_BASE)"; fi

finish
