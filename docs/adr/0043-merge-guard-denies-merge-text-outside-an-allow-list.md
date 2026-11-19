---
ticket: 680
stage: design
status: accepted
confidence: medium
decided_by: worker (trial-p3), design input from the Fable 5.2 advisor; owner answers on #680
date: 2026-11-19
---

# 0043. merge-guard denies merge-like text outside an allow list of commands that never run their arguments

## Context

`merge-guard.sh` denied a merge hidden in a shell string by a list of wrapper names (bash, env, nice,
flock, ...). The security review of PR #679 showed that the list cannot be complete: an interpreter
(`python3 -c`, `perl -e`, `awk 'BEGIN{system()}'`), `find -exec`, `git -c alias.x='!...'` and a
backslash-newline inside the word `merge` all reached `gh pr merge` with no owner prompt. The owner's
answers on #680: the default for merge-like text in a command that is not on the allow list is deny;
backslash-newline joining is in scope, inside quotes and heredocs too; run-time encoding (#675) stays
out of scope; the false positives must stay under a small ceiling, measured by a replay of 30 days of
the owner's session transcripts.

## Options

- Rule of the ticket only: deny when a removed quoted string holds merge-like text and the command is
  not on the allow list. Smaller, but `echo '<merge>' | python3 -`, `X='<merge>'; python3 -c "$X"` and
  unquoted forms (`git -c alias.x=!gh\ pr\ merge ...`) stay open.
- Allow list plus a call-level rule (chosen): the splitter reads the text the way the shell does, and
  merge-like text is allowed only where no command of the call can run it.
- Whole-call allow list (every command of a call with merge-like text must be listed): simplest, far
  over the ceiling (`gh pr view --json ... && npm test`).

## Decision

1. The splitter (one awk pass) reads backslash escapes, backslash-newline (in code, in double quotes
   and in unquoted heredocs, not in single quotes), `$( )` inside double quotes as code, and heredoc
   end words exactly as bash and zsh do. Anything it cannot read like the shell is denied.
2. In an unquoted heredoc body, a simple `$( ... )` (no quote, backtick, `#`, `<`, nested `$` form or
   `case`; backslash parity as the shell reads it) is parsed as code like any other command; the rest
   of the body is data. Any other body with an expansion is one opaque command that is never listed.
   A heredoc line that starts with the end word and a `)` is denied: bash ends a heredoc inside `$( )`
   there, and this reader does not.
3. Merge-like text means `gh ... merge`, `pr merge`, `pulls/<n>/merge`, `repos/.../merges` and the
   GraphQL merge mutations as substrings. Only an explicit list of harmless words is removed first
   (`mergeable`, `merged`, `mergeState...`, `mergeCommit`, `merge-base`, `merge_method`, `merge-guard`),
   so an interpreter escape such as `merge\x20` still counts.
4. R1: a command that is not a judged merge and not on the allow list is denied when its own text,
   quoted text, heredoc or here-string holds merge-like text.
5. R2: when any command of the call holds merge-like text, every other command of the call must be on
   the allow list (text flows through pipes, variables and files).
6. R3: an assignment in front of a command, with merge-like text, is denied (it reaches the command's
   environment).
7. R4: merge-like text plus a write (redirection or tee) to a sure git hook or config target (`.git`,
   a `hooks/` directory, husky, lefthook, `pre-commit`, a `gh/` directory) is denied, with or without
   git in the call. A write to a possible config target (a hidden name, `config`, a `*rc` file, a
   target with `$`, a backtick, a glob or a quoted name, or any write after a `cd` to such a place) is
   denied only next to git, gh or rg. A write to `notes.md` next to `git add` is allowed.
8. The allow list: shell builtins and text tools that run nothing (echo, printf without -v, cat,
   grep, jq, sleep, seq, ...); `sed` only as `sed -n '<range>p'`; git read and commit subcommands;
   `git fetch|ls-remote|push` only without merge-like text and without `--upload-pack`, `--exec`,
   `--receive-pack`; gh read and write-text subcommands (`pr create|comment|edit --body`, `issue ...`).
   A command with any expansion other than `$NAME`, `${NAME}`, a special parameter or `$( )` is never
   listed: `$((`, `$[`, `${s:x}`, `${a[x]}` and `${!x}` in bash and `${(e)x}`, `$~x` in zsh evaluate a
   value, and an array subscript or `(e)` in that value runs `$( )` (checked in bash and zsh).
   After replay rounds 1 and 2: a write target is judged by its file name (a data name such as `.md`
   under `$VAR/` is not configuration; `VAR=` set earlier in the call is resolved), `.git/info/*` is
   not a sure target, a function defined in the call may be called (its body is judged; a name that is
   already a command is not honored), case patterns after `;;` are data, an escaped backtick in an
   unquoted heredoc is text, and an assignment in front of git, gh or rg takes it off the list.
9. The wrapper list stays as a second net: it is the only check that denies a merge built at run time
   behind bash -c, eval or xargs, which holds no literal text.

## Why

The allow list is closed where the wrapper list was open: an unknown program is denied next to merge
text instead of allowed. Rules 2, 3, 7 and the widened list keep the benign denials under the owner's
ceiling; the advisor's first version denied 193 distinct benign-looking commands of 2,160 in the
replay, most from rule 7 on any file write, from read-only git next to `gh api ... .mergeable_state`,
and from opaque heredocs in `gh pr create --body "$(cat <<EOF ...)"`.

## Consequences

- A command that runs an interpreter, `sed` with a script, `awk`, `find`, `git -c` or `xargs` next to
  merge-like text is denied; the owner runs it by hand or the agent splits it into two Bash calls.
- A plain merge continued over two lines with a backslash-newline is one merge again and can be put
  to the owner (the old hook denied it).
- Not closed (#675): a merge built at run time with no literal text (`gh pr m{e..e}rge`, `$'...'`,
  base64, string slicing in an interpreter), a file written in one Bash call and run in the next.
  Branch protection on `main` is the backstop.
- The Write tool is not a Bash call: a hook or config file written with it is not seen by R4.
- The awk is a small shell reader; a desync it does not detect turns code into data. Each new case
  needs a test in `tests/hooks/merge-guard.test.sh`.

## Review

The design was reviewed before code by the advisor agent (Opus 5.5): go with changes. Its findings 1
(zsh `${(e)x}`, `$~x` and bash `${!x}`; two of them reproduced here), 2 (keep substring matching), 3
(husky, lefthook, `cd .git/hooks`), 4 (heredoc parity, strict spans, `EOF)` desync; reproduced in bash)
and 5 (`sed` getopt reordering) are folded into items 2, 3, 7 and 8 above, each with a test.

## How to reverse

Revert the PR of #680: the hook returns to the wrapper list alone. No other file depends on the new
rules.
