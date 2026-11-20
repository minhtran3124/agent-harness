#!/bin/bash
# plugins/harness/scripts/fleet-check.sh checks the end state of one ticket: receipt, report,
# acceptance-test commits, security receipt, repro (red on base, green on head) and suite. Every case
# builds its own throwaway git repo and evidence dir and uses tiny fake commands, so it is hermetic.
# shellcheck source=../lib.sh
source "$(dirname "$0")/../lib.sh"
FC="$ROOT/plugins/harness/scripts/fleet-check.sh"

if ! command -v jq >/dev/null 2>&1; then
  t "fleet-check needs jq"; skip "jq not installed"; finish
fi

gitc() { local r=$1; shift; git -C "$r" "$@"; }

# commit_file <repo> <path> <content> <subject>: commits one file; sets LASTC to the new sha.
commit_file() {
  mkdir -p "$1/$(dirname "$2")"
  printf '%s\n' "$3" > "$1/$2"
  gitc "$1" add -f -- "$2" >/dev/null
  gitc "$1" commit -q -m "$4"
  LASTC=$(gitc "$1" rev-parse HEAD)
}

init_repo() { # sets R WORK EV and BASE (a README commit)
  R=$(mktemp -d); WORK=$(mktemp -d); EV=$(mktemp -d)
  _CLEANUP_DIRS+=("$R" "$WORK" "$EV")
  git -C "$R" init -q -b main 2>/dev/null || git -C "$R" init -q
  gitc "$R" config user.email test@test
  gitc "$R" config user.name test
  commit_file "$R" README "base" "base"
  BASE=$LASTC
}

# new_fixture: base is a README. head adds fix.txt, ok.txt and t.sh (passes only with fix.txt).
new_fixture() {
  init_repo
  printf '%s\n' 'test -f fix.txt' > "$R/t.sh"
  printf 'x\n' > "$R/fix.txt"; printf 'x\n' > "$R/ok.txt"
  gitc "$R" add t.sh fix.txt ok.txt
  gitc "$R" commit -q -m "fix"
  HEAD=$(gitc "$R" rev-parse HEAD)
  write_receipt "$HEAD"; write_report "$HEAD"
}

write_receipt() { # write_receipt <head> [findings-json]
  printf '{"v":1,"ticket":"1","head":"%s","verdict":"pass","findings":%s,"commands":[{"cmd":"x","exit_code":0}],"model":"m","reviewed_with":[]}\n' \
    "$1" "${2:-[]}" > "$EV/receipt.json"
}
write_report() { # write_report <head> [status]
  printf '{"v":2,"run":"r","ticket":"1","status":"%s","head":"%s"}\n' "${2:-done}" "$1" > "$EV/report.json"
}
write_sec() { # write_sec <head> [findings-json]
  printf '{"v":1,"head":"%s","findings":%s}\n' "$1" "${2:-[]}" > "$EV/security-receipt.json"
}
rehead() { HEAD=$(gitc "$R" rev-parse HEAD); write_receipt "$HEAD"; write_report "$HEAD"; }

# fc <extra args...>: run the script on the fixture; sets OUT and RC.
fc() {
  OUT=$(cd "$WORK" && bash "$FC" --repo "$R" --base "$BASE" --head "$HEAD" --evidence "$EV" "$@" 2>&1); RC=$?
}
SUITE=(--suite-cmd 'test -f ok.txt')
REPRO=(--repro-cmd 'bash t.sh' --repro-files t.sh)
BUG=(--kind bug "${REPRO[@]}" "${SUITE[@]}")

has() { if printf '%s\n' "$OUT" | grep -qF -- "$1"; then pass; else fail "missing '$1' in: $(printf '%s' "$OUT" | tr '\n' '|')"; fi; }
hasnt() { if printf '%s\n' "$OUT" | grep -qF -- "$1"; then fail "unexpected '$1' in: $(printf '%s' "$OUT" | tr '\n' '|')"; else pass; fi; }
rc_is() { if [ "$RC" -eq "$1" ]; then pass; else fail "rc=$RC, want $1 — $(printf '%s' "$OUT" | tr '\n' '|')"; fi; }
no_mismatch() { if [ "$RC" = 0 ] && ! printf '%s\n' "$OUT" | grep -q '^MISMATCH'; then pass; else fail "rc=$RC out: $(printf '%s' "$OUT" | tr '\n' '|')"; fi; }

# --- happy path ---------------------------------------------------------------------------------
new_fixture
t "happy bug ticket: every check ok, exit 0"; fc "${BUG[@]}"
if [ "$RC" = 0 ] && ! printf '%s\n' "$OUT" | grep -q '^MISMATCH' && printf '%s\n' "$OUT" | grep -qF 'ok repro: red on base (exit 1), green on head (exit 0)' \
  && printf '%s\n' "$OUT" | grep -qF 'ok suite: exit 0' && printf '%s\n' "$OUT" | grep -qF 'ok receipt:' \
  && printf '%s\n' "$OUT" | grep -qF 'ok report:' && printf '%s\n' "$OUT" | grep -qF 'skip acceptance:' \
  && printf '%s\n' "$OUT" | grep -qF 'ok security: no risky path'; then pass
