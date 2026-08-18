#!/bin/bash
# Contract tests for scripts/ci-strict-gate.sh — the strict-in-CI gate.
# When a PR diff touches hard-gate paths it must carry a high-risk SUMMARY with
# machine-verified proof; diffs that miss hard-gate paths (incl. the tests/hooks/
# false-positive class) pass. Fixtures are throwaway git repos with a base commit
# and a divergent HEAD; the gate is run with BASE = the base commit sha.
source "$(dirname "$0")/../lib.sh"

GATE="$ROOT/scripts/ci-strict-gate.sh"
VERIFY_PY="$ROOT/scripts/verify_summary.py"

# mkrepo → echoes a fresh repo dir with verify_summary.py available and one base commit
mkrepo() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main 2>/dev/null || git -C "$d" init -q
  git -C "$d" config user.email t@t; git -C "$d" config user.name t
  mkdir -p "$d/scripts"; cp "$VERIFY_PY" "$d/scripts/"
  echo "seed" > "$d/README.md"
  git -C "$d" add -A >/dev/null 2>&1; git -C "$d" commit -qm base
  echo "$d"
}

# write_summary <repo> <lane> <command-or-empty> [slug=x] — writes specs/<slug>/SUMMARY.md
write_summary() {
  local slug="${4:-x}"
  mkdir -p "$1/specs/$slug"
  {
    echo "# $slug"
    echo "Lane: $2"
    echo ""
    echo "### Verify"
    echo ""
    echo "| Check | Command | Exit | Notes |"
    echo "| --- | --- | --- | --- |"
    [ -n "$3" ] && echo "| ok | $3 | 0 | n |"
  } > "$1/specs/$slug/SUMMARY.md"
}

# commit_run <repo> — commit working changes and run the gate vs the base commit
commit_run() {
  local r="$1" base
  base=$(git -C "$r" rev-parse HEAD~0)  # base is still HEAD before this commit…
  git -C "$r" add -A >/dev/null 2>&1
  git -C "$r" commit -qm change
  OUT=$(cd "$r" && bash "$GATE" "$base" 2>&1); RC=$?
}

t "clean diff (no hard-gate paths) → pass silently (exit 0)"
r=$(mkrepo); echo "more" >> "$r/README.md"; commit_run "$r"
assert_rc 0

t "diff touches hooks/ with NO changed SUMMARY → BLOCK (exit 1)"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"; commit_run "$r"
assert_rc 1

t "diff touches hooks/ + SUMMARY but Lane is not high-risk → BLOCK (exit 1)"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
write_summary "$r" "normal" "test 1 = 1"; commit_run "$r"
assert_rc 1

t "diff touches hooks/ + high-risk SUMMARY with a real ### Verify row → PASS (exit 0)"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
write_summary "$r" "high-risk" "test 1 = 1"; commit_run "$r"
assert_rc 0

t "high-risk SUMMARY whose only Verify row is trivial (true) → BLOCK (DR-6 forgery)"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
write_summary "$r" "high-risk" "true"; commit_run "$r"
assert_rc 1

t "sole high-risk SUMMARY whose ### Verify MISMATCHES (claims 0, exits 1) → BLOCK (exit 1)"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
write_summary "$r" "high-risk" "false"; commit_run "$r"
assert_rc 1

t "≥1 high-risk SUMMARY passes while another fails → PASS (exit 0); the failure is a non-blocking warning"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
write_summary "$r" "high-risk" "test 1 = 1"  "good"
write_summary "$r" "high-risk" "false" "bad"
commit_run "$r"
assert_rc 0

t "diff touches ONLY tests/hooks/ (false-positive class) → PASS (exit 0)"
r=$(mkrepo); mkdir -p "$r/tests/hooks"; echo 'x' > "$r/tests/hooks/foo.test.sh"; commit_run "$r"
assert_rc 0

t "diff touches templates/ (the ^templates/ extension) with NO SUMMARY → BLOCK (exit 1)"
r=$(mkrepo); mkdir -p "$r/templates"; echo 'x' > "$r/templates/FOO.template.md"; commit_run "$r"
assert_rc 1

