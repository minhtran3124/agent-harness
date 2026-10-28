# Hooks and permissions

The short hook table is in `CLAUDE.md`; `scripts/lint-doc-truth.sh` keeps that table in step with
`hooks/` and `settings.json`. Harness v5 (epic #338, issue #349) replaced the old commit gate and its
companions with three small hooks plus a `permissions.deny` list. Everything else is judgment, not
a mechanical gate.

## Hook details

In the `CLAUDE.md` table, wired (✅) means registered in `settings.json` and firing; dormant (⬜)
means present on disk but not registered. All three hooks fail open: a missing `jq`/`git`, or a
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

After a `gh pr merge` (or a merge made through `gh api .../pulls/<n>/merge`), removes the worktree and
local branch of every branch whose PR is merged on GitHub with the same tip commit as the local branch,
and tells the model what it removed. It never uses a force flag: `git worktree remove` refuses a worktree with changes or a lock, and
`git branch -d` refuses a branch git does not see as merged (for example a squash merge; the hook reports it and
leaves it). It never touches `main`, `master`, the checked-out branch of the main checkout, or the worktree the
session is running in. Run by hand with no argument, it prints the same report.

## One fixed hook set

`scripts/install-harness.sh` and `scripts/deploy-harness.sh` install one fixed hook set: every hook wired in this repo's root `settings.json` (`secrets-scan.sh`, `pr-opened.sh`, `clean-worktrees.sh`). The earlier `--profile minimal|standard|strict` choice and the `<target>/.claude/.harness-profile` file are gone; both scripts still accept `--profile` so old install commands keep working, but print a one-line warning and ignore it, and a re-sync deletes a leftover `.harness-profile`. Re-sync prunes retired harness hooks (`commit-gate.sh`, `branch-isolation-guard.sh`, `session-knowledge.sh`, `model-config.sh`, the `lib` helper dir) from the consumer's `.claude/hooks/` and `.claude/settings.json` through the deployed-file manifest, drops event keys left empty, and preserves the consumer's own hooks.

## Permissions

The root `settings.json` carries a `permissions.deny` list (no `allow` rules):

| Rule | Blocks |
|---|---|
| `Read(./.env)`, `Read(./.env.*)` | Reading a `.env` file in the project root |
| `Edit(./.env)`, `Edit(./.env.*)` | Writing a `.env` file (the `Edit` rule covers every file-writing tool) |
| `Bash(git push --force*)`, `Bash(git push -f*)` | Force pushes |
| `Bash(git push * main)`, `Bash(git push * master)` | Pushing to the default branch |

`permissions.deny` reaches a consumer only on the first install. A re-sync merges the `.hooks` part of `settings.json` only and leaves the consumer's `permissions` alone, so the consumer owns their permissions after install. To get the deny list in an existing install, copy it by hand.
Deny rules are prefix patterns on the command text; they are a guard against mistakes, not a sandbox.

## What is intentionally not enforced

The v4 commit gate, the branch-isolation guard and the session-knowledge loader are gone, together with the lane, escalation, receipt and run-state checks they ran. Nothing blocks a commit for a missing `SUMMARY.md`, a low lane, or a pending escalation; nothing blocks an edit on `main`; nothing preloads `docs/solutions/` at session start. Read `docs/solutions/INDEX.md` when you plan. Per-role models come from `agents/runtime-bindings.json` only; the `harness-models.json` override is gone.

## Rule-loading tiers

A file in `rules/` with `paths:` frontmatter is contextual and loads on demand. A file without it auto-loads every session. Adding `paths:` to a rule that lacks it **removes** it from the always-on set. That is a behavior change, not a formatting fix.

Today the source tree contains one always-on file (`behavior.md`) and no path-scoped ones. The nine other rules were removed in v5. `tests/scripts/rule-loading-tiers.test.sh` keeps this inventory exact against `rules/*.md`. A re-sync prunes the removed rule files from a consumer's `.claude/rules/` and leaves the consumer's own rule files alone.

## Re-sync note

Re-sync (`scripts/install-harness.sh` / `scripts/deploy-harness.sh`) is conflict-guarded for protected files (e.g. `<path under rules/ or agents/>`, including any locally-generated per-repo files): a differing local copy is kept by default and the incoming version is written beside it as `<file>.harness-incoming` for review, instead of being silently overwritten. Pass `--overwrite-conflicts` to replace protected files with the incoming copy instead of keeping local.
