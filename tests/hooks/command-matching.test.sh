#!/bin/bash
# Unit tests for the shared git-command matcher (hooks/lib/git-command.sh).
# Pins DR-1: every wrapped/prefixed git-commit form is detected, and adjacent
# non-commit forms do not false-fire.
source "$(dirname "$0")/../lib.sh"
source "$ROOT/hooks/lib/git-command.sh"

sc()  { t "commit: $1";        if hook_cmd_is_git_commit "$1"; then pass; else fail "expected match"; fi; }
snc() { t "not-commit: $1";    if hook_cmd_is_git_commit "$1"; then fail "unexpected match"; else pass; fi; }
scp() { t "commit|push: $1";   if hook_cmd_is_git_commit_or_push "$1"; then pass; else fail "expected match"; fi; }
sncp(){ t "not c|p: $1";       if hook_cmd_is_git_commit_or_push "$1"; then fail "unexpected match"; else pass; fi; }

# ── DR-1 bypass forms: MUST be detected ──────────────────────────────
sc 'git commit -m x'
sc 'cd x && git commit'
sc 'cd /tmp && git commit -m "msg"'
sc 'git -C dir commit'
sc 'git -C . commit'
sc 'git -c k=v commit'
sc 'git -c a=b -C d commit'
sc 'command git commit'
sc 'echo done; git commit'
sc 'sudo git commit -m x'
sc 'FOO=bar git commit'
sc 'git --no-pager commit'
sc 'true && git commit || echo fail'

# ── Adjacent / safe forms: MUST NOT false-fire ──────────────────────
snc 'echo "git commit"'
snc 'git log --grep=commit'
snc 'git commit-graph write'
snc 'git show'
snc 'git status'
snc ''
snc 'cd git-commit-dir && ls'
snc '# git commit'
snc 'echo git commit is coming'
# F1 — separators/subcommand text inside quoted strings must NOT forge a match
snc 'echo "hello; git commit the code now"'
snc "echo 'a && git commit b'"
snc 'echo "step 1; git commit later" && ls'
# ...but a real commit whose MESSAGE contains a separator still matches
sc 'git commit -m "msg; more"'
sc 'git commit -m "wip" && echo done'

# ── commit-or-push (check-untracked-py) ─────────────────────────────
scp 'git push'
scp 'cd x && git push origin main'
scp 'git commit -m x'
scp 'git -C d push'
sncp 'git fetch'
sncp 'echo git push'

finish