else fail "rc=$RC out: $(printf '%s' "$OUT" | tr '\n' '|')"; fi
t "happy path: last line and fleet-check.json"
last=$(printf '%s\n' "$OUT" | tail -1)
if [ "$last" = 'fleet-check: 0 mismatch(es), mode warn' ] \
  && [ "$(jq -r '.mismatches' "$EV/fleet-check.json")" = 0 ] && [ "$(jq -r '.v' "$EV/fleet-check.json")" = 1 ] \
  && [ "$(jq -r '.head' "$EV/fleet-check.json")" = "$HEAD" ] && [ "$(jq -r '.mode' "$EV/fleet-check.json")" = warn ] \
  && [ "$(jq -r '.checks | length' "$EV/fleet-check.json")" = 6 ] \
  && [ "$(jq -r '.checks[] | select(.name=="repro") | .result' "$EV/fleet-check.json")" = ok ] \
  && [ "$(jq -r '.checks[] | select(.name=="acceptance") | .result' "$EV/fleet-check.json")" = skip ] \
  && [ -z "$(ls -A "$EV" | grep '^\.fleet-check\.')" ]; then pass
else fail "last='$last' json: $(cat "$EV/fleet-check.json" 2>&1)"; fi

t "an uppercase full head in the JSON files matches (lowercase string compare)"
U=$(printf '%s' "$HEAD" | tr 'a-f' 'A-F'); write_receipt "$U"; write_report "$U"; fc "${BUG[@]}"; no_mismatch
t "an abbreviated head in receipt.json is a MISMATCH"
write_receipt "${HEAD:0:8}"; write_report "$HEAD"; fc "${BUG[@]}"; has 'MISMATCH receipt: head'
t "an abbreviated head in report.json is a MISMATCH"
write_receipt "$HEAD"; write_report "${HEAD:0:7}"; fc "${BUG[@]}"; has 'MISMATCH report: head'
t "a ref name as the head in receipt.json is a MISMATCH"
write_receipt "main"; write_report "$HEAD"; fc "${BUG[@]}"; has 'MISMATCH receipt: head'

# --- worker-controlled repo state does not change the result ------------------------------------
new_fixture
t "moving the base ref in the worker repo does not change the result"
gitc "$R" update-ref refs/heads/main "$BASE"; gitc "$R" tag -f base-moved "$BASE" >/dev/null
fc "${BUG[@]}"; no_mismatch
new_fixture
t "a tag named like the short head sha does not change the result"
gitc "$R" tag "${HEAD:0:8}" "$BASE"; gitc "$R" tag "${BASE:0:8}" "$HEAD"; fc "${BUG[@]}"; no_mismatch
new_fixture
t "git replace on the head commit does not change the result"
gitc "$R" replace "$HEAD" "$BASE" 2>/dev/null; fc "${BUG[@]}"; no_mismatch

new_fixture
printf '* filter=evil\n' > "$R/.gitattributes"; gitc "$R" add .gitattributes; gitc "$R" commit -q -m "attrs"; rehead
MARK="$WORK/marker"
mkdir -p "$R/.git/hooks"
printf '#!/bin/sh\ntouch "%s.hook"\n' "$MARK" > "$R/.git/hooks/post-checkout"; chmod +x "$R/.git/hooks/post-checkout"
gitc "$R" config filter.evil.smudge "touch $MARK.smudge; cat"
gitc "$R" config core.hooksPath "$R/.git/hooks"
gitc "$R" config core.fsmonitor "touch $MARK.fsmonitor; echo"
t "a post-checkout hook, a smudge filter and fsmonitor in the worker repo are not executed"
fc "${BUG[@]}"
if [ ! -e "$MARK.hook" ] && [ ! -e "$MARK.smudge" ] && [ ! -e "$MARK.fsmonitor" ]; then pass; else fail "marker exists: $(ls "$WORK")"; fi
t "and the checks still ran"; has 'ok suite: exit 0'

