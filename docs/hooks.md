# Hooks and permissions

The short hook table is in `CLAUDE.md`; `scripts/lint-doc-truth.sh` keeps that table in step with
`plugins/harness/hooks/` and its `hooks.json`. The harness has five small hooks plus a `permissions.deny` list. Everything else is judgment, not
a mechanical gate.

## Hook details

In the `CLAUDE.md` table, wired (✅) means registered in `plugins/harness/hooks/hooks.json` and firing; dormant (⬜)
means present on disk but not registered. Each hook is registered in exec form (`bash` plus the script path under `${CLAUDE_PLUGIN_ROOT}/hooks/`), so it needs no execute bit at run time. All hooks except `merge-guard.sh` fail open (`merge-guard.sh` fails closed, see its section): a missing `jq`/`git`, or a
payload they cannot parse, lets the action through.

### `secrets-scan.sh` (PreToolUse, Bash)

Acts only on a `git commit` command. Scans the staged diff and the staged file names and exits 2 on a hit.
`Verifies:` the staged diff matches a short list of secret patterns (`sk-` keys, AWS `AKIA` keys, `password=`, `api_key=`,
`client_secret=` and similar assignments), and that no `*.env` file is staged. Test files, `*.example`, `*.md`
and `docs/` are not scanned. `Does not verify:` that a clean diff holds no secret; it is a pattern match,
not a scanner. It reads the index when it runs, so `git add x && git commit` in one Bash call is checked
against what was staged before that call. Stage in one call and commit in the next.

### `merge-guard.sh` (PreToolUse, Bash)

Blocks a PR merge unless the PR base is a `feat/*` branch or the owner approves that one PR (see below). It acts on `gh pr merge` and `gh api .../pulls/<n>/merge`
(at command position, after `&&`, `;`, `|`, `( )`, braces or env assignments; it uses the same segment splitter as
`clean-worktrees.sh`, so text in a heredoc or quoted string that only mentions a merge is ignored). For every PR number
in every merge segment it reads the live base with `gh pr view <n> --repo <r> --json baseRefName` and the repo default
branch with `gh repo view`. It allows the merge only when the base matches `feat/*` and is not the default branch.
`main`, `master`, `develop`, `development`, `staging`, `production`, `release/*`, `release-*`, the default branch and any
other name are denied. It exits 2 with the reason on stderr.

**Owner approval for one PR into base.** The one exception is a single plain `gh pr merge <n> --repo o/r --match-head-commit <head sha>` (the flag must equal the head the hook reads, so a later push cannot ride the approval; no `--auto`,
one PR, the only merge in the command, not `gh api`) whose base is `main`, `master`, `develop`, `development`, `staging`,
`production`, `release/*`, `release-*` or the repo default branch. The hook reads the base and the head commit
(`--json baseRefName,headRefOid`; the head must be 40 hex characters) and prints `permissionDecision: "ask"` with the
reason `Merge PR #<n> of <repo> into <base> at <head sha>?`. Claude Code shows the owner a confirmation prompt, and the
owner approves in it; the agent cannot answer it. The approval covers that one call only: no session-wide or multi-PR
approval exists. `permission_mode` must be `default`, `acceptEdits`, `auto` or `bypassPermissions`; a missing, unknown
or `dontAsk` mode, and a subagent or workflow agent (payload carries `agent_id`), are denied. Probe (headless
`claude -p`): under `default`, `auto` and `bypassPermissions` an `ask` is not turned into an allow; with no one to
answer, Claude Code returns it as a denial. So no `UserPromptSubmit` token fallback exists. The hook never outputs
`allow`. The owner's `!` or terminal merge stays as before.

**It fails closed, unlike the other hooks (ADR: fail-closed merge guard).** Once it has seen a merge, any doubt denies:
no `gh`, no `jq`, no PR number, no `--repo` (`GH_REPO` does not count), a `gh` error, empty or bad output, a `gh` call that
stalls (killed after 10 s; the whole hook has a 20 s budget under its 30 s `timeout`). It also denies `--auto`,
`gh api graphql ... mergePullRequest`, `{owner}/{repo}` placeholders in a `gh api` path, a merge inside `bash -c`, `eval`,
`xargs` or another wrapper, a merge that is not at command position (`command gh`, `/usr/bin/gh`, backticks), and
`gh alias set|import` next to the word merge. Any denied segment blocks the whole command. A Bash call that is not a merge
exits 0 before any parsing, so it costs nothing. There is no environment-variable bypass.
`Verifies:` the PR base and default branch of every judged merge. `Does not verify:` the owner's own `!` or terminal
merges (the hook never sees them), a local `git merge`, a merge through the web UI or another client, a command built at
run time, or whether the PR is ready (the workflow gate checks that). Local mode has no PRs, so the guard does not apply there.

