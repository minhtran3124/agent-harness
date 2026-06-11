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
write_summary "$r" "normal" "true"; commit_run "$r"
assert_rc 1

t "diff touches hooks/ + high-risk SUMMARY with a real ### Verify row → PASS (exit 0)"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
write_summary "$r" "high-risk" "true"; commit_run "$r"
assert_rc 0

t "sole high-risk SUMMARY whose ### Verify MISMATCHES (claims 0, exits 1) → BLOCK (exit 1)"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
write_summary "$r" "high-risk" "false"; commit_run "$r"
assert_rc 1

t "≥1 high-risk SUMMARY passes while another fails → PASS (exit 0); the failure is a non-blocking warning"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
write_summary "$r" "high-risk" "true"  "good"
write_summary "$r" "high-risk" "false" "bad"
commit_run "$r"
assert_rc 0

t "diff touches ONLY tests/hooks/ (false-positive class) → PASS (exit 0)"
r=$(mkrepo); mkdir -p "$r/tests/hooks"; echo 'x' > "$r/tests/hooks/foo.test.sh"; commit_run "$r"
assert_rc 0

t "diff touches templates/ (the ^templates/ extension) with NO SUMMARY → BLOCK (exit 1)"
r=$(mkrepo); mkdir -p "$r/templates"; echo 'x' > "$r/templates/FOO.template.md"; commit_run "$r"
assert_rc 1

finish
