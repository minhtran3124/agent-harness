---
name: using-git-worktrees
description: Set up or verify an isolated worktree before implementation-plan execution. Detect existing isolation first, prefer the harness-native worktree tool, and use a safe git fallback only when needed.
---

# Using Git Worktrees

Announce that you are setting up an isolated workspace. Run
`skills/using-git-worktrees/scripts/detect-isolation.sh` before creating anything.

- `linked-worktree`: report the path and branch; use it (a detached head needs a branch before
  finish).
- `submodule`: do not misclassify it as an isolated worktree; follow its own repository policy.
- `main-worktree`: create isolation as below.

## Create isolation

Use a native worktree tool if the harness provides one; do not create untracked state the harness
cannot manage. Otherwise choose an existing `.worktrees/` (preferred) or `worktrees/` location,
or the location documented in `CLAUDE.md`; if none exists, ask before choosing a root. Ensure the
chosen parent is ignored before running:

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