### `pr-opened.sh` (PostToolUse, Bash)

After a `gh pr create`, adds a reminder to the model's context to run the review workflow on the new PR
(inside a subagent it says to hand the PR number back). It only reminds; it never blocks.

### `clean-worktrees.sh` (PostToolUse, Bash; SessionStart)

Removes the worktree and local branch of merged branches. It first runs `git fetch -q --prune <remote>`
(a failed fetch, for example offline, does not stop it). It has two modes.

- **PostToolUse** acts only on a real merge command: `gh pr merge <n>` or `gh api .../pulls/<n>/merge`, at command position
  (at the start, or after `&&`, `;`, `|` or env assignments). Text inside a heredoc or a quoted string is ignored, so an
  issue body, commit message or `echo` that only mentions the phrase does nothing. The scope is that one PR: the hook
  looks it up with `gh pr view <n> --json state,headRefName`. With no number in the command it uses the PR of the current
  branch; if that lookup fails it exits silently and cleans nothing.
- **SessionStart** (`clean-worktrees.sh SessionStart`, no payload) sweeps every branch, so a PR merged on the GitHub web is cleaned
  at the next session start. It returns what it removed as `additionalContext`. It is registered in its own group with
  matcher `startup` (not on resume, clear or compact) and a 30 second `timeout`, so a slow network cannot stall session start. The session's own branch and worktree are skipped, and so is any worktree that another running process has as its working directory (found through `/proc`, or `lsof` where there is no `/proc`).
- The SessionStart sweep has a time budget (`CLEAN_BUDGET` seconds, default 20, under the 30s hook timeout; `0` turns it off; a non-numeric value is treated as `0`, with no warning). It is checked before each branch, so no branch is left half-cleaned; the summary then says `stopped` and the next sweep finishes the rest.
- Run by hand with no argument, it sweeps every branch and prints plain text.

A branch is removed by the first rule that fits:

1. **Merged PR, exact tip** (needs `gh`): a merged PR whose head commit equals the local tip. This also covers squash merges, which
   are not in git history. It uses `git branch -D`; this is the only forced delete. The exact tip match is the guard: a branch with
   a commit after the merge is kept.
2. **`worktree-*` agent branch**: no worktree has it checked out and its tip is contained in a `<remote>/*` branch
   (`<remote>/HEAD` does not count). Deleted with `git branch -d`.
3. **No `gh`**: the upstream is gone and the tip is an ancestor of `<remote>/main`. Deleted with `git branch -d`. If
   `<remote>/main` is missing, no rule applies and the branch is kept.

`git worktree remove` has no force flag: it refuses a worktree with changes or a lock. The hook never touches `main`, `master`,
`develop`, `development`, `staging`, `production`, `release/*`, `release-*`,
a `CLEAN_KEEP` name, the current branch (checked before every rule), or the worktree the session runs in.

Settings (space-separated lists), set in the `env` block of `.claude/settings.json`:

| Variable | Default | Effect |
|---|---|---|
| `CLEAN_REMOTE` | `origin` | Remote used for the fetch, rule 2, rule 3 and `CLEAN_RECREATE` |
| `CLEAN_KEEP` | empty | Extra protected branch names, added to `main master`, the long-lived names above and the current branch |
| `CLEAN_STRICT` | empty | Globs (for example `run/*`). A match is removed only by rule 1 (exact-tip merged PR), never by rules 2 or 3 |
| `CLEAN_RECREATE` | empty | Base branches to recreate (a name with a leading dash, a glob or an invalid ref name, and long-lived names such as `develop` or `release/*`, are skipped; the push is never forced): when `git ls-remote` says the name is missing (exit 2), push `<remote>/main` as that branch. Any other `ls-remote` failure does nothing |

```json
{
  "env": {
    "CLEAN_KEEP": "automation workflow",
    "CLEAN_STRICT": "run/*",
    "CLEAN_RECREATE": "automation"
  }
}
```

### `session-rules.sh` (SessionStart)

A plugin has no rules component, so this hook prints `plugins/harness/rules/behavior.md` as the
`additionalContext` of the SessionStart JSON envelope. It uses no `jq` (the text is escaped with `sed`
and `awk`). A missing rule file prints nothing and exits 0. Whether a model obeys imperative text
delivered this way is not verified in a live session.

## One fixed hook set

The plugin registers one fixed hook set in `plugins/harness/hooks/hooks.json`: `session-rules.sh`, `secrets-scan.sh`, `pr-opened.sh` and `clean-worktrees.sh` (PostToolUse and SessionStart). Claude Code merges them with the user's and the project's hooks. The repo's own `settings.json` wires no hooks, or each would run twice (`tests/scripts/settings-wiring.test.sh` checks it). To develop the plugin, run `claude --plugin-dir plugins/harness`.

