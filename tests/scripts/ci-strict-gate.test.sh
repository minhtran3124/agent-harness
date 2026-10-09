#!/bin/bash
# Contract tests for scripts/ci-strict-gate.sh — the strict-in-CI gate.
# When a PR diff touches hard-gate paths it must carry a high-risk SUMMARY with
# machine-verified proof; diffs that miss hard-gate paths (incl. the tests/hooks/
# false-positive class) pass. Fixtures are throwaway git repos with a base commit
# and a divergent HEAD; the gate is run with BASE = the base commit sha.
source "$(dirname "$0")/../lib.sh"

GATE="$ROOT/scripts/ci-strict-gate.sh"
VERIFY_PY="$ROOT/scripts/verify_summary.py"
OQ_PY="$ROOT/scripts/check_open_questions.py"

# mkrepo → echoes a fresh repo dir with verify_summary.py and check_open_questions.py
# available and one base commit
mkrepo() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main 2>/dev/null || git -C "$d" init -q
  git -C "$d" config user.email t@t; git -C "$d" config user.name t
  mkdir -p "$d/scripts"; cp "$VERIFY_PY" "$OQ_PY" "$d/scripts/"
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

# commit_run <repo> [VAR=val ...] — commit working changes and run the gate vs the base commit
commit_run() {
  local r="$1" base
  base=$(git -C "$r" rev-parse HEAD~0)  # base is still HEAD before this commit…
  git -C "$r" add -A >/dev/null 2>&1
  git -C "$r" commit -qm change
  OUT=$(cd "$r" && env "${@:2}" bash "$GATE" "$base" 2>&1); RC=$?
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

# ── Shipping section: open-question check on a phase that ships in this PR ────
# A specs-only PR that flips a PLAN.md to `status: shipped` never reaches the tier
# logic (it takes the early exit 0), so the open-question check runs before it. The
# register sits in a parent spec and closes at the child phase's slug.

# write_register <repo> — specs/p/QUESTIONS.md with open OQ-1 closing at p-phase-1
write_register() {
  mkdir -p "$1/specs/p"
  printf '%s\n' '# Open questions' '## OQ-1' '- raised-by: p' '- closes-at: p-phase-1' \
    '- decided-by: owner' '- default-until-closed: keep current behaviour' '- status: open' \
    > "$1/specs/p/QUESTIONS.md"
}

# write_plan <repo> <status> — specs/p-phase-1/PLAN.md. The status line carries a trailing
# space and every line a CRLF ending, which the frontmatter read must tolerate.
write_plan() {
  mkdir -p "$1/specs/p-phase-1"
  printf -- '---\r\ntitle: p phase 1\r\nstatus: %s \r\n---\r\n# Plan\r\n' "$2" \
    > "$1/specs/p-phase-1/PLAN.md"
}

# base_commit <repo> — commit the working tree, which becomes the base commit_run diffs against
base_commit() { git -C "$1" add -A >/dev/null 2>&1; git -C "$1" commit -qm base2; }

t "(a) specs-only branch ships a phase with an open question → finding printed, exit 0"
r=$(mkrepo); write_register "$r"; base_commit "$r"
write_plan "$r" shipped; commit_run "$r"
assert_rc_contains 0 "OQ-1"

t "(b) case (a) under REQUIRE_QUESTIONS_CLOSED=1 → exit 1"
r=$(mkrepo); write_register "$r"; base_commit "$r"
write_plan "$r" shipped; commit_run "$r" REQUIRE_QUESTIONS_CLOSED=1
assert_rc_contains 1 "OQ-1"

t "(c) plan already shipped at the base, branch only appends a Status Log line → no check, exit 0"
r=$(mkrepo); write_register "$r"; write_plan "$r" shipped; base_commit "$r"
printf -- '- 2026-10-09 status log append\r\n' >> "$r/specs/p-phase-1/PLAN.md"; commit_run "$r"
assert_rc_not_contains 0 "OQ-1"

t "(c2) plan moves from in-progress at the base to shipped on the branch → checked"
r=$(mkrepo); write_register "$r"; write_plan "$r" in-progress; base_commit "$r"
write_plan "$r" shipped; commit_run "$r"
assert_rc_contains 0 "OQ-1"

t "(d) branch touches hooks/ and ships a phase with no open question and no SUMMARY → BLOCK (exit 1)"
r=$(mkrepo); mkdir -p "$r/hooks"; echo '#!/bin/bash' > "$r/hooks/foo.sh"
write_plan "$r" shipped; commit_run "$r"
assert_rc 1

t "(e) case (a) with the check script absent → skip message, exit 0"
r=$(mkrepo); write_register "$r"; rm "$r/scripts/check_open_questions.py"; base_commit "$r"
write_plan "$r" shipped; commit_run "$r"
assert_rc_contains 0 "open-question check skipped: scripts/check_open_questions.py not found"

t "(e) case (a) with the check script absent, under REQUIRE_QUESTIONS_CLOSED=1 → exit 1"
r=$(mkrepo); write_register "$r"; rm "$r/scripts/check_open_questions.py"; base_commit "$r"
write_plan "$r" shipped; commit_run "$r" REQUIRE_QUESTIONS_CLOSED=1
assert_rc_contains 1 "open-question check skipped"

# big_body <repo> — append ~1 MB of plan body after the frontmatter. The frontmatter read
# must consume all of its input: an awk that exits at the closing `---` leaves `git show`
# writing into a closed pipe, and under pipefail the SIGPIPE (141) reads as "not shipped".
big_body() {
  local line="filler body line of a long plan, kept long to grow the blob quickly........"
  local i chunk=""
  for i in $(seq 1 100); do chunk="$chunk$line"$'\n'; done
  for i in $(seq 1 130); do printf '%s' "$chunk"; done >> "$1/specs/p-phase-1/PLAN.md"
}

t "(f) shipping a ~1 MB PLAN.md with an open question → finding printed (no SIGPIPE skip)"
r=$(mkrepo); write_register "$r"; base_commit "$r"
write_plan "$r" shipped; big_body "$r"; commit_run "$r"
assert_rc_contains 0 "OQ-1"

t "(f) the ~1 MB shipping PLAN.md under REQUIRE_QUESTIONS_CLOSED=1 → exit 1"
r=$(mkrepo); write_register "$r"; base_commit "$r"
write_plan "$r" shipped; big_body "$r"; commit_run "$r" REQUIRE_QUESTIONS_CLOSED=1
assert_rc_contains 1 "OQ-1"

t "(f) a ~1 MB PLAN.md already shipped at the base, appended on the branch → no check"
r=$(mkrepo); write_register "$r"; write_plan "$r" shipped; big_body "$r"; base_commit "$r"
printf -- '- 2026-10-09 status log append\r\n' >> "$r/specs/p-phase-1/PLAN.md"; commit_run "$r"
assert_rc_not_contains 0 "OQ-1"

# broken_check <repo> <python-body> — replace the copied check script with one that fails
broken_check() { printf '%s\n' "$2" > "$1/scripts/check_open_questions.py"; }

t "(g) the check script exits 3 → error named on stderr, exit 0 in warn mode"
r=$(mkrepo); write_register "$r"; broken_check "$r" 'raise SystemExit(3)'; base_commit "$r"
write_plan "$r" shipped; commit_run "$r"
assert_rc_contains 0 "open-question check errored for p-phase-1 (exit 3)"

t "(g) the check script exits 3 under REQUIRE_QUESTIONS_CLOSED=1 → exit 1, BLOCKED names the error"
r=$(mkrepo); write_register "$r"; broken_check "$r" 'raise SystemExit(3)'; base_commit "$r"
write_plan "$r" shipped; commit_run "$r" REQUIRE_QUESTIONS_CLOSED=1
assert_rc_contains 1 "BLOCKED — the open-question check errored"

t "(g) the check script crashes (exit 1) in warn mode → reported as an error, exit 0"
r=$(mkrepo); write_register "$r"; broken_check "$r" 'raise RuntimeError("boom")'; base_commit "$r"
write_plan "$r" shipped; commit_run "$r"
assert_rc_contains 0 "open-question check errored for p-phase-1 (exit 1)"

t "(g) the missing-script block names the missing script, not open questions"
r=$(mkrepo); write_register "$r"; rm "$r/scripts/check_open_questions.py"; base_commit "$r"
write_plan "$r" shipped; commit_run "$r" REQUIRE_QUESTIONS_CLOSED=1
assert_rc_contains 1 "BLOCKED — scripts/check_open_questions.py not found"

t "(h) status: Shipped (capitalised) counts as shipped → checked"
r=$(mkrepo); write_register "$r"; base_commit "$r"
write_plan "$r" Shipped; commit_run "$r"
assert_rc_contains 0 "OQ-1"

t "(i) a non-ASCII slug directory shipping with an open question → finding printed"
r=$(mkrepo); mkdir -p "$r/specs/p" "$r/specs/café-phase"
printf '%s\n' '# Open questions' '## OQ-1' '- raised-by: p' '- closes-at: café-phase' \
  '- decided-by: owner' '- default-until-closed: keep current behaviour' '- status: open' \
  > "$r/specs/p/QUESTIONS.md"
base_commit "$r"
printf -- '---\nstatus: shipped\n---\n# Plan\n' > "$r/specs/café-phase/PLAN.md"; commit_run "$r"
assert_rc_contains 0 "café-phase ships in this diff"

# ── SC-history section: a failed Success Criterion whose goalpost moved ──────
# The base carries specs/s/PLAN.md with SC-1 expecting exit 0. A specs-only branch
# never reaches the tier logic, so the section runs before it, like the shipping one.

# write_sc_plan <repo> <expected> — specs/s/PLAN.md with one SC row
write_sc_plan() {
  mkdir -p "$1/specs/s"
  printf '%s\n' '# Plan' '' '| ID | Criterion | Check | Expected |' '| --- | --- | --- | --- |' \
    "| SC-1 | it works | \`test 1 = 1\` | $2 |" > "$1/specs/s/PLAN.md"
}

# write_sc_summary <repo> <exit> — specs/s/SUMMARY.md with one Verify row mapped to SC-1
write_sc_summary() {
  mkdir -p "$1/specs/s"
  printf '%s\n' '# s' 'Lane: high-risk' '' '### Verify' '' \
    '| Check | Command | Exit | Notes | Criterion |' '| --- | --- | --- | --- | --- |' \
    "| ok | test 1 = 1 | $2 | n | SC-1 |" > "$1/specs/s/SUMMARY.md"
}

# sc_goalpost_run <repo> [VAR=val ...] — on the branch, record SC-1 failing (exit 1), then
# move SC-1's Expected to exit 1 in a second commit, and run the gate vs the base
sc_goalpost_run() {
  local r="$1" base
  base=$(git -C "$r" rev-parse HEAD)
  write_sc_summary "$r" 1; git -C "$r" add -A >/dev/null 2>&1; git -C "$r" commit -qm fail
  write_sc_plan "$r" "exit 1"; git -C "$r" add -A >/dev/null 2>&1; git -C "$r" commit -qm move
  OUT=$(cd "$r" && env "${@:2}" bash "$GATE" "$base" 2>&1); RC=$?
}

t "(j) specs-only branch moves a failed SC's Expected → SC-GOALPOST printed, exit 0"
r=$(mkrepo); write_sc_plan "$r" "exit 0"; base_commit "$r"
sc_goalpost_run "$r"
assert_rc_contains 0 "SC-GOALPOST [SC-1]"

t "(k) case (j) under REQUIRE_SC_STABLE=1 → exit 1, BLOCKED names the changed SC"
r=$(mkrepo); write_sc_plan "$r" "exit 0"; base_commit "$r"
sc_goalpost_run "$r" REQUIRE_SC_STABLE=1
assert_rc_contains 1 "a failed Success Criterion was changed"

t "(l) SC-1's Expected changes with no failing row → no finding, exit 0"
r=$(mkrepo); write_sc_plan "$r" "exit 0"; base_commit "$r"
write_sc_plan "$r" "exit 1"; commit_run "$r" REQUIRE_SC_STABLE=1
assert_rc_not_contains 0 "SC-GOALPOST"

# broken_verify <repo> — replace the copied verify_summary.py with a stub that exits 2
broken_verify() { printf '%s\n' 'raise SystemExit(2)' > "$1/scripts/verify_summary.py"; }

t "(m) the sc-history check exits 2 → error named, exit 0 in warn mode"
r=$(mkrepo); write_sc_plan "$r" "exit 0"; broken_verify "$r"; base_commit "$r"
write_sc_plan "$r" "exit 1"; commit_run "$r"
assert_rc_contains 0 "sc-history check errored for s (exit 2)"

t "(m) the sc-history check exits 2 under REQUIRE_SC_STABLE=1 → exit 1, BLOCKED names the error"
r=$(mkrepo); write_sc_plan "$r" "exit 0"; broken_verify "$r"; base_commit "$r"
write_sc_plan "$r" "exit 1"; commit_run "$r" REQUIRE_SC_STABLE=1
assert_rc_contains 1 "BLOCKED — the sc-history check errored"

t "(n) REQUIRE_SC_STABLE=' 1' (surrounding whitespace) is read as 1, as verify_summary.py reads it"
r=$(mkrepo); write_sc_plan "$r" "exit 0"; base_commit "$r"
sc_goalpost_run "$r" "REQUIRE_SC_STABLE= 1"
assert_rc_contains 1 "a failed Success Criterion was changed"

# rename_spec_run <repo> [VAR=val ...] — on the branch, move specs/s to specs/t and run the gate
rename_spec_run() {
  local r="$1" base
  base=$(git -C "$r" rev-parse HEAD)
  git -C "$r" mv specs/s specs/t; git -C "$r" commit -qm rename
  OUT=$(cd "$r" && env "${@:2}" bash "$GATE" "$base" 2>&1); RC=$?
}
RENAME_LINE="sc-history: spec directory renamed s -> t; failure history before the rename is not followed"

t "(o) a branch renaming specs/s to specs/t → rename named, exit 0 in warn mode"
r=$(mkrepo); write_sc_plan "$r" "exit 0"; write_sc_summary "$r" 1; base_commit "$r"
rename_spec_run "$r"
assert_rc_contains 0 "$RENAME_LINE"

t "(o) the rename under REQUIRE_SC_STABLE=1 → exit 1, BLOCKED names the error"
r=$(mkrepo); write_sc_plan "$r" "exit 0"; write_sc_summary "$r" 1; base_commit "$r"
rename_spec_run "$r" REQUIRE_SC_STABLE=1
assert_rc_contains 1 "BLOCKED — the sc-history check errored"
case "$OUT" in *"$RENAME_LINE"*) pass ;; *) fail "rename line missing under REQUIRE: $OUT" ;; esac