# ── scripts/ WARN tier ────────────────────────────────────────────────────────
# scripts/ holds the gate logic itself (verify_summary.py decides what every other
# gate accepts), so it is gated — but warn-first, because 9 of the last 80 PRs
# would have blocked on it. REQUIRE_SCRIPTS_PROOF=1 promotes warn → block.

t "diff touches scripts/ with NO SUMMARY → WARN, not block (exit 0)"
r=$(mkrepo); echo '# edit' >> "$r/scripts/verify_summary.py"; commit_run "$r"
assert_rc 0

t "the scripts/ warn tier still SAYS what is missing (a silent warn is no gate)"
r=$(mkrepo); echo '# edit' >> "$r/scripts/verify_summary.py"; commit_run "$r"
assert_rc_contains 0 "WARN-ONLY"

t "scripts/ + REQUIRE_SCRIPTS_PROOF=1 and no SUMMARY → BLOCK (exit 1)"
r=$(mkrepo); echo '# edit' >> "$r/scripts/verify_summary.py"
base=$(git -C "$r" rev-parse HEAD)
git -C "$r" add -A >/dev/null 2>&1; git -C "$r" commit -qm change
OUT=$(cd "$r" && REQUIRE_SCRIPTS_PROOF=1 bash "$GATE" "$base" 2>&1); RC=$?
assert_rc 1

t "scripts/ + a real high-risk SUMMARY → PASS (exit 0)"
r=$(mkrepo); echo '# edit' >> "$r/scripts/verify_summary.py"
write_summary "$r" "high-risk" "test 1 = 1"; commit_run "$r"
assert_rc 0

t "diff touches ONLY scripts/test_*.py (excluded false-positive class) → PASS silently (exit 0)"
r=$(mkrepo); echo 'x' > "$r/scripts/test_thing.py"; commit_run "$r"
assert_silent_ok

t "scripts/test_*.py stays excluded even under REQUIRE_SCRIPTS_PROOF=1"
r=$(mkrepo); echo 'x' > "$r/scripts/test_thing.py"
base=$(git -C "$r" rev-parse HEAD)
git -C "$r" add -A >/dev/null 2>&1; git -C "$r" commit -qm change
OUT=$(cd "$r" && REQUIRE_SCRIPTS_PROOF=1 bash "$GATE" "$base" 2>&1); RC=$?
assert_rc 0

t "a test-only scripts/ edit ALONGSIDE a real one is still gated (exclusion is per-file, not per-diff)"
r=$(mkrepo); echo 'x' > "$r/scripts/test_thing.py"; echo '# edit' >> "$r/scripts/verify_summary.py"
commit_run "$r"
assert_rc_contains 0 "WARN-ONLY"

t "hooks/ keeps BLOCKING even while scripts/ is warn-tier (tiers do not leak)"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
echo '# edit' >> "$r/scripts/verify_summary.py"; commit_run "$r"
assert_rc 1

# ── An unresolvable EXPLICIT base must be a hard error, not a silent pass ─────
# Every case above passes a valid base sha, so until now the argument path had no
# coverage at all — and it is the ONLY path CI takes (harness-ci.yml passes
# `origin/${{ github.base_ref }}`). With a bad base, `git diff ... 2>/dev/null || true`
# swallows the fatal, DIFF is empty, and the gate exits 0 having inspected nothing:
# a STRICT gate reporting success because it could not run. Measured before the fix:
# `bash scripts/ci-strict-gate.sh no/such/ref` → exit 0, zero output.
t "an explicit base ref that does not resolve is refused (exit 1), not silently passed"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
git -C "$r" add -A >/dev/null 2>&1; git -C "$r" commit -qm change
OUT=$(cd "$r" && bash "$GATE" no/such/ref 2>&1); RC=$?
assert_rc_contains 1 "does not resolve to a commit"

t "a base that resolves to a non-commit object (blob) is refused too"
r=$(mkrepo); echo "more" >> "$r/README.md"
git -C "$r" add -A >/dev/null 2>&1; git -C "$r" commit -qm change
blob=$(git -C "$r" rev-parse HEAD:README.md)
OUT=$(cd "$r" && bash "$GATE" "$blob" 2>&1); RC=$?
assert_rc_contains 1 "does not resolve to a commit"

finish