# --- repro --------------------------------------------------------------------------------------
new_fixture
t "repro green on base is a MISMATCH"; fc --kind bug --repro-cmd 'true' --repro-files t.sh "${SUITE[@]}"; has 'MISMATCH repro: not red on base'
t "repro red on head is a MISMATCH"; fc --kind bug --repro-cmd 'false' --repro-files t.sh "${SUITE[@]}"; has 'MISMATCH repro: not green on head'
t "base exit 127 (command not found) is a MISMATCH, not red"
fc --kind bug --repro-cmd 'no_such_cmd_xyz' --repro-files t.sh "${SUITE[@]}"; has 'MISMATCH repro: test did not run on base (exit 127)'
t "repro file absent on base without the overlay: exit 127 is a MISMATCH (kind feature)"
fc --kind feature --repro-cmd 'bash t.sh' "${SUITE[@]}"; has 'MISMATCH repro: test did not run on base'
t "kind bug with --repro-cmd and no --repro-files exits 2"; fc --kind bug --repro-cmd 'bash t.sh' "${SUITE[@]}"; rc_is 2
t "kind bug without --repro-cmd is a MISMATCH"; fc --kind bug "${SUITE[@]}"; has 'MISMATCH repro: kind bug needs --repro-cmd'
t "kind feature without --repro-cmd skips repro"; fc --kind feature "${SUITE[@]}"; has 'skip repro: no --repro-cmd'
t "kind feature with --repro-cmd and the overlay runs it"; fc --kind feature "${REPRO[@]}" "${SUITE[@]}"; has 'ok repro: red on base'
t "a repro file that is not in head is a MISMATCH"; fc --kind bug --repro-cmd 'true' --repro-files nope.sh "${SUITE[@]}"; has 'MISMATCH repro: cannot overlay'
t "a glob in --repro-files is taken literally"; fc --kind bug --repro-cmd 'true' --repro-files '*.sh' "${SUITE[@]}"; has 'MISMATCH repro: cannot overlay'
t "a base that does not exist in the repo is reported as a MISMATCH"
OUT=$(cd "$WORK" && bash "$FC" --repo "$R" --base 0000000000000000000000000000000000000001 --head "$HEAD" --evidence "$EV" --kind bug "${REPRO[@]}" --no-suite 2>&1); RC=$?
if printf '%s\n' "$OUT" | grep -qF 'MISMATCH repro: git mirror not usable'; then pass; else fail "$OUT"; fi
t "a head that does not descend from base is a MISMATCH"
OUT=$(cd "$WORK" && bash "$FC" --repo "$R" --base "$HEAD" --head "$BASE" --evidence "$EV" --kind bug "${REPRO[@]}" --no-suite 2>&1); RC=$?
if printf '%s\n' "$OUT" | grep -qF 'MISMATCH repro: git mirror not usable: head does not descend from base'; then pass; else fail "$OUT"; fi

# --- SHA-256 repository ---------------------------------------------------------------------------
t "a SHA-256 worker repo is read through a SHA-256 mirror"
R=$(mktemp -d); WORK=$(mktemp -d); EV=$(mktemp -d); _CLEANUP_DIRS+=("$R" "$WORK" "$EV")
if git -C "$R" init -q --object-format=sha256 -b main 2>/dev/null; then
  gitc "$R" config user.email test@test; gitc "$R" config user.name test
  commit_file "$R" README "base" "base"; BASE=$LASTC
  printf '%s\n' 'test -f fix.txt' > "$R/t.sh"; printf 'x\n' > "$R/fix.txt"; printf 'x\n' > "$R/ok.txt"
  gitc "$R" add t.sh fix.txt ok.txt; gitc "$R" commit -q -m "fix"; rehead
  fc "${BUG[@]}" --ticket-id 1; no_mismatch
else
  skip "this git cannot create a SHA-256 repository"
fi
new_fixture
t "--ticket-id that differs from the evidence is a MISMATCH"; fc "${BUG[@]}" --ticket-id 2; has 'MISMATCH receipt'

# --- shallow source -----------------------------------------------------------------------------
new_fixture
SRC=$R; CLONE=$(mktemp -d); _CLEANUP_DIRS+=("$CLONE"); rmdir "$CLONE"
git clone -q --depth 1 "file://$SRC" "$CLONE" 2>/dev/null
R=$CLONE
t "a shallow worker repo is a MISMATCH, never a silent ok"; fc "${BUG[@]}"; has 'MISMATCH repro: git mirror not usable'

