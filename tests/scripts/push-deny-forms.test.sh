#!/bin/bash
# Spike for #530: which `git push` forms to main/master does the settings.json deny list block?
#
# MATCHER EVIDENCE. Claude Code docs (https://code.claude.com/docs/en/permissions, "Wildcard
# patterns", "Compound commands", "What a Bash rule doesn't match") say: `*` in a Bash rule matches
# any text including spaces; a deny rule applies when ANY subcommand of a compound command matches
# (separators && || ; | |& & and newline); `git -C . push` and `git 'push'` are not matched.
# This file emulates that with bash `case` (`*` = any text) after splitting the command on those
# separators. The emulation is a model; the REAL matcher was run once on 2026-10-31 (claude 2.1.314,
# --model haiku, project .claude/settings.json holding exactly these 14 rules, local bare remote,
# --permission-mode default --allowedTools Bash --setting-sources project). Observed by the real matcher:
#   DENIED, remote unmoved: git push origin HEAD:main | HEAD:refs/heads/main | +main  (and the three master forms)
#   DENIED:                 git push origin HEAD:main; echo ok     (compound is split, the first part matches)
#   ALLOWED, remote moved:  git push origin HEAD:main --no-verify | git -C . push origin HEAD:main
#                           git push origin 'HEAD:main' | git push origin HEAD:"main"
#   ALLOWED, no push:       git push origin feat/x; git checkout main     (control)
#   ALLOWED, remote unmoved: bare `git push` from a feat/x branch (push.default refused it; not run from main)
# The emulation below agrees with every one of those observations (the rows carry the same forms).
# CAVEAT: only valid while every Bash(...) deny rule uses `*` as its sole metacharacter (checked below).
# Each form is also really run against a local bare remote (no network); a form that is ALLOWED and
# moves main/master is tagged GAP.
# Output: one line per form, BLOCKED|ALLOWED [GAP] <form>.
source "$(dirname "$0")/../lib.sh"

if ! command -v jq >/dev/null 2>&1; then
  t "push-deny-forms (need jq)"; skip "jq is not installed"
  finish
fi

export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
TMP=$(mktemp -d); _CLEANUP_DIRS+=("$TMP")
BARE="$TMP/remote.git"; CLONE="$TMP/clone"; SEED="$TMP/seed"

git init -q --bare "$BARE"
git -C "$BARE" symbolic-ref HEAD refs/heads/main
git init -q "$SEED"
git -C "$SEED" config user.name test; git -C "$SEED" config user.email test@test
git -C "$SEED" checkout -q -b main 2>/dev/null || git -C "$SEED" checkout -q main
git -C "$SEED" commit -q --allow-empty -m base
git -C "$SEED" branch master
git -C "$SEED" push -q "$BARE" main master
git clone -q "$BARE" "$CLONE" 2>/dev/null
git -C "$CLONE" config user.name test; git -C "$CLONE" config user.email test@test
git -C "$CLONE" branch -q --track master origin/master 2>/dev/null
BASE=$(git -C "$BARE" rev-parse refs/heads/main)

# denied_one <single command> -> 0 when any settings.json Bash(...) deny glob matches it
denied_one() {
  local cmd="$1" rule glob
  while IFS= read -r rule; do
    glob=${rule#Bash(}; glob=${glob%)}
    # shellcheck disable=SC2254
    case "$cmd" in $glob) return 0 ;; esac
  done < <(jq -r '.permissions.deny[] | select(startswith("Bash("))' "$ROOT/settings.json")
  return 1
}

# denied <command> -> 0 when any subcommand matches (the docs: a deny rule applies when any part of a compound command matches)
denied() {
  local part
  while IFS= read -r part; do
    part=${part#"${part%%[![:space:]]*}"}; part=${part%"${part##*[![:space:]]}"}
    [ -n "$part" ] || continue
    denied_one "$part" && return 0
  done < <(printf '%s\n' "$1" | sed -e 's/&&/\n/g; s/||/\n/g; s/|&/\n/g; s/[;|&]/\n/g')
  return 1
}

# plain_star_glob <glob> -> 0 when the glob has no bash metacharacter other than `*`
plain_star_glob() { case "$1" in *[\?\[\\]*) return 1 ;; *) return 0 ;; esac; }

