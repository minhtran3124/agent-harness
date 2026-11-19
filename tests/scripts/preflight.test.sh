#!/usr/bin/env bash
# plugins/harness/skills/pd-autopilot/scripts/preflight.sh checks the setup an autopilot run needs before
# triage: git, gh, jq and python3 in PATH, a gh login, and specs/ ignored in the checkout. Each case
# runs it with a private fake PATH (a git symlink and stubs for gh, jq and python3) and a private git
# config, so the result does not depend on the host's gh login, jq or global gitignore.
set -uo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
pre="$root/plugins/harness/skills/pd-autopilot/scripts/preflight.sh"
bash_bin=$(command -v bash)
git_bin=$(command -v git)

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

fails=0
ok() { printf '  ok    %s\n' "$1"; }
bad() { printf '  FAIL  %s\n' "$1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; fails=$((fails + 1)); }

if [ ! -f "$pre" ]; then
  bad "preflight.sh exists" "missing $pre"
  echo; echo "preflight.test.sh: FAILED"; exit 1
fi

# mkenv <name> <with_jq 0|1> <specs_ignored 0|1>: sets bin and repo.
mkenv() {
  local d="$work/$1"
  mkdir -p "$d/bin" "$d/repo"
  bin="$d/bin"; repo="$d/repo"
  ln -s "$git_bin" "$bin/git"
  printf '#!%s\nexit 0\n' "$bash_bin" > "$bin/python3"
  # gh auth status exits with FAKE_GH_AUTH_RC; any other gh call exits 0.
  # shellcheck disable=SC2016  # the stub expands its own arguments
  printf '#!%s\n[ "$1 $2" = "auth status" ] && exit "${FAKE_GH_AUTH_RC:-0}"\nexit 0\n' "$bash_bin" > "$bin/gh"
  [ "$2" = 1 ] && printf '#!%s\nexit 0\n' "$bash_bin" > "$bin/jq"
  chmod +x "$bin"/python3 "$bin"/gh
  [ -f "$bin/jq" ] && chmod +x "$bin/jq"
  "$git_bin" -C "$repo" init -q
  [ "$3" = 1 ] && printf '/specs/\n' > "$repo/.gitignore"
  return 0
}
# runpre <gh_auth_rc> [args...]: sets out and rc.
runpre() {
  local auth=$1; shift
  out=$(env -i PATH="$bin" HOME="$work/home" XDG_CONFIG_HOME="$work/xdg" \
    GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 FAKE_GH_AUTH_RC="$auth" \
    "$bash_bin" "$pre" "$@" 2>&1)
  rc=$?
}

mkenv allok 1 1; runpre 0 --repo-dir "$repo"
if [ "$rc" = 0 ] && [ "$out" = 'preflight: ok' ]; then ok "all checks pass -> exit 0 and 'preflight: ok'"
else bad "all checks pass -> exit 0 and 'preflight: ok'" "rc=$rc out=$out"; fi

mkenv nojq 0 1; runpre 0 --repo-dir "$repo"
if [ "$rc" = 1 ] && [ "$out" = 'missing: jq' ]; then ok "jq absent -> exit 1 and 'missing: jq'"
else bad "jq absent -> exit 1 and 'missing: jq'" "rc=$rc out=$out"; fi

mkenv noauth 1 1; runpre 1 --repo-dir "$repo"
if [ "$rc" = 1 ] && [ "$out" = 'missing: gh auth' ]; then ok "gh auth fails -> exit 1 and 'missing: gh auth'"
else bad "gh auth fails -> exit 1 and 'missing: gh auth'" "rc=$rc out=$out"; fi

mkenv noign 1 0; runpre 0 --repo-dir "$repo"
if [ "$rc" = 1 ] && [ "$out" = 'missing: specs/ ignore' ]; then ok "specs/ not ignored -> exit 1 and 'missing: specs/ ignore'"
else bad "specs/ not ignored -> exit 1 and 'missing: specs/ ignore'" "rc=$rc out=$out"; fi

mkenv two 0 0; runpre 1 --repo-dir "$repo"
if [ "$rc" = 1 ] && [ "$out" = $'missing: jq\nmissing: gh auth\nmissing: specs/ ignore' ]; then ok "several failures -> one line each, in check order"
else bad "several failures -> one line each, in check order" "rc=$rc out=$out"; fi

mkdir -p "$work/notrepo"
mkenv norepo 1 0; runpre 0 --repo-dir "$work/notrepo"
if [ "$rc" = 1 ] && [ "$out" = 'missing: git repo' ]; then ok "a dir that is not a git repo -> exit 1 and 'missing: git repo'"
else bad "a dir that is not a git repo -> exit 1 and 'missing: git repo'" "rc=$rc out=$out"; fi

mkenv nodir 1 1; runpre 0
if [ "$rc" = 2 ]; then ok "no --repo-dir -> exit 2"; else bad "no --repo-dir -> exit 2" "rc=$rc out=$out"; fi

runpre 0 --repo-dir "$work/does-not-exist"
if [ "$rc" = 2 ]; then ok "--repo-dir that does not exist -> exit 2"; else bad "--repo-dir that does not exist -> exit 2" "rc=$rc out=$out"; fi

# hostcase <name> <origin url|''> <host the fake gh accepts>: gh auth status exits 0 only for that --hostname.
hostcase() {
  mkenv "$1" 1 1
  # shellcheck disable=SC2016  # the stub expands its own arguments
  printf '#!%s\n[ "$1 $2" = "auth status" ] || exit 0\n[ "$3 $4" = "--hostname %s" ] && exit 0\nexit 1\n' "$bash_bin" "$3" > "$bin/gh"
  [ -n "$2" ] && "$git_bin" -C "$repo" remote add origin "$2"
  runpre 0 --repo-dir "$repo"
}
for c in 'ghe-https|https://ghe.example.com/o/r.git|ghe.example.com' \
         'ghe-ssh|git@ghe.example.com:o/r.git|ghe.example.com' \
         'ghe-sshurl|ssh://git@ghe.example.com:2222/o/r.git|ghe.example.com' \
         'gh-https|https://github.com/o/r.git|github.com' \
         'no-origin||github.com'; do
  IFS='|' read -r name url host <<<"$c"
  hostcase "$name" "$url" "$host"
  if [ "$rc" = 0 ] && [ "$out" = 'preflight: ok' ]; then ok "$name: gh auth checked on $host -> exit 0"
  else bad "$name: gh auth checked on $host -> exit 0" "rc=$rc out=$out"; fi
done
# An SSH config alias resolves through ssh -G before gh sees it (fake ssh maps github-work -> github.com).
for c in 'alias-scp|git@github-work:o/r.git' 'alias-sshurl|ssh://git@github-work/o/r.git'; do
  IFS='|' read -r name url <<<"$c"
  mkenv "$name" 1 1
  # shellcheck disable=SC2016  # the stub expands its own arguments
  printf '#!%s\n[ "$1 $2" = "-G github-work" ] && { echo "user git"; echo "hostname github.com"; exit 0; }\necho "hostname $2"\n' "$bash_bin" > "$bin/ssh"
  # shellcheck disable=SC2016
  printf '#!%s\n[ "$1 $2" = "auth status" ] || exit 0\n[ "$3 $4" = "--hostname github.com" ] && exit 0\nexit 1\n' "$bash_bin" > "$bin/gh"
  ln -sf "$(command -v awk)" "$bin/awk"
  chmod +x "$bin/ssh"
  "$git_bin" -C "$repo" remote add origin "$url"
  runpre 0 --repo-dir "$repo"
  if [ "$rc" = 0 ] && [ "$out" = 'preflight: ok' ]; then ok "$name: SSH alias github-work checked on github.com -> exit 0"
  else bad "$name: SSH alias github-work checked on github.com -> exit 0" "rc=$rc out=$out"; fi
done

hostcase ghe-wronghost 'https://ghe.example.com/o/r.git' github.com
if [ "$rc" = 1 ] && [ "$out" = 'missing: gh auth' ]; then ok "origin on ghe.example.com, login only on github.com -> 'missing: gh auth'"
else bad "origin on ghe.example.com, login only on github.com -> 'missing: gh auth'" "rc=$rc out=$out"; fi

echo
if [ "$fails" -eq 0 ]; then echo "preflight.test.sh: ok"; exit 0; fi
echo "preflight.test.sh: FAILED ($fails)"; exit 1
