#!/bin/bash
# Tests for plugins/harness/scripts/ground-check.sh: claims in a research brief, design or plan are
# checked against a git ref (never the working tree). Exit 0 all hold, 1 a claim failed, 2 usage.
source "$(dirname "$0")/../lib.sh"

BASH_BIN=$(command -v bash)
GC="$ROOT/plugins/harness/scripts/ground-check.sh"

# A throwaway repo with one commit. The working tree is changed after the commit so a test can prove
# the script reads the ref, not the checkout.
REPO=$(mktemp -d); _CLEANUP_DIRS+=("$REPO")
git -C "$REPO" init -q -b main 2>/dev/null || git -C "$REPO" init -q
git -C "$REPO" config user.email test@test
git -C "$REPO" config user.name test
mkdir -p "$REPO/src" "$REPO/tests"
printf 'line one\nfunction buildWidget(opts) {\n  return opts.size;\n}\nconst MAX_ITEMS = 5;\n' > "$REPO/src/app.js"
printf '#!/bin/bash\necho run\n' > "$REPO/tests/run.sh"
printf 'one\ntwo\n' > "$REPO/README.md"
git -C "$REPO" add -A
git -C "$REPO" commit -q -m init
SHA=$(git -C "$REPO" rev-parse HEAD)
printf 'extra\n' > "$REPO/src/untracked-only.js"   # exists in the checkout, not on the ref

WORK=$(mktemp -d); _CLEANUP_DIRS+=("$WORK")
# chk <mode> <text> — writes the text to a file, runs the script, sets OUT and RC.
chk() {
  printf '%s\n' "$2" > "$WORK/in.md"
  OUT=$(cd "$WORK" && "$BASH_BIN" "$GC" --repo "$REPO" --ref HEAD --mode "$1" in.md 2>&1); RC=$?
}
has() { printf '%s\n' "$OUT" | grep -qF -- "$1"; }
nfail() { printf '%s\n' "$OUT" | grep -c '^FAIL '; }

