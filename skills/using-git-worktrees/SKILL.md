---
name: using-git-worktrees
description: Set up or verify an isolated worktree before implementation-plan execution. Detect existing isolation first, prefer the harness-native worktree tool, and use a safe git fallback only when needed.
allowed-tools: Read, Bash(git *), Bash(ls *), Bash(skills/using-git-worktrees/scripts/detect-isolation.sh*), Bash(bash skills/using-git-worktrees/scripts/detect-isolation.sh*), Bash(bash scripts/deploy-harness.sh *)
---

# Using Git Worktrees

Announce that you are setting up an isolated workspace. Run
`skills/using-git-worktrees/scripts/detect-isolation.sh` before creating anything.

- `linked-worktree`: report the path and branch; use it (a detached head needs a branch before
  finish).
- `submodule`: do not misclassify it as an isolated worktree; follow its own repository policy.
- `main-worktree`: create isolation as below.

## Create isolation

Use the native worktree tool if the harness provides one; do not create untracked state the
harness cannot manage. In Claude Code, call `EnterWorktree` with `name: "<type>/<kebab-slug>"` so
the tool itself creates the worktree under `.claude/worktrees/`. Do not create a checkout by hand
and enter it with `path`: a path outside `.claude/worktrees/` raises a "permission-root relocation"
confirmation on every entry.

The tool names the branch `worktree-<name>` (with `/` written as `+`), not `<type>/<slug>`. Rename
it with `git branch -m <type>/<slug>`. Immediately after entering, before any edit, compare
`git rev-parse HEAD` with `git rev-parse <base>` (the branch the PR will target); if they differ,
run `git reset --keep <base>`, which stops instead of discarding local changes.

Only when no native tool exists, choose an existing `.worktrees/` (preferred) or `worktrees/`
location, or the location documented in `CLAUDE.md`; if none exists, ask before choosing a root.
Ensure the chosen parent is ignored before running:

```bash
git worktree add <parent>/<branch> -b <branch>
```

Use `<type>/<kebab-slug>` branch names and keep the slug equal to `specs/<slug>` where possible.
Never silently create a nested worktree or allow `git add -A` to capture one as a gitlink.

## Enter the workspace

From inside the selected workspace, deploy the derived harness first:

```bash
bash scripts/deploy-harness.sh --target "$(git rev-parse --show-toplevel)"
```

Then detect project setup from repository manifests and run its clean baseline. Report an existing
failure before implementation. `writing-plans` and `subagent-driven-development` require this
skill; `finishing-a-development-branch` owns the final PR flow.