# --- receipt ------------------------------------------------------------------------------------
new_fixture
t "receipt missing is a MISMATCH"; rm "$EV/receipt.json"; fc "${BUG[@]}"; has 'MISMATCH receipt: receipt.json is missing'
t "receipt that does not parse is a MISMATCH"; printf '{nope' > "$EV/receipt.json"; fc "${BUG[@]}"; has 'MISMATCH receipt: receipt.json does not parse'
t "receipt head differs is a MISMATCH"; write_receipt "$BASE"; fc "${BUG[@]}"; has 'MISMATCH receipt: head'
t "receipt verdict changes is a MISMATCH"
printf '{"v":1,"head":"%s","verdict":"changes","findings":[]}\n' "$HEAD" > "$EV/receipt.json"; fc "${BUG[@]}"; has "MISMATCH receipt: verdict is 'changes'"
t "receipt with an open finding is a MISMATCH"
write_receipt "$HEAD" '[{"id":"a","severity":"high","status":"open"}]'; fc "${BUG[@]}"; has 'MISMATCH receipt: 1 open finding'
t "receipt accepted finding without accepted_by is a MISMATCH"
write_receipt "$HEAD" '[{"id":"a","severity":"low","status":"accepted"}]'; fc "${BUG[@]}"; has 'without accepted_by'
t "receipt accepted finding with a blank accepted_by is a MISMATCH"
write_receipt "$HEAD" '[{"id":"a","severity":"low","status":"accepted","accepted_by":"  "}]'; fc "${BUG[@]}"; has 'without accepted_by'
t "receipt accepted_by 'worker' is a MISMATCH"
write_receipt "$HEAD" '[{"id":"a","severity":"low","status":"accepted","accepted_by":"worker"}]'; fc "${BUG[@]}"; has 'without accepted_by'
t "receipt accepted_by owner and advisor, plus a fixed finding, is ok"
write_receipt "$HEAD" '[{"id":"a","severity":"low","status":"accepted","accepted_by":"owner"},{"id":"c","severity":"low","status":"accepted","accepted_by":"Advisor "},{"id":"b","severity":"low","status":"fixed"}]'
fc "${BUG[@]}"; has 'ok receipt:'
t "receipt findings as a string is a MISMATCH"
printf '{"v":1,"head":"%s","verdict":"pass","findings":"none"}\n' "$HEAD" > "$EV/receipt.json"; fc "${BUG[@]}"; has 'MISMATCH receipt: findings is not an array'
t "receipt without findings is a MISMATCH"
printf '{"v":1,"head":"%s","verdict":"pass"}\n' "$HEAD" > "$EV/receipt.json"; fc "${BUG[@]}"; has 'MISMATCH receipt: findings is not an array'
t "receipt with a non-object finding is a MISMATCH"
write_receipt "$HEAD" '["x"]'; fc "${BUG[@]}"; has 'MISMATCH receipt: findings holds a non-object'
t "receipt status 'Open ' (case and blanks) counts as open: MISMATCH"
write_receipt "$HEAD" '[{"id":"a","severity":"low","status":"Open "}]'; fc "${BUG[@]}"; has 'MISMATCH receipt: 1 open finding'
t "receipt with an unknown status is a MISMATCH"
write_receipt "$HEAD" '[{"id":"a","severity":"low","status":"wontfix"}]'; fc "${BUG[@]}"; has 'status other than open, fixed or accepted'
t "receipt with a null severity is a MISMATCH"
write_receipt "$HEAD" '[{"id":"a","severity":null,"status":"fixed"}]'; fc "${BUG[@]}"; has 'unknown severity'
t "receipt ticket differs from --ticket-id is a MISMATCH"; write_receipt "$HEAD"; fc "${BUG[@]}" --ticket-id 2; has "MISMATCH receipt: ticket '1' is not 2"
t "receipt and report ticket equal to --ticket-id are ok"; fc "${BUG[@]}" --ticket-id 1; no_mismatch
t "report ticket differs from --ticket-id is a MISMATCH"; write_report "$HEAD"; fc "${BUG[@]}" --ticket-id 3; has "MISMATCH report: ticket '1' is not 3"
t "a symlinked receipt.json is a MISMATCH"
mv "$EV/receipt.json" "$WORK/real-receipt.json"; ln -s "$WORK/real-receipt.json" "$EV/receipt.json"; fc "${BUG[@]}"; has 'MISMATCH receipt: receipt.json is symlink'

# --- report -------------------------------------------------------------------------------------
new_fixture
t "report status not done is a MISMATCH"; write_report "$HEAD" blocked; fc "${BUG[@]}"; has "MISMATCH report: status is 'blocked'"
t "report v 1 is a MISMATCH"
printf '{"v":1,"status":"done","head":"%s"}\n' "$HEAD" > "$EV/report.json"; fc "${BUG[@]}"; has "MISMATCH report: v is '1'"
t "report head differs is a MISMATCH"; write_report "$BASE"; fc "${BUG[@]}"; has 'MISMATCH report: head'
t "report missing is a MISMATCH"; rm "$EV/report.json"; fc "${BUG[@]}"; has 'MISMATCH report: report.json is missing'

# --- suite --------------------------------------------------------------------------------------
new_fixture
t "suite failing is a MISMATCH"; fc --kind bug "${REPRO[@]}" --suite-cmd 'test -f missing.txt'; has 'MISMATCH suite: suite command exited 1'
t "--no-suite skips the suite"; fc --kind bug "${REPRO[@]}" --no-suite; has 'skip suite: --no-suite'
t "the suite runs in a fresh head checkout (repro overlay does not leak, fix.txt is there)"
fc --kind bug "${REPRO[@]}" --suite-cmd 'test -f fix.txt && test -f t.sh'; has 'ok suite: exit 0'
t "the suite cannot see an env var exported by the caller"
OUT=$(cd "$WORK" && SECRET_TOKEN=abc123 bash "$FC" --repo "$R" --base "$BASE" --head "$HEAD" --evidence "$EV" --kind bug "${REPRO[@]}" --suite-cmd 'test -z "${SECRET_TOKEN:-}"' 2>&1); RC=$?
if printf '%s\n' "$OUT" | grep -qF 'ok suite: exit 0'; then pass; else fail "$OUT"; fi
t "the repro command cannot see it either"
OUT=$(cd "$WORK" && SECRET_TOKEN=abc123 bash "$FC" --repo "$R" --base "$BASE" --head "$HEAD" --evidence "$EV" --kind bug --repro-cmd 'test -z "${SECRET_TOKEN:-}" && test -f fix.txt' --repro-files t.sh --no-suite 2>&1); RC=$?
if printf '%s\n' "$OUT" | grep -qF 'ok repro: red on base'; then pass; else fail "$OUT"; fi

