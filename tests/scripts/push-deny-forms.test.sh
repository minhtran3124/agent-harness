#!/bin/bash
# Spike for #530: which `git push` forms to main/master does the settings.json deny list block?
# Claude Code's permission matcher cannot run offline, so this emulates the prefix glob with bash
# `case` (`*` matches any text, spaces included) over the deny list read from settings.json. Each
# form is also really run against a local bare remote (no network) to confirm it moves the remote
# ref, so a form that is ALLOWED and reaches main/master is tagged GAP.
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

# denied <command> -> 0 when any settings.json Bash(...) deny glob matches it
denied() {
  local cmd="$1" rule glob
  while IFS= read -r rule; do
    glob=${rule#Bash(}; glob=${glob%)}
    # shellcheck disable=SC2254
    case "$cmd" in $glob) return 0 ;; esac
  done < <(jq -r '.permissions.deny[] | select(startswith("Bash("))' "$ROOT/settings.json")
  return 1
}

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

for br in main master; do
  for f in "git push origin $br" "git push origin HEAD:$br" "git push origin HEAD:refs/heads/$br" \
           "git push origin +$br" "git push origin +HEAD:$br" "git push --force origin $br" "git push -f origin $br" \
           "git push origin :$br" "git push origin refs/heads/$br" "git push origin +refs/heads/$br" \
           "git push origin $br --no-verify" "git push origin HEAD:$br --no-verify" \
           "git push origin \"$br\"" "git push origin 'HEAD:$br'" "git push origin \"HEAD:$br\""; do
    row expect-blocked "$f" "$br"
  done
done
for br in main master; do
  row gap "git push" "$br"
  row gap "git push origin" "$br"
  row gap "git -C @CLONE@ push origin $br" "$br"
  row gap "git push origin ma\"in\"" "$br"
  row gap "B=$br; git push origin \"\$B\"" "$br"
done
row control "git push origin feat/x" feat/x

t "docs/hooks.md known gaps do not list the blocked delete form"
if sed -n '/^### Known gaps/,/^### Server-side/p' "$ROOT/docs/hooks.md" | grep -q 'git push origin :main'; then
  fail "docs/hooks.md lists 'git push origin :main' as a gap, but the deny list blocks it"
else pass; fi

finish
