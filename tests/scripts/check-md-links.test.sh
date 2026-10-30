#!/bin/bash
# Contract tests for scripts/check-md-links.sh.
source "$(dirname "$0")/../lib.sh"

CHECK="$ROOT/scripts/check-md-links.sh"

# A temp git repo holding the given README.md body.
md_repo() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q
  mkdir -p "$d/docs"
  printf 'hello\n' > "$d/docs/real.md"
  printf '%s\n' "$1" > "$d/README.md"
  git -C "$d" add -A
  echo "$d"
}

run_check() { OUT=$(bash "$CHECK" "$1" 2>&1); RC=$?; }

t "a link to an existing file passes"
d=$(md_repo 'See [real](docs/real.md) and [frag](docs/real.md#top).')
run_check "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "a dead relative link fails and is named"
d=$(md_repo 'See [gone](docs/missing.md).')
run_check "$d"
if [ "$RC" != 0 ] && printf '%s' "$OUT" | grep -q 'docs/missing.md'; then pass; else fail "rc=$RC: $OUT"; fi

t "anchor-only, http, https and mailto links are ignored"
d=$(md_repo '[a](#section) [b](http://example.invalid/x) [c](https://example.invalid/y.md) [d](mailto:a@b.c)')
run_check "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "a dead link inside a fenced code block is ignored"
d=$(md_repo $'```\n[x](nope.md)\n```')
run_check "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "a dead link under docs/solutions is not checked"
d=$(md_repo 'ok')
mkdir -p "$d/docs/solutions"; printf '[x](nope.md)\n' > "$d/docs/solutions/a.md"
git -C "$d" add -A
run_check "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "a dead backticked path in README.md fails"
d=$(md_repo 'Run `scripts/gone.sh` first.')
run_check "$d"; [ "$RC" != 0 ] && pass || fail "rc=$RC: $OUT"

t "an existing backticked path in README.md passes"
d=$(md_repo 'Read `docs/real.md`.')
run_check "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

finish
