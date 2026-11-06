#!/bin/bash
# Acceptance tests for #575: scripts/lint-adr-paths.sh (a missing path in docs/adr must be marked
# '(historical)'). Black-box: the script runs inside a throwaway git repo.
source "$(dirname "$0")/../lib.sh"

LINT_SRC="$ROOT/scripts/lint-adr-paths.sh"

# adr_repo <file-name> <body> -> temp git repo holding docs/adr/<file-name>, the lint copied in.
adr_repo() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q
  mkdir -p "$d/docs/adr" "$d/scripts" "$d/plugins/harness/hooks"
  [ -f "$LINT_SRC" ] && cp "$LINT_SRC" "$d/scripts/"
  printf 'x\n' > "$d/scripts/real.sh"
  printf 'x\n' > "$d/plugins/harness/hooks/real-hook.sh"
  mkdir -p "$d/.claude/rules"; printf 'x\n' > "$d/.claude/rules/real-rule.md"
  printf '%s\n' "$2" > "$d/docs/adr/$1"
  git -C "$d" add -A
  echo "$d"
}
run_lint() { [ -f "$1/scripts/lint-adr-paths.sh" ] && { OUT=$(cd "$1" && bash scripts/lint-adr-paths.sh 2>&1); RC=$?; } || { OUT="script missing"; RC=127; }; }

t "AC3: the lint script exists"
[ -f "$LINT_SRC" ] && pass || fail "scripts/lint-adr-paths.sh is missing"

t "AC3: an unmarked missing path fails and names file:line"
d=$(adr_repo 0099-x.md $'# T\n\nSee `scripts/gone.sh` here.')
run_lint "$d"
if [ "$RC" != 0 ] && printf '%s' "$OUT" | grep -q '0099-x.md:3'; then pass; else fail "rc=$RC: $OUT"; fi

t "AC3/AC4: the same path marked (historical) passes"
d=$(adr_repo 0099-x.md $'# T\n\nSee `scripts/gone.sh` (historical) here.')
run_lint "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "AC3: a path that exists at the repo root passes unmarked"
d=$(adr_repo 0099-x.md 'See `scripts/real.sh`.')
run_lint "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "AC3: a path that exists under plugins/harness/ passes unmarked"
d=$(adr_repo 0099-x.md 'See `hooks/real-hook.sh`.')
run_lint "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "F2: a real .claude/ file resolves as written"
d=$(adr_repo 0099-x.md 'See `.claude/rules/real-rule.md`.')
run_lint "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "AC3: only the marked line is excused; an unmarked one on another line still fails"
d=$(adr_repo 0099-x.md $'`scripts/gone.sh` (historical)\n`scripts/other-gone.sh`')
run_lint "$d"
if [ "$RC" != 0 ] && printf '%s' "$OUT" | grep -q '0099-x.md:2'; then pass; else fail "rc=$RC: $OUT"; fi

t "AC3: no dependence on ADR numbers (file with no number prefix is scanned)"
d=$(adr_repo notes.md 'See `scripts/gone.sh`.')
run_lint "$d"; { [ "$RC" != 0 ] && [ "$RC" != 127 ]; } && pass || fail "rc=$RC: $OUT"

t "AC3: no dependence on ADR numbers (a very high number is scanned)"
d=$(adr_repo 4242-later.md 'See `skills/gone/SKILL.md`.')
run_lint "$d"; { [ "$RC" != 0 ] && [ "$RC" != 127 ]; } && pass || fail "rc=$RC: $OUT"

t "AC3: the script source names no ADR number"
if [ -f "$LINT_SRC" ] && ! grep -Eq '\b00[0-9]{2}\b' "$LINT_SRC"; then pass; else fail "script missing or mentions a 00NN number"; fi

t "AC3: every unmarked missing path is reported, not only the first"
d=$(adr_repo 0099-x.md $'`scripts/a-gone.sh`\n`scripts/b-gone.sh`')
run_lint "$d"
if [ "$RC" != 0 ] && printf '%s' "$OUT" | grep -q ':1' && printf '%s' "$OUT" | grep -q ':2'; then pass; else fail "rc=$RC: $OUT"; fi

t "AC2/AC7: the lint passes on this repository's own docs/adr"
OUT=$(cd "$ROOT" && bash scripts/lint-adr-paths.sh 2>&1); RC=$?
[ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "AC4: run-tests.sh runs the lint as an L1 step"
if grep -Fq 'lint-adr-paths.sh || fail "scripts/lint-adr-paths.sh"' "$ROOT/scripts/run-tests.sh"; then pass; else fail "no L1 step in scripts/run-tests.sh"; fi

t "AC7: shellcheck is clean for the new script"
if ! command -v shellcheck >/dev/null 2>&1; then skip "shellcheck not installed"
elif [ -f "$LINT_SRC" ] && shellcheck "$LINT_SRC" >/dev/null 2>&1; then pass; else fail "shellcheck failed or script missing"; fi

finish
