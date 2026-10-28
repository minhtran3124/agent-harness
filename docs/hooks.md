# Hooks and permissions

The short hook table is in `CLAUDE.md`; `scripts/lint-doc-truth.sh` keeps that table in step with
`plugins/harness/hooks/` and its `hooks.json`. The harness has four small hooks plus a `permissions.deny` list. Everything else is judgment, not
a mechanical gate.

## Hook details

In the `CLAUDE.md` table, wired (✅) means registered in `plugins/harness/hooks/hooks.json` and firing; dormant (⬜)
means present on disk but not registered. Each hook is registered in exec form (`bash` plus the script path under `${CLAUDE_PLUGIN_ROOT}/hooks/`), so it needs no execute bit at run time. All four hooks fail open: a missing `jq`/`git`, or a
payload they cannot parse, lets the action through.

### `secrets-scan.sh` (PreToolUse, Bash)

Acts only on a `git commit` command. Scans the staged diff and the staged file names and exits 2 on a hit.
`Verifies:` the staged diff matches a short list of secret patterns (`sk-` keys, AWS `AKIA` keys, `password=`, `api_key=`,
`client_secret=` and similar assignments), and that no `*.env` file is staged. Test files, `*.example`, `*.md`
and `docs/` are not scanned. `Does not verify:` that a clean diff holds no secret; it is a pattern match,
not a scanner. It reads the index when it runs, so `git add x && git commit` in one Bash call is checked
against what was staged before that call. Stage in one call and commit in the next.

### `pr-opened.sh` (PostToolUse, Bash)

After a `gh pr create`, adds a reminder to the model's context to run the review workflow on the new PR
(inside a subagent it says to hand the PR number back). It only reminds; it never blocks.

### `clean-worktrees.sh` (PostToolUse, Bash)

Acts only on a real merge command: `gh pr merge <n>` or `gh api .../pulls/<n>/merge`, at command position
(at the start, or after `&&`, `;`, `|` or env assignments). Text inside a heredoc or a quoted string is ignored, so an
issue body, commit message or `echo` that only mentions the phrase does nothing. The scope is that one PR: the hook
looks it up with `gh pr view <n> --json state,headRefName` and, if it is merged, removes the worktree and local
branch of that PR's branch when the PR has the same tip commit as the local branch, then tells the model what it
removed. With no number in the command it uses the PR of the current branch; if that lookup fails it exits
silently and cleans nothing. It never uses a force flag: `git worktree remove` refuses a worktree with changes or a lock, and
`git branch -d` refuses a branch git does not see as merged (for example a squash merge; the hook reports it and
leaves it). It never touches `main`, `master`, the checked-out branch of the main checkout, or the worktree the
session is running in. Run by hand with no argument, it sweeps every merged branch and prints the same report.

### `session-rules.sh` (SessionStart)

A plugin has no rules component, so this hook prints `plugins/harness/rules/behavior.md` as the
`additionalContext` of the SessionStart JSON envelope. It uses no `jq` (the text is escaped with `sed`
and `awk`). A missing rule file prints nothing and exits 0. Whether a model obeys imperative text
delivered this way is not verified in a live session.

## One fixed hook set

The plugin registers one fixed hook set in `plugins/harness/hooks/hooks.json`: `session-rules.sh`, `secrets-scan.sh`, `pr-opened.sh` and `clean-worktrees.sh`. Claude Code merges them with the user's and the project's hooks. The repo's own `settings.json` wires no hooks, or each would run twice (`tests/scripts/settings-wiring.test.sh` checks it). To develop the plugin, run `claude --plugin-dir plugins/harness`.

## Permissions

The root `settings.json` carries a `permissions.deny` list (no `allow` rules). The plugin cannot ship it, so `/harness:setup` merges these rules into a consuming project's `.claude/settings.json` with `merge-deny.sh`:

| Rule | Blocks |
|---|---|
| `Read(./.env)`, `Read(./.env.*)` | Reading a `.env` file in the project root |
| `Edit(./.env)`, `Edit(./.env.*)` | Writing a `.env` file (the `Edit` rule covers every file-writing tool) |
| `Bash(git push --force*)`, `Bash(git push -f*)` | Force pushes |
| `Bash(git push * main)`, `Bash(git push * master)` | Pushing to the default branch |

`merge-deny.sh` keeps every existing key and deny entry, adds only the missing rules, and writes nothing when none is missing. It needs `jq` and refuses a settings file that is not valid JSON.
`/harness:setup` can also offer one allow rule, `Bash(gh pr merge *)`, through `merge-allow.sh` into the owner's untracked local settings file. This is opt-in and needs a yes from the owner; the root `settings.json` still has no allow rules.
Deny rules are prefix patterns on the command text; they are a guard against mistakes, not a sandbox.

## What is intentionally not enforced

Nothing blocks a commit for missing evidence; nothing blocks an edit on `main`; nothing preloads `docs/solutions/` at session start. Read `docs/solutions/INDEX.md` when you plan. Per-role models, effort and tools come from the agent files' frontmatter only.

## Rule-loading tiers

Today the plugin ships one always-on file (`rules/behavior.md`, one always-on file) and no path-scoped ones. The nine other rules were removed in v5. `session-rules.sh` delivers it at session start. `tests/scripts/rule-loading-tiers.test.sh` keeps this inventory exact against `plugins/harness/rules/*.md` and tests the delivery.