## Permissions

The root `settings.json` carries a `permissions.deny` list (no `allow` rules). The plugin cannot ship it, so `/harness:setup` merges these rules into a consuming project's `.claude/settings.json` with `merge-deny.sh`:

| Rule | Blocks |
|---|---|
| `Read(./.env)`, `Read(./.env.*)` | Reading a `.env` file in the project root |
| `Edit(./.env)`, `Edit(./.env.*)` | Writing a `.env` file (the `Edit` rule covers every file-writing tool) |
| `Bash(git push --force*)`, `Bash(git push -f*)` | Force pushes |
| `Bash(git push * main)`, `Bash(git push * master)` | Pushing to the default branch |
| `Bash(git push *:main)`, `Bash(git push *:master)` | Refspec pushes such as `HEAD:main` |
| `Bash(git push *:refs/heads/main)`, `Bash(git push *:refs/heads/master)` | Full-ref refspec pushes such as `HEAD:refs/heads/main` |
| `Bash(git push * +main)`, `Bash(git push * +master)` | Forced refspec pushes such as `+main` |

`merge-deny.sh` keeps every existing key and deny entry, adds only the missing rules, and writes nothing when none is missing. It needs `jq` and refuses a settings file that is not valid JSON.
`/harness:setup` offers no allow rule and never writes the owner's local settings file. To let a run merge ticket PRs into `feat/<slug>`, the owner adds an allow rule for `gh pr merge` to their own settings; the `merge-guard.sh` hook still blocks every merge whose PR base is not `feat/*`. The root `settings.json` has no allow rules.
Deny rules are glob patterns on the command text (`*` matches any text, spaces included); they are a guard against mistakes, not a sandbox. The list holds 14 rules: the original 8 plus 6 push-form rules (ADR 0131). Claude Code splits a compound command at `&&`, `||`, `;`, `|`, `|&`, `&` and newlines and denies it when any part matches, so `git push origin main; echo ok` is denied and `git push origin feat/x; git checkout main` is allowed ([permissions docs](https://code.claude.com/docs/en/permissions)).
`tests/scripts/push-deny-forms.test.sh` (spike #530, ADR 0131) prints a BLOCKED/ALLOWED line for each push form, using a local bare remote. Its header records which forms the real Claude Code matcher denied.

### Known gaps

A glob matches text, so each form below is ALLOWED and moves `main` on the remote. Each one is a gap row in the test, which fails if the gap closes. The reason a glob cannot express it is given per form:

- Trailing flags, `git push origin HEAD:main --no-verify` or `git push origin main --no-verify`: every rule ends in the branch name. A rule that tolerates text after the name (`* main *`) also matches a push of `feat/x` followed by any argument that is the word `main`, and a glob cannot tell a flag from another argument.
- Full ref without a colon, `git push origin refs/heads/main` and `+refs/heads/main`: a glob has no word boundary. `*refs/heads/main` needs further rules for trailing flags and quotes, and a variant that ends in `*` also matches `refs/heads/mainline`.
- Quoting the branch or refspec, `git push origin "main"`, `'HEAD:main'`, `HEAD:"main"`, `ma"in"`: the shell removes the quotes after the rule is matched, and a glob needs one rule per quote placement.
- Bare `git push` or `git push <remote>` when the upstream (or `push.default`) is `main`: the command text has no branch name to match.
- `git -C <dir> push ...`, or any other text before `push`: every rule starts with `git push`. The permissions docs list `git -C . push` as a form a prefix rule does not match.
- Aliases, and a refspec built in a shell variable (`B=main; git push origin "$B"`): the name is not in the command text.

Separator forms such as `git push origin main;` or `git push origin HEAD:main && echo ok` are not gaps: Claude Code splits the compound command and the first part matches (observed with the real matcher, ADR 0131).

The rules are a mistake guard, not a sandbox.

### Server-side branch protection (manual owner step)

TODO(owner): enable branch protection on main in GitHub (require PR, block force-push and deletion). The workflow never changes GitHub settings.

## What is intentionally not enforced

Nothing blocks a commit for missing evidence; nothing blocks an edit on `main`; nothing preloads `docs/solutions/` at session start. Read `docs/solutions/INDEX.md` when you plan. Per-role models, effort and tools come from the agent files' frontmatter only.

## Rule-loading tiers

Today the plugin ships one always-on file (`rules/behavior.md`, one always-on file) and no path-scoped ones. The nine other rules were removed in v5. `session-rules.sh` delivers it at session start. `tests/scripts/rule-loading-tiers.test.sh` keeps this inventory exact against `plugins/harness/rules/*.md` and tests the delivery.
