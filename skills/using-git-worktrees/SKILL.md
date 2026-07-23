---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via the harness's native worktree tool or a git worktree fallback, with detection-first and safety verification
---

# Using Git Worktrees

Ensure work happens in an isolated workspace.

**Core principle:** Detect existing isolation → use the native worktree tool → fall back to `git worktree` only when no native tool exists. Never fight the harness.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Step 0 — Detect existing isolation

Check before creating anything, or you risk nesting a worktree inside a worktree.

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
git rev-parse --show-superproject-working-tree 2>/dev/null   # non-empty ⇒ submodule, not a worktree
```

`GIT_DIR != GIT_COMMON` is **also** true inside a git submodule — that is why the submodule probe
is not optional.

- **`GIT_DIR != GIT_COMMON` and not a submodule** → already isolated. Skip creation, go to Step 2.
  Report the path and branch (or note a detached HEAD, which needs a branch at finish time).
- **Otherwise** → a normal checkout; continue to Step 1.

## Step 1 — Create the workspace

**Native tool first.** If the harness exposes a worktree tool — `EnterWorktree` / `WorktreeCreate`,
a `/worktree` command, or a `--worktree` flag — **use it and skip the fallback**. It handles
directory placement, branch creation, and cleanup, and the harness can see and clean up the
result. Running `git worktree add` when a native tool exists creates phantom state the harness
cannot track.

**Fallback, only when no native tool exists:**

1. **Pick the location, do not assume it.** Reuse an existing `.worktrees/` or `worktrees/`
   (`.worktrees` wins if both exist), else the directory `CLAUDE.md` names
   (`grep -i "worktree.*director" CLAUDE.md`), else ask the user — offer project-local
   `.worktrees/` or a path outside the repo entirely. Defaulting silently splits worktrees
   across two roots, and `finishing-a-development-branch` then cleans up only one of them.
2. **Make sure it is ignored — and fix it if it is not.** `git check-ignore -q .worktrees`.
   If it is NOT ignored: add the pattern to `.gitignore` and commit that **first**, then
   create the worktree. Skipping this is not cosmetic: `git add -A` turns the untracked
   worktree into an embedded-repo **gitlink**, committing a broken entry that no hook catches
   (`git ls-files --others` reports the directory, never the files inside it).
3. `git worktree add <dir>/<branch> -b <branch>`, then `cd` into it and continue at Step 2.

## Step 2 — Deploy the harness into the worktree

Run this **from inside** the new workspace — every path into this step (already isolated,
native tool, or the fallback) has you standing in it, so the target is resolved from where you
are rather than carried in a variable set several steps earlier:

```bash
bash scripts/deploy-harness.sh --target "$(git rev-parse --show-toplevel)"
```

**Run this before anything else in the new workspace.** `.claude/` is gitignored (a derived
artifact), so a fresh worktree has no hooks, no skills, and no `settings.json` — the harness is
effectively broken there until this runs.

Then run whatever project setup the repo needs (detect it from the manifests present — do not
assume a stack) and confirm the test baseline is clean before implementing. If the baseline
already fails, report it and ask before proceeding; otherwise a pre-existing failure gets
mistaken for one you introduced.

## Branch naming

`<type>/<kebab-slug>` — Conventional Branch, mirroring Conventional Commits.

- **`<type>`**: `feat` · `fix` · `docs` · `chore` · `refactor` · `test` · `perf` · `ci`.
- **`<slug>`**: kebab-case, and it SHOULD equal the `specs/<slug>` slug for this work.
  `finishing-a-development-branch` resolves the plan by stripping the prefix
  (`slug=${branch#*/}`), so a matching slug makes that resolution exact. A ticket-prefixed slug
  carries its prefix through unchanged (e.g. `feat/gh-121-spec-folder-prefix`).

Examples: `feat/api-key-generation` · `fix/deploy-merge-invalid-json`. Never a bare name
(`auth`), a non-standard prefix (`feature/`, `bugfix/`), or spaces.

## Integration

- **Called by** `writing-plans` and `subagent-driven-development` (required before executing tasks).
- **Pairs with** `finishing-a-development-branch`, which opens the PR when the work is done.
