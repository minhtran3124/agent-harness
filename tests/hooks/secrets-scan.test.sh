#!/bin/bash
# Contract tests for hooks/secrets-scan.sh: blocks `git commit` with a secret or a .env staged;
# passes clean commits and every other command.
source "$(dirname "$0")/../lib.sh"

H=secrets-scan.sh
COMMIT=$(json_cmd 'git commit -m x')

R=$(new_repo $H)
stage "$R" src/app.py 'KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"'
t "staged fake API key blocks a git commit (exit 2)"
run_hook "$R" $H "$COMMIT"
if [ "$RC" = 2 ] && printf '%s' "$OUT" | grep -q 'BLOCKED'; then pass; else fail "rc=$RC out=$OUT"; fi

t "git -C . commit is also blocked"
run_hook "$R" $H "$(json_cmd 'git -C . commit -m x')"
if [ "$RC" = 2 ]; then pass; else fail "rc=$RC"; fi

t "the same staged secret does not block a non-commit command"
run_hook "$R" $H "$(json_cmd 'git status')"
if [ "$RC" = 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

R=$(new_repo $H)
stage "$R" src/app.py 'print("hello")'
t "clean staged change passes"
run_hook "$R" $H "$COMMIT"
if [ "$RC" = 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

R=$(new_repo $H)
stage "$R" .env 'FOO=bar'
t "staged .env file blocks a git commit"
run_hook "$R" $H "$COMMIT"
if [ "$RC" = 2 ] && printf '%s' "$OUT" | grep -q '\.env'; then pass; else fail "rc=$RC out=$OUT"; fi

R=$(new_repo $H)
stage "$R" tests/fixture.py 'KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"'
t "a placeholder secret under tests/ is not scanned"
run_hook "$R" $H "$COMMIT"
if [ "$RC" = 0 ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "a malformed payload fails open"
run_hook "$R" $H 'not json'
if [ "$RC" = 0 ]; then pass; else fail "rc=$RC"; fi

finish
