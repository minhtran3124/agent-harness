#!/bin/bash
# Shared matcher for the git-command PreToolUse hooks.
#
# Detects a `git … commit` (or push) invocation inside a shell command string
# for the common wrappings: leading `cd`, env assignments, or wrappers
# (command/sudo/env), and git global options (-C, -c, --flags).
# This closes the `^git commit` anchor bypass (DR-1): `cd x && git commit`,
# `git -C dir commit`, `git -c k=v commit`, `command git commit`,
# `echo done; git commit` are all detected; `echo "git commit"`,
# `echo "x; git commit y"`, `git log --grep=commit`, and `git commit-graph write`
# are correctly ignored.
#
# KNOWN UNCAUGHT (out of scope — full shell parsing is intentionally not done):
# subshell/group/substitution forms `(git commit)`, `{ git commit; }`,
# `$(git commit)`, backticks; indirection `sh -c '…'`, `xargs git commit`;
# an absolute path `/usr/bin/git commit`; a quoted command word `"git" commit`.
# These are far rarer than the DR-1 forms and are not treated as supported.
#
# Design notes:
#   - Splits on shell separators && || ; | & by pure bash parameter expansion
#     (NOT sed: BSD/macOS sed does not turn `\n` into a newline in the
#     replacement, so a sed split would silently break on macOS).
#   - Tokenizes each segment with `read -ra` (no pathname globbing, unlike
#     `set --`). Full shell quote parsing is intentionally NOT attempted — the
#     subcommand always appears before any commit-message text, so whitespace
#     tokenization is sufficient to identify the invocation.
#   - bash 3.2 compatible (macOS default): no `declare -A`, no `grep -P`,
#     no `mapfile`, no GNU-only sed.
#
# Usage from a hook:
#   source "$(cd "$(dirname "$0")" && pwd)/lib/git-command.sh"
#   hook_cmd_is_git_commit "$COMMAND"          || exit 0
#   hook_cmd_is_git_commit_or_push "$COMMAND"  || exit 0

# _git_subcommand_in <command-string> <subcmd> [subcmd...]
# Returns 0 if any &&/||/;/|/&-separated segment is a git invocation whose
# subcommand exactly equals one of the given subcommands.
_git_subcommand_in() {
  local cmd="$1"; shift
  local wanted=" $* "   # space-padded list, matched with a word glob below

  # Drop quoted spans first, so a separator or `git commit`-looking text INSIDE a
  # commit message or an `echo "…"` string cannot forge a spurious segment
  # (e.g. `echo "step 1; git commit later"` must NOT match). A real
  # `git commit -m "msg; more"` still matches — the invocation is outside quotes.
  # Unbalanced quotes are left as-is. Portable sed: BRE char classes only, no
  # `\n` in the replacement (BSD/macOS sed would not expand it).
  local s
  s=$(printf '%s' "$cmd" | sed -e "s/'[^']*'//g" -e 's/"[^"]*"//g')

  # Split on shell command separators -> newlines (pure bash; order matters:
  # replace the two-char operators before their single-char subsets).
  s="${s//&&/$'\n'}"; s="${s//||/$'\n'}"
  s="${s//;/$'\n'}";  s="${s//|/$'\n'}"; s="${s//&/$'\n'}"

  local seg
  while IFS= read -r seg; do
    local -a toks=()
    IFS=$' \t' read -ra toks <<< "$seg"
    local n=${#toks[@]} i=0

    # Skip leading prefix tokens: `cd PATH`, env assignments (FOO=bar), wrappers.
    while [ "$i" -lt "$n" ]; do
      case "${toks[$i]}" in
        cd)                                 i=$((i+2)) ;;
        command|builtin|exec|sudo|nice|env) i=$((i+1)) ;;
        [A-Za-z_]*=*)                       i=$((i+1)) ;;
        *)                                  break ;;
      esac
    done

    # The command word must be `git`.
    [ "$i" -lt "$n" ] && [ "${toks[$i]}" = "git" ] || continue
    i=$((i+1))

    # Skip git global options: -C DIR, -c K=V, and any other -flag.
    while [ "$i" -lt "$n" ]; do
      case "${toks[$i]}" in
        -C|-c) i=$((i+2)) ;;
        -*)    i=$((i+1)) ;;
        *)     break ;;
      esac
    done

    # The next token is the subcommand; match it exactly.
    [ "$i" -lt "$n" ] || continue
    case "$wanted" in
      *" ${toks[$i]} "*) return 0 ;;
    esac
  done <<< "$s"

  return 1
}

hook_cmd_is_git_commit()         { _git_subcommand_in "$1" commit; }
hook_cmd_is_git_commit_or_push() { _git_subcommand_in "$1" commit push; }