t "a real backtick path passes (exit 0)"
chk full 'The entry point is `src/app.js` and the runner is `tests/run.sh`.'
if [ "$RC" -eq 0 ] && [ "$(nfail)" = 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a missing path fails (exit 1) with one FAIL path line that names it"
chk full 'See `src/missing.js` for details.'
if [ "$RC" -eq 1 ] && [ "$(nfail)" = 1 ] && has 'FAIL path: src/missing.js'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a file only in the working tree, not on the ref, fails"
chk full 'See `src/untracked-only.js`.'
if [ "$RC" -eq 1 ] && has 'FAIL path: src/untracked-only.js'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a path:N citation with a matching backtick quote passes"
chk full 'The size is read at `src/app.js:3` — `return opts.size;`'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a quote that does not occur within lines N-2..N+2 fails with FAIL quote"
chk full 'The limit is at `src/app.js:1` — `const MAX_ITEMS = 5;`'
if [ "$RC" -eq 1 ] && has 'FAIL quote:'; then pass; else fail "rc=$RC out=$OUT"; fi

t "an unrelated backtick span later on the line is not taken as the quote"
chk full 'The size is read at `src/app.js:3`, which the `Gadget` class uses.'
if [ "$RC" -eq 0 ] && ! has 'FAIL quote'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a quote cut at an ellipsis matches its prefix"
chk full 'See `src/app.js:2` — `function buildWidget(...`'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a line number past the end of the file fails with FAIL line"
chk full 'See `src/app.js:99`.'
if [ "$RC" -eq 1 ] && has 'FAIL line:'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a line range past the end fails with FAIL line"
chk full 'See src/app.js:3-99 for the body.'
if [ "$RC" -eq 1 ] && has 'FAIL line:'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a citation of a unique bare file name is checked against that file"
chk full 'The limit is at app.js:5.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a missing path marked (new) passes"
chk full 'We add `src/widget.js` (new) and call it from `src/app.js`.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a (new) marker exempts the token everywhere in the same text"
chk full 'Create `src/widget.js` (new).
Later: edit `src/widget.js` to add logging.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a plan Files: line with an unquoted path followed by (new) passes"
chk paths-only '### 1. Tests
- Files: tests/ground.test.sh (new), src/app.js
- Done-when: `bash tests/ground.test.sh` → exit 0'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a plan Files: line with a missing path not marked new fails"
chk paths-only '- Files: src/app.js, src/nope.js'
if [ "$RC" -eq 1 ] && has 'FAIL path: src/nope.js'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a missing camelCase symbol fails with FAIL symbol"
chk full 'The helper `renderGadget` does the work.'
if [ "$RC" -eq 1 ] && has 'FAIL symbol: renderGadget'; then pass; else fail "rc=$RC out=$OUT"; fi

t "an existing camelCase symbol and an UPPER_CASE symbol pass"
chk full 'Call `buildWidget` and read `MAX_ITEMS`, also written `buildWidget()`.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a plain lowercase word and a flag in backticks are not symbol claims"
chk full 'Use the `config` and pass `--force` to it.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a missing symbol marked (new) passes"
chk full 'Add `renderGadget` (new) next to `buildWidget`.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a dotted symbol passes when its last segment is on the ref"
chk full 'Reads `opts.size`, then `opts.buildWidget`.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a valid Pins sha passes"
chk full "Pins: $SHA"
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "an unknown Pins sha fails with FAIL pins"
chk full 'Pins: 0123456789abcdef0123456789abcdef01234567'
if [ "$RC" -eq 1 ] && has 'FAIL pins:'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a Pins sha that is not an ancestor of the ref fails"
git -C "$REPO" checkout -q -b side
printf 'x\n' > "$REPO/side.txt"; git -C "$REPO" add side.txt; git -C "$REPO" commit -q -m side
SIDE=$(git -C "$REPO" rev-parse HEAD)
git -C "$REPO" checkout -q main
chk full "Pins: $SIDE"
if [ "$RC" -eq 1 ] && has 'FAIL pins:'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a Done-when command with a missing script path fails with FAIL command"
chk paths-only '- Done-when: `bash tests/nope.test.sh` → exit 0'
if [ "$RC" -eq 1 ] && has 'FAIL command:'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a Done-when command with an existing script path passes"
chk paths-only '- Done-when: `bash tests/run.sh` → exit 0'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "--mode paths-only ignores a missing symbol, a bad quote and Pins"
chk paths-only 'Pins: 0123456789abcdef0123456789abcdef01234567
The helper `renderGadget` at `src/app.js:1` — `nothing like this`.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "URLs, absolute paths, ~ paths and glob tokens in backticks are skipped"
chk full 'See `https://example.com/a/b`, `/etc/hosts`, `~/x/y`, `src/*.js` and `src/<name>.js`.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a gitignored path (specs/) is skipped"
chk full 'The plan is in `specs/foo/plan.md`.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a directory that is a tree on the ref passes"
chk full 'Tests live in `tests/` and sources in `src`.'
if [ "$RC" -eq 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a product name such as Node.js or Vue.js is not a missing path"
chk full 'The runner needs `Node.js` and the UI uses `Vue.js`.'
if [ "$RC" -eq 0 ] && [ "$(nfail)" = 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "the script prints one FILE <name> <line-count> <byte-count> line per input"
printf 'a\nb\nc\n' > "$WORK/three.md"
OUT=$(cd "$WORK" && "$BASH_BIN" "$GC" --repo "$REPO" --ref HEAD --mode full three.md 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has 'FILE three.md 3 6'; then pass; else fail "rc=$RC out=$OUT"; fi

t "several input files are checked in one call"
printf 'See `src/app.js`.\n' > "$WORK/a.md"; printf 'See `src/gone.js`.\n' > "$WORK/b.md"
OUT=$(cd "$WORK" && "$BASH_BIN" "$GC" --repo "$REPO" --ref HEAD --mode full a.md b.md 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has 'FILE a.md' && has 'FILE b.md' && has 'FAIL path: src/gone.js'; then pass; else fail "rc=$RC out=$OUT"; fi

t "a ref that does not resolve exits 2"
printf 'x\n' > "$WORK/in.md"
OUT=$(cd "$WORK" && "$BASH_BIN" "$GC" --repo "$REPO" --ref no-such-ref --mode full in.md 2>&1); RC=$?
if [ "$RC" -eq 2 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a missing input file exits 2"
OUT=$(cd "$WORK" && "$BASH_BIN" "$GC" --repo "$REPO" --ref HEAD --mode full nope.md 2>&1); RC=$?
if [ "$RC" -eq 2 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a bad mode or no input file exits 2"
OUT=$(cd "$WORK" && "$BASH_BIN" "$GC" --repo "$REPO" --ref HEAD --mode weird in.md 2>&1); rc1=$?
OUT=$(cd "$WORK" && "$BASH_BIN" "$GC" --repo "$REPO" --ref HEAD --mode full 2>&1); rc2=$?
if [ "$rc1" -eq 2 ] && [ "$rc2" -eq 2 ]; then pass; else fail "rc1=$rc1 rc2=$rc2"; fi

finish
