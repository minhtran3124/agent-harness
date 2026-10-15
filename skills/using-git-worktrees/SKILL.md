---
name: using-git-worktrees
description: Set up or verify an isolated worktree before implementation-plan execution. Detect existing isolation first, prefer the harness-native worktree tool, and use a safe git fallback only when needed.
allowed-tools: Read, Bash(git *), Bash(ls *), Bash(skills/using-git-worktrees/scripts/detect-isolation.sh*), Bash(bash skills/using-git-worktrees/scripts/detect-isolation.sh*), Bash(bash scripts/deploy-harness.sh *)
---

# Using Git Worktrees

Announce that you are setting up an isolated workspace. Run
`skills/using-git-worktrees/scripts/detect-isolation.sh` before you create anything. Act on its
result:

- `linked-worktree`: report the path and branch. Use this worktree. A detached head needs a branch
  before finish.
- `submodule`: do not misclassify it as an isolated worktree. Follow its own repository policy.
- `main-worktree`: create isolation as below.

## Create isolation

Use the native worktree tool if the harness provides one. Do not create untracked state that the
harness cannot manage. In Claude Code, call `EnterWorktree` with `name: "<type>/<kebab-slug>"`, so
that the tool itself creates the worktree under `.claude/worktrees/`. Do not create a checkout by
hand and enter it with `path`. A path outside `.claude/worktrees/` raises a "permission-root
relocation" confirmation on every entry.

If feature-intake already cut `<type>/<slug>` (it holds the intent commit), do these steps:

1. Switch the main checkout off `<type>/<slug>` with `git -C <main checkout> switch <base>`.
   Untracked spec files stay.
2. Then, inside the new worktree, run `git reset --keep <type>/<slug>` and
   `git branch -M <type>/<slug>`.
3. In this case, the PR still targets `<base>`.

Otherwise, do these steps:

1. The tool names the branch `worktree-<name>` (with `/` written as `+`), not `<type>/<slug>`.
   Rename it with `git branch -m <type>/<slug>`.
2. Immediately after entering, before any edit, compare `git rev-parse HEAD` with
   `git rev-parse <base>` (the branch the PR will target).
3. If they differ, run `git reset --keep <base>`. This command stops instead of discarding local
   changes.

Only when no native tool exists, use this fallback. Choose an existing `.worktrees/` (preferred) or
`worktrees/` location, or the location documented in `CLAUDE.md`. If none exists, ask before you
choose a root. Ensure the chosen parent is ignored before running:

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
skill. `finishing-a-development-branch` owns the final PR flow.