# create_then_rename_run <repo> [VAR=val ...] — on the branch, create specs/s (PLAN + SUMMARY)
# in one commit and rename it to specs/t in a later one. The net base...HEAD diff shows only
# additions under specs/t, so the rename is visible only per commit.
create_then_rename_run() {
  local r="$1" base
  base=$(git -C "$r" rev-parse HEAD)
  write_sc_plan "$r" "exit 0"; write_sc_summary "$r" 1
  git -C "$r" add -A >/dev/null 2>&1; git -C "$r" commit -qm create
  git -C "$r" mv specs/s specs/t; git -C "$r" commit -qm rename
  OUT=$(cd "$r" && env "${@:2}" bash "$GATE" "$base" 2>&1); RC=$?
}

t "(p) a branch that creates specs/s and later renames it to specs/t → rename named, exit 0 in warn mode"
r=$(mkrepo); create_then_rename_run "$r"
assert_rc_contains 0 "$RENAME_LINE"

t "(p) the create-then-rename under REQUIRE_SC_STABLE=1 → exit 1, BLOCKED names the error"
r=$(mkrepo); create_then_rename_run "$r" REQUIRE_SC_STABLE=1
assert_rc_contains 1 "BLOCKED — the sc-history check errored"
case "$OUT" in *"$RENAME_LINE"*) pass ;; *) fail "rename line missing under REQUIRE: $OUT" ;; esac

finish