# --- acceptance (--qa-commit) -------------------------------------------------------------------
QADIR=tests/acceptance
qa_args() { QA=(--kind feature --no-suite --qa-dir "$QADIR" "$@"); }

init_repo
commit_file "$R" tests/acceptance/a.sh "t" "Add acceptance tests for #7"; Q1=$LASTC
commit_file "$R" src/code.sh "c" "implement"
rehead; qa_args --qa-commit "$Q1"
t "acceptance: a listed qa commit before the code is ok"; fc "${QA[@]}"; has 'ok acceptance:'

init_repo
commit_file "$R" tests/acceptance/a.sh "t" "Add acceptance tests for #7"; Q1=$LASTC
commit_file "$R" src/code.sh "c" "implement"
commit_file "$R" tests/acceptance/a.sh "t2" "Add acceptance tests for #7"; Q2=$LASTC
rehead
t "acceptance: a second qa commit not listed is a MISMATCH even with the old subject"
fc --kind feature --no-suite --qa-dir "$QADIR" --qa-commit "$Q1"; has "touches $QADIR but is not a --qa-commit"
t "acceptance: a listed repair qa commit after the code is ok"
fc --kind feature --no-suite --qa-dir "$QADIR" --qa-commit "$Q1" --qa-commit "$Q2"; has 'ok acceptance:'
t "acceptance: a trailing slash and ./ on --qa-dir are normalised"
fc --kind feature --no-suite --qa-dir "./$QADIR/" --qa-commit "$Q1" --qa-commit "$Q2"; has 'ok acceptance:'
t "acceptance: the qa dir compares case-insensitively"
fc --kind feature --no-suite --qa-dir "Tests/Acceptance" --qa-commit "$Q1" --qa-commit "$Q2"; has 'ok acceptance:'
commit_file "$R" "$QADIR/café.sh" "true" "later edit with an odd name"; rehead
t "acceptance: an unlisted commit that adds a non-ASCII name in the qa dir is a MISMATCH"
fc --kind feature --no-suite --qa-dir "$QADIR" --qa-commit "$Q1" --qa-commit "$Q2"; has "but is not a --qa-commit"
init_repo
commit_file "$R" "tests/acceptance/a.sh" "true" "Add acceptance tests for #1"; QC=$LASTC
commit_file "$R" "src/code.txt" "x" "code"
commit_file "$R" "TESTS/Acceptance/b.sh" "true" "sneaky case"; rehead
t "acceptance: an unlisted commit under another case of the qa dir is a MISMATCH"
fc --kind feature --no-suite --qa-dir tests/acceptance --qa-commit "$QC"; has "but is not a --qa-commit"
init_repo
gitc "$R" commit -q --allow-empty -m "Add acceptance tests for #1"; QE=$(gitc "$R" rev-parse HEAD)
commit_file "$R" "src/code.txt" "x" "code"
commit_file "$R" "tests/acceptance/a.sh" "true" "Add acceptance tests for #1"; QL=$LASTC; rehead
t "acceptance: an empty first qa commit does not count as tests before code"
fc --kind feature --no-suite --qa-dir tests/acceptance --qa-commit "$QE" --qa-commit "$QL"; has "touches nothing in tests/acceptance"

new_fixture
printf '{"v":1,"ticket":"1","head":"%s","verdict":"pass\\n","findings":[],"commands":[]}\n' "$HEAD" > "$EV/receipt.json"
t "a verdict that ends in a newline is not pass"; fc "${BUG[@]}"; has 'MISMATCH receipt'
new_fixture
printf 'null\n{"v":2,"run":"r","ticket":"1","status":"done","head":"%s"}\n' "$HEAD" > "$EV/report.json"
t "a report file with two JSON documents is a MISMATCH"; fc "${BUG[@]}"; has 'MISMATCH report'
new_fixture
printf '{"v":2,"run":"r","ticket":"1","status":"a\\"b\\\\","head":"%s"}\n' "$HEAD" > "$EV/report.json"
t "a quote and a backslash in a JSON value still give a valid fleet-check.json"; fc "${BUG[@]}"
if jq -e . "$EV/fleet-check.json" >/dev/null 2>&1; then pass; else fail "invalid JSON: $(cat "$EV/fleet-check.json")"; fi
new_fixture
ln -s tools "$R/scripts"; mkdir "$R/tools"; gitc "$R" add scripts; gitc "$R" commit -q -m "symlink named scripts"; rehead
t "security: a symlink named scripts is a risky path"; fc "${BUG[@]}"; has 'MISMATCH security'

