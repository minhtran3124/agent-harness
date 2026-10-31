#!/bin/bash
# Tests for scripts/check-tag-version.sh: a matching tag passes, a mismatched tag fails,
# tags below v5.1.0 are ignored, and the real repo's tags pass.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/check-tag-version.sh"
R=$(mktemp -d); _CLEANUP_DIRS+=("$R")
G=(git -C "$R" -c user.email=t@t -c user.name=t -c commit.gpgsign=false -c tag.gpgsign=false)
git -C "$R" init -q
echo 2.28.0 > "$R/VERSION"; "${G[@]}" add VERSION; "${G[@]}" commit -qm old
"${G[@]}" tag v4.0.0
echo 5.1.0 > "$R/VERSION"; "${G[@]}" commit -qam ok
"${G[@]}" tag v5.1.0

t "old tag with a wrong VERSION (v4.0.0) is ignored and a matching v5.1.0 passes"
bash "$SCRIPT" --root "$R" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 0 ]; then pass; else fail "want exit 0, got $rc"; fi

echo 5.2.0 > "$R/VERSION"; "${G[@]}" commit -qam bad
"${G[@]}" tag v5.2.1

t "a tag whose VERSION differs from the tag name exits 1"
out=$(bash "$SCRIPT" --root "$R" 2>&1); rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q 'v5.2.1'; then pass; else fail "rc=$rc out=$out"; fi

t "the script leaves the tag list unchanged"
if [ "$(git -C "$R" tag --list | tr '\n' ' ')" = "v4.0.0 v5.1.0 v5.2.1 " ]; then pass; else fail "tags changed"; fi

t "the current repo tags pass"
bash "$SCRIPT" --root "$ROOT" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 0 ]; then pass; else fail "want exit 0, got $rc"; fi

finish