t "emulation holds: every Bash deny rule uses only the * wildcard"
bad=""
while IFS= read -r rule; do
  g=${rule#Bash(}; g=${g%)}
  plain_star_glob "$g" || bad="$bad [$rule]"
done < <(jq -r '.permissions.deny[] | select(startswith("Bash("))' "$ROOT/settings.json")
if [ -z "$bad" ]; then pass; else fail "rules use ?, [ or backslash, so the bash case emulation may differ from Claude Code:$bad"; fi

t "emulation guard rejects a ? [ or backslash glob"
if plain_star_glob 'git push ? main' || plain_star_glob 'git push [a]* main' || plain_star_glob 'git push \* main'; then
  fail "plain_star_glob accepted a non-star metacharacter"
elif plain_star_glob 'git push * main'; then pass; else fail "plain_star_glob rejected a star-only glob"; fi

t "emulation splits compound commands (a deny rule applies when any part matches)"
if denied "git push origin HEAD:main; echo ok" && denied "echo a && git push origin +main" \
   && ! denied "git push origin feat/x; git checkout main"; then pass; else fail "compound splitting is wrong"; fi

# reaches <form> <branch> -> 0 when running the form moves refs/heads/main or master on the remote
reaches() {
  local form="$1" b="$2" cmd
  git -C "$BARE" update-ref refs/heads/main "$BASE"; git -C "$BARE" update-ref refs/heads/master "$BASE"
  if [ "$b" = feat/x ]; then
    git -C "$CLONE" checkout -q -f -B feat/x main
  else
    git -C "$CLONE" checkout -q -f "$b"; git -C "$CLONE" update-ref "refs/remotes/origin/$b" "$BASE"
  fi
  git -C "$CLONE" reset -q --hard "$BASE"
  git -C "$CLONE" commit -q --allow-empty -m change
  cmd=${form//@CLONE@/$CLONE}
  (cd "$CLONE" && eval "$cmd") >/dev/null 2>&1
  [ "$(git -C "$BARE" rev-parse refs/heads/main)" != "$BASE" ] || [ "$(git -C "$BARE" rev-parse refs/heads/master)" != "$BASE" ]
}

# row <kind> <form> <branch>   kind: expect-blocked | gap (must stay ALLOWED and reach main) | control
row() {
  local kind="$1" form="$2" b="$3" cmd state tag=""
  cmd=${form//@CLONE@/<dir>}
  if denied "$cmd"; then state=BLOCKED; else state=ALLOWED; fi
  if [ "$state" = ALLOWED ] && reaches "$form" "$b"; then tag=" GAP"; fi
  printf '%s%s %s\n' "$state" "$tag" "$cmd"
  t "$kind: $cmd"
  case "$kind" in
    expect-blocked) if [ "$state" = BLOCKED ]; then pass; else fail "$cmd is allowed by the deny list"; fi ;;
    control)        if [ "$state" = ALLOWED ] && [ -z "$tag" ]; then pass; else fail "control should be ALLOWED and not reach main: $state$tag"; fi ;;
    gap)            if [ "$state" = ALLOWED ] && [ "$tag" = " GAP" ]; then pass
                    else fail "documented gap changed ($state$tag): a closed gap belongs in expect-blocked and out of docs/hooks.md Known gaps"; fi ;;
  esac
}

# Blocked: the 2 original forms, the 6 owner-confirmed forms (:B, :refs/heads/B, +B), their combinations
for br in main master; do
  for f in "git push origin $br" "git push origin HEAD:$br" "git push origin HEAD:refs/heads/$br" \
           "git push origin +$br" "git push origin +HEAD:$br" "git push --force origin $br" "git push -f origin $br" \
           "git push origin :$br" "git push origin +HEAD:refs/heads/$br" \
           "git push origin $br; echo ok" "git push origin HEAD:$br && echo ok"; do
    row expect-blocked "$f" "$br"
  done
done

# Known gaps (docs/hooks.md "Known gaps"): ALLOWED and they move the remote. Each row fails if the gap closes.
for br in main master; do
  row gap "git push origin HEAD:$br --no-verify" "$br"            # trailing flag: no rule ends in the branch
  row gap "git push origin $br --no-verify" "$br"                 # trailing flag after a plain branch
  row gap "git push origin refs/heads/$br" "$br"                  # full ref without a colon or plus
  row gap "git push origin +refs/heads/$br" "$br"                 # plus full ref: `+main` rule needs the name right after +
  row gap "git push origin \"$br\"" "$br"                         # quoted branch
  row gap "git push origin 'HEAD:$br'" "$br"                      # quoted refspec
  row gap "git push origin HEAD:\"$br\"" "$br"                    # quote inside the refspec
  row gap "git push origin ma\"in\"" "$br"                        # quote splits the word
  row gap "git push" "$br"                                        # upstream is main
  row gap "git push origin" "$br"
  row gap "git -C @CLONE@ push origin $br" "$br"                  # text before `push`
  row gap "B=$br; git push origin \"\$B\"" "$br"                  # variable refspec
done

# Controls: legitimate commands that must stay allowed
row control "git push origin feat/x" feat/x
row control "git push origin feat/x; git checkout main" feat/x    # review point [55]: main mentioned after a feature push
row control "git push origin feat/x && git merge main" feat/x
row control "git push origin feat/x; gh pr create --base main" feat/x
row control "git push origin \"feat/domain\"" feat/x
row control "git push origin 'feat/domain'" feat/x
row control "git push origin \"feat/foo-master\"" feat/x
for n in maintenance main-fix mainline master-plan; do
  row control "git push origin HEAD:refs/heads/$n" feat/x
  row control "git push origin HEAD:$n" feat/x
done

t "docs/hooks.md known gaps do not list the blocked delete form"
if sed -n '/^### Known gaps/,/^### Server-side/p' "$ROOT/docs/hooks.md" | grep -q 'git push origin :main'; then
  fail "docs/hooks.md lists 'git push origin :main' as a gap, but the deny list blocks it"
else pass; fi

finish