init_repo
commit_file "$R" src/code.sh "c" "implement"
commit_file "$R" tests/acceptance/a.sh "t" "Add acceptance tests for #7"; Q1=$LASTC
rehead
t "acceptance: a code commit before the first qa commit is a MISMATCH"
fc --kind feature --no-suite --qa-dir "$QADIR" --qa-commit "$Q1"; has 'MISMATCH acceptance: code commit'

init_repo
mkdir -p "$R/tests/acceptance" "$R/src"; printf 't\n' > "$R/tests/acceptance/a.sh"; printf 'c\n' > "$R/src/code.sh"
gitc "$R" add -A; gitc "$R" commit -q -m "Add acceptance tests for #7"; Q1=$(gitc "$R" rev-parse HEAD)
rehead
t "acceptance: a qa commit that also touches code is a MISMATCH"
fc --kind feature --no-suite --qa-dir "$QADIR" --qa-commit "$Q1"; has "touches paths outside $QADIR"

init_repo
commit_file "$R" tests/acceptance/a.sh "t" "Add acceptance tests for #7"; Q1=$LASTC
gitc "$R" checkout -q -b side; commit_file "$R" src/side.sh "s" "side work"
gitc "$R" checkout -q main; commit_file "$R" src/code.sh "c" "main work"
gitc "$R" merge -q --no-ff side -m "join" >/dev/null 2>&1
rehead
t "acceptance: a merge commit in the range is a MISMATCH"
fc --kind feature --no-suite --qa-dir "$QADIR" --qa-commit "$Q1"; has 'MISMATCH acceptance: a merge commit is in the range'

init_repo
commit_file "$R" src/code.sh "c" "implement"; C1=$LASTC
rehead
t "acceptance: a --qa-commit outside the range is a MISMATCH"
fc --kind feature --no-suite --qa-dir "$QADIR" --qa-commit "$BASE"; has 'is not in'
t "acceptance: a commit that is not in the range is rejected for code too (qa commit is code)"
fc --kind feature --no-suite --qa-dir "$QADIR" --qa-commit "$C1"; has "touches paths outside $QADIR"

t "usage: --qa-dir without --qa-commit exits 2"; fc --kind feature --no-suite --qa-dir "$QADIR"; rc_is 2
t "usage: --qa-commit without --qa-dir exits 2"; fc --kind feature --no-suite --qa-commit "$C1"; rc_is 2
t "usage: --qa-commit that is not a full sha exits 2"; fc --kind feature --no-suite --qa-dir "$QADIR" --qa-commit "${C1:0:10}"; rc_is 2
t "usage: --qa-dir '.' exits 2"; fc --kind feature --no-suite --qa-dir . --qa-commit "$C1"; rc_is 2
t "usage: --qa-dir '/' exits 2"; fc --kind feature --no-suite --qa-dir / --qa-commit "$C1"; rc_is 2
t "usage: --qa-dir './' exits 2"; fc --kind feature --no-suite --qa-dir ./ --qa-commit "$C1"; rc_is 2
t "usage: --qa-dir with .. exits 2"; fc --kind feature --no-suite --qa-dir a/../b --qa-commit "$C1"; rc_is 2

# --- security -----------------------------------------------------------------------------------
new_fixture
commit_file "$R" hooks/x.sh "echo" "touch a hook"
rehead
SEC=(--kind feature --no-suite)
t "security: risky path without a security receipt is a MISMATCH"; fc "${SEC[@]}"; has 'MISMATCH security: risky path (hooks/x.sh'
t "security: risky path with a clean receipt is ok"; write_sec "$HEAD"; fc "${SEC[@]}"; has 'ok security: risky path'
t "security: a receipt with only a medium open finding is ok"
write_sec "$HEAD" '[{"severity":"medium","status":"open"}]'; fc "${SEC[@]}"; has 'ok security: risky path'
t "security: an open high finding is a MISMATCH"
write_sec "$HEAD" '[{"severity":"high","status":"open"}]'; fc "${SEC[@]}"; has 'MISMATCH security: risky path (hooks/x.sh): 1 open critical or high'
t "security: a fixed critical finding is ok"
write_sec "$HEAD" '[{"severity":"critical","status":"fixed"}]'; fc "${SEC[@]}"; has 'ok security: risky path'
t "security: a receipt head that differs is a MISMATCH"; write_sec "$BASE"; fc "${SEC[@]}"; has 'MISMATCH security: risky path (hooks/x.sh): head'
t "security: a short receipt head is a MISMATCH"; write_sec "${HEAD:0:8}"; fc "${SEC[@]}"; has 'MISMATCH security: risky path (hooks/x.sh): head'
t "security: findings with an unknown severity are a MISMATCH"
write_sec "$HEAD" '[{"severity":"urgent","status":"fixed"}]'; fc "${SEC[@]}"; has 'unknown severity'
t "security: a symlinked receipt is a MISMATCH"
rm -f "$EV/security-receipt.json"; write_sec "$HEAD"; mv "$EV/security-receipt.json" "$WORK/real-sec.json"; ln -s "$WORK/real-sec.json" "$EV/security-receipt.json"
fc "${SEC[@]}"; has 'security-receipt.json is symlink'

for rp in 'db/m.sql' 'scripts/run.sh' '.github/CODEOWNERS' 'REVIEW.md' '.claude/settings.local.json' 'auth/café.txt' 'secrets/my file.txt'; do
  new_fixture; commit_file "$R" "$rp" "x" "add risky"; rehead
  t "security: '$rp' counts as risky"; fc "${SEC[@]}"; has 'MISMATCH security: risky path ('
done
t "security: a non-ASCII risky name prints as plain ASCII"
new_fixture; commit_file "$R" "auth/café.txt" "x" "add"; rehead; fc "${SEC[@]}"
if printf '%s' "$OUT" | LC_ALL=C grep -q '[^ -~]'; then
  # the OUT may contain newlines only
  if printf '%s' "$OUT" | LC_ALL=C tr -d '\n' | LC_ALL=C grep -q '[^ -~]'; then fail "non-ASCII byte in output"; else pass; fi
else pass; fi

# a renamed risky path cannot hide: base has hooks/x.sh, head moves it away
new_fixture
commit_file "$R" hooks/x.sh "echo hi" "add hook"; BASE=$LASTC
gitc "$R" mv hooks/x.sh lib_x.sh; gitc "$R" commit -q -m "rename away"
rehead
t "security: renaming a risky path away is still seen"; fc "${SEC[@]}"; has 'MISMATCH security: risky path (hooks/x.sh'

new_fixture
t "security: a receipt with an open critical finding and no risky path is a MISMATCH"
write_sec "$HEAD" '[{"severity":"critical","status":"open"}]'; fc "${SEC[@]}"; has 'MISMATCH security: no risky path: 1 open critical or high'
t "security: a clean receipt with no risky path is ok"; write_sec "$HEAD"; fc "${SEC[@]}"; has 'ok security: no risky path'
rm -f "$EV/security-receipt.json"
t "security: --risky without a receipt is a MISMATCH"; fc "${SEC[@]}" --risky; has 'MISMATCH security: --risky'
t "security: --risky with a clean receipt is ok"; write_sec "$HEAD"; fc "${SEC[@]}" --risky; has 'ok security: no risky path'

# --- modes and exit codes -----------------------------------------------------------------------
new_fixture
RED=(--kind bug --repro-cmd 'true' --repro-files t.sh "${SUITE[@]}")
t "warn mode exits 0 with mismatches"; fc "${RED[@]}" --mode warn
if [ "$RC" = 0 ] && printf '%s\n' "$OUT" | tail -1 | grep -qF 'fleet-check: 1 mismatch(es), mode warn' \
  && [ "$(jq -r '.mismatches' "$EV/fleet-check.json")" = 1 ]; then pass; else fail "rc=$RC out: $OUT"; fi
t "block mode exits 1 with mismatches"; fc "${RED[@]}" --mode block
if [ "$RC" = 1 ] && printf '%s\n' "$OUT" | tail -1 | grep -qF 'mode block' && [ "$(jq -r '.mode' "$EV/fleet-check.json")" = block ]; then pass; else fail "rc=$RC out: $OUT"; fi
t "block mode exits 0 with no mismatch"; fc "${BUG[@]}" --mode block; rc_is 0
t "default mode is warn"; fc "${RED[@]}"; rc_is 0

# --- untrusted evidence is never executed and never printed raw ---------------------------------
new_fixture
t "shell text in report.json and receipt.json is never executed"
printf '{"v":2,"run":"$(touch PWNED)","ticket":"; touch PWNED","status":"$(touch PWNED)","head":"; touch PWNED `touch PWNED`","cmd":"touch PWNED","commands":[{"cmd":"touch PWNED","exit_code":0}]}\n' > "$EV/report.json"
printf '{"v":1,"head":"$(touch PWNED)","verdict":"pass","findings":[{"id":"; touch PWNED","status":"accepted","accepted_by":"$(touch PWNED)"}],"commands":[{"cmd":"touch PWNED","exit_code":0}]}\n' > "$EV/receipt.json"
fc "${BUG[@]}"
found=$(find "$WORK" "$R" "$EV" /tmp -maxdepth 1 -name PWNED 2>/dev/null | head -1)
if [ -z "$found" ] && printf '%s\n' "$OUT" | grep -qF 'MISMATCH report:' && [ -f "$EV/fleet-check.json" ] && jq -e . "$EV/fleet-check.json" >/dev/null; then pass
else fail "found='$found' rc=$RC out: $(printf '%s' "$OUT" | tr '\n' '|')"; fi

t "control characters in evidence values are stripped from output and JSON, and long values are cut"
ESC=$'\033'; long=$(printf 'A%.0s' $(seq 1 400))
printf '{"v":2,"ticket":"1","status":"%s","head":"%s"}\n' "x\\u001b[31m\\r\\nred${long}" "$HEAD" > "$EV/report.json"
fc "${BUG[@]}"
if ! printf '%s' "$OUT" | grep -q "$ESC" && ! grep -q "$ESC" "$EV/fleet-check.json" \
  && jq -e . "$EV/fleet-check.json" >/dev/null && ! printf '%s' "$OUT" | grep -qF "$(printf 'A%.0s' $(seq 1 250))" \
  && printf '%s\n' "$OUT" | grep -qF 'MISMATCH report: status is'; then pass; else fail "out: $(printf '%s' "$OUT" | cut -c1-300)"; fi

# --- the repo is left untouched -----------------------------------------------------------------
new_fixture
snap() {
  printf '%s\n--\n%s\n--\n%s\n--\n' "$(gitc "$R" worktree list)" "$(gitc "$R" for-each-ref)" "$(gitc "$R" rev-parse HEAD)"
  (cd "$R/.git" && find . -type f | sort | while IFS= read -r f; do cksum "$f"; done)
  (cd "$R" && ls -A | sort | tr '\n' ' ')
}
before=$(snap); fc "${BUG[@]}"; after=$(snap)
t "the --repo worktree list, refs and .git contents are byte-identical after a run"
if [ "$before" = "$after" ] && [ -z "$(ls "$R/.git/worktrees" 2>/dev/null)" ]; then pass; else fail "before/after differ: $(diff <(printf '%s' "$before") <(printf '%s' "$after") | head -5)"; fi
before=$(snap); fc --kind bug --repro-cmd 'true' --repro-files nope.sh --suite-cmd false; after=$(snap)
t "the repo is unchanged after a run that fails inside the checkout too"
if [ "$before" = "$after" ]; then pass; else fail "before/after differ"; fi

# --- result file --------------------------------------------------------------------------------
new_fixture
echo precious > "$WORK/victim"; ln -s "$WORK/victim" "$EV/fleet-check.json"
t "a symlinked fleet-check.json is not followed"; fc "${BUG[@]}"
if [ "$(cat "$WORK/victim")" = precious ] && [ -L "$EV/fleet-check.json" ] && printf '%s\n' "$OUT" | grep -qF 'refusing to write'; then pass; else fail "victim: $(cat "$WORK/victim") out: $OUT"; fi
t "block mode exits 1 when the result file cannot be written"; fc "${BUG[@]}" --mode block; rc_is 1

# --- TMPDIR with a space ------------------------------------------------------------------------
new_fixture
SPACE="$WORK/a b"; mkdir -p "$SPACE"; echo keep > "$WORK/sentinel"; echo keep > "$SPACE/inside"
t "a TMPDIR containing a space works and deletes nothing outside its own temp dir"
OUT=$(cd "$WORK" && TMPDIR="$SPACE" bash "$FC" --repo "$R" --base "$BASE" --head "$HEAD" --evidence "$EV" "${BUG[@]}" 2>&1); RC=$?
if [ "$RC" = 0 ] && ! printf '%s\n' "$OUT" | grep -q '^MISMATCH' && [ -f "$WORK/sentinel" ] && [ -f "$SPACE/inside" ] \
  && [ "$(ls -A "$SPACE")" = inside ]; then pass; else fail "rc=$RC out: $OUT ls: $(ls -A "$SPACE")"; fi

# --- usage errors -------------------------------------------------------------------------------
new_fixture
t "no arguments exits 2"; OUT=$(bash "$FC" 2>&1); RC=$?; rc_is 2
t "a missing required arg (--evidence) exits 2 and names it"
OUT=$(bash "$FC" --repo "$R" --base "$BASE" --head "$HEAD" --kind bug 2>&1); RC=$?
if [ "$RC" = 2 ] && printf '%s' "$OUT" | grep -qF -- '--evidence is required'; then pass; else fail "rc=$RC $OUT"; fi
t "a short --head exits 2"; OUT=$(bash "$FC" --repo "$R" --base "$BASE" --head "${HEAD:0:10}" --evidence "$EV" --kind bug 2>&1); RC=$?; rc_is 2
t "a ref name as --base exits 2"; OUT=$(bash "$FC" --repo "$R" --base main --head "$HEAD" --evidence "$EV" --kind bug 2>&1); RC=$?; rc_is 2
t "a bad --kind exits 2"; fc --kind nope; rc_is 2
t "a bad --mode exits 2"; fc "${BUG[@]}" --mode loud; rc_is 2
t "the removed --ticket option exits 2"; fc "${BUG[@]}" --ticket 7; rc_is 2
t "an unknown option exits 2"; fc "${BUG[@]}" --bogus; rc_is 2
t "an option with no value exits 2"; OUT=$(bash "$FC" --repo 2>&1); RC=$?; rc_is 2

finish
