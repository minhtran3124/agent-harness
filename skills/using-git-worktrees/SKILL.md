---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via the harness's native worktree tool or a git worktree fallback, with detection-first and safety verification
---

# Using Git Worktrees

## Overview

Ensure work happens in an isolated workspace. **Detect existing isolation first. Then prefer the
harness's native worktree tool. Fall back to manual `git worktree` only when no native tool
exists.** Worktrees share the same repository, allowing work on multiple branches without switching.

**Core principle:** Detect → native tool → git fallback. Never fight the harness.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Step 0: Detect Existing Isolation

**Before creating anything, check whether you are already in an isolated workspace** — otherwise
you risk nesting a worktree inside a worktree.

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

**Submodule guard:** `GIT_DIR != GIT_COMMON` is *also* true inside a git submodule. Before
concluding "already in a worktree," verify you are not in a submodule:

```bash
# If this prints a path, you are in a submodule, not a worktree — treat as a normal repo.
git rev-parse --show-superproject-working-tree 2>/dev/null
```

- **If `GIT_DIR != GIT_COMMON` (and not a submodule):** you are already in a linked worktree.
  **Skip creation** — jump to Creation Step 3 (Project Setup). Report:
  - On a branch: "Already in isolated workspace at `<path>` on branch `<name>`."
  - Detached HEAD: "Already isolated at `<path>` (detached HEAD, externally managed) — branch creation needed at finish time."
- **If `GIT_DIR == GIT_COMMON` (or in a submodule):** you are in a normal repo checkout — continue.

## Step 1: Create the Workspace — Native Tool First

You have two mechanisms; try them **in this order**.

### 1a. Native worktree tool (preferred)

Do you have a harness-native way to create a worktree — a tool named like `EnterWorktree` /
`WorktreeCreate`, a `/worktree` command, or a `--worktree` flag? **If so, use it and skip the git
fallback** (then continue at Creation Step 3, Project Setup).

Native tools handle directory placement, branch creation, and cleanup, and the harness can see and
manage the result. Running `git worktree add` when a native tool exists creates phantom state the
harness can't track — the #1 mistake. Only proceed to 1b when no native tool is available.

### 1b. Git worktree fallback

**Only when 1a does not apply.** Use the Directory Selection → Safety Verification → Creation Steps
below to create the worktree manually with git.

## Directory Selection Process

Follow this priority order:

### 1. Check Existing Directories

```bash
# Check in priority order
ls -d .worktrees 2>/dev/null     # Preferred (hidden)
ls -d worktrees 2>/dev/null      # Alternative
```

**If found:** Use that directory. If both exist, `.worktrees` wins.

### 2. Check CLAUDE.md

```bash
grep -i "worktree.*director" CLAUDE.md 2>/dev/null
```

**If preference specified:** Use it without asking.

### 3. Ask User

If no directory exists and no CLAUDE.md preference:

```
No worktree directory found. Where should I create worktrees?

1. .worktrees/ (project-local, hidden)
2. ~/.config/superpowers/worktrees/<project-name>/ (global location)

Which would you prefer?
```

## Safety Verification

### For Project-Local Directories (.worktrees or worktrees)

**MUST verify directory is ignored before creating worktree:**

```bash
# Check if directory is ignored (respects local, global, and system gitignore)
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

**If NOT ignored:**

Per Jesse's rule "Fix broken things immediately":
1. Add appropriate line to .gitignore
2. Commit the change
3. Proceed with worktree creation

**Why critical:** Prevents accidentally committing worktree contents to repository.

### For Global Directory (~/.config/superpowers/worktrees)

No .gitignore verification needed - outside project entirely.

## Branch Naming

`$BRANCH_NAME` is not free-form. Use **`<type>/<kebab-slug>`** (Conventional Branch — mirrors
Conventional Commits):

- **`<type>`** is one of: `feat` · `fix` · `docs` · `chore` · `refactor` · `test` · `perf` · `ci`.
  Pick the type that matches the change's primary intent (same vocabulary the commit will use).
- **`<slug>`** is kebab-case and SHOULD equal the `specs/<slug>` slug for this work, so the branch
  is traceable to its plan. `finishing-a-development-branch` derives the plan by stripping the
  prefix (`slug=${branch#*/}`), so a matching slug makes that resolution exact.

Examples: `feat/api-key-generation` · `fix/deploy-merge-invalid-json` · `docs/worktree-naming`.

Do not use a bare name (`auth`), a non-standard prefix (`feature/…`, `bugfix/…`), or spaces.

## Creation Steps

### 1. Detect Project Name

```bash
project=$(basename "$(git rev-parse --show-toplevel)")
```

### 2. Create Worktree

```bash
# Determine full path
case $LOCATION in
  .worktrees|worktrees)
    path="$LOCATION/$BRANCH_NAME"
    ;;
  ~/.config/superpowers/worktrees/*)
    path="~/.config/superpowers/worktrees/$project/$BRANCH_NAME"
    ;;
esac

# Create worktree with new branch
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

### 3. Run Project Setup

**Harness first — always check for `scripts/deploy-harness.sh`:**

```bash
# Deploy .claude/ into the worktree (harness skills, hooks, rules, settings)
# .claude/ is gitignored (derived artifact) — worktrees won't have it without this step.
if [ -f scripts/deploy-harness.sh ]; then
  bash scripts/deploy-harness.sh --target "$path"
fi
```

This must run before anything else. Without it the worktree has no hooks, no skills, and
no `settings.json`, so the harness is effectively broken in that workspace.

Auto-detect and run appropriate package manager setup:

```bash
# Node.js
if [ -f package.json ]; then npm install; fi

# Rust
if [ -f Cargo.toml ]; then cargo build; fi

# Python
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then poetry install; fi

# Go
if [ -f go.mod ]; then go mod download; fi
```

### 4. Verify Clean Baseline

Run tests to ensure worktree starts clean:

```bash
# Examples - use project-appropriate command
npm test
cargo test
pytest
go test ./...
```

**If tests fail:** Report failures, ask whether to proceed or investigate.

**If tests pass:** Report ready.

### 5. Report Location

```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| Already in a linked worktree | Skip creation (Step 0) |
| In a submodule | Treat as normal repo (Step 0 guard) |
| Native worktree tool available | Use it (Step 1a) — do NOT `git worktree add` |
| No native tool | Git worktree fallback (Step 1b) |
| `.worktrees/` exists | Use it (verify ignored) |
| `worktrees/` exists | Use it (verify ignored) |
| Both exist | Use `.worktrees/` |
| Neither exists | Check CLAUDE.md → Ask user |
| Directory not ignored | Add to .gitignore + commit |
| Tests fail during baseline | Report failures + ask |
| No package.json/Cargo.toml | Skip dependency install |

## Common Mistakes

### Fighting the harness

- **Problem:** Running `git worktree add` when the harness already provides a native worktree tool (e.g. `EnterWorktree`) — creates phantom state the harness can't see or clean up
- **Fix:** Step 1a defers to the native tool; only fall back to git when none exists

### Skipping detection

- **Problem:** Creating a nested worktree inside an existing one
- **Fix:** Always run Step 0 (`git-dir` vs `git-common-dir`, + submodule guard) before creating anything

### Skipping ignore verification

- **Problem:** Worktree contents get tracked, pollute git status
- **Fix:** Always use `git check-ignore` before creating project-local worktree

### Assuming directory location

- **Problem:** Creates inconsistency, violates project conventions
- **Fix:** Follow priority: existing > CLAUDE.md > ask

### Proceeding with failing tests

- **Problem:** Can't distinguish new bugs from pre-existing issues
- **Fix:** Report failures, get explicit permission to proceed

### Hardcoding setup commands

- **Problem:** Breaks on projects using different tools
- **Fix:** Auto-detect from project files (package.json, etc.)

## Example Workflow

```
You: I'm using the using-git-worktrees skill to set up an isolated workspace.

[Check .worktrees/ - exists]
[Verify ignored - git check-ignore confirms .worktrees/ is ignored]
[Create worktree: git worktree add .worktrees/feat/auth -b feat/auth]
[Run npm install]
[Run npm test - 47 passing]

Worktree ready at /Users/jesse/myproject/.worktrees/auth
Tests passing (47 tests, 0 failures)
Ready to implement auth feature
```

## Red Flags

**Never:**
- Name a branch off-standard — use `<type>/<kebab-slug>` with a valid type (see Branch Naming); no bare names, no `feature/`/`bugfix/`, no spaces
- Create a worktree when Step 0 detects existing isolation (don't nest worktrees)
- Use `git worktree add` when a native worktree tool exists (Step 1a) — this is the #1 mistake
- Skip Step 1a and jump straight to the git fallback
- Create worktree without verifying it's ignored (project-local)
- Skip baseline test verification
- Proceed with failing tests without asking
- Assume directory location when ambiguous
- Skip CLAUDE.md check
- Skip `deploy-harness.sh --target` when `scripts/deploy-harness.sh` exists — the worktree will have no `.claude/` without it

**Always:**
- Run Step 0 detection first (+ submodule guard)
- Prefer the native worktree tool over the git fallback
- Follow directory priority: existing > CLAUDE.md > ask
- Verify directory is ignored for project-local
- Run `bash scripts/deploy-harness.sh --target "$path"` before package manager setup (if the script exists)
- Auto-detect and run project setup
- Verify clean test baseline

## Integration

**Called by:**
- **brainstorming** (Phase 4) - REQUIRED when design is approved and implementation follows
- **subagent-driven-development** - REQUIRED before executing any tasks
- **executing-plans** - REQUIRED before executing any tasks
- Any skill needing isolated workspace

**Pairs with:**
- **finishing-a-development-branch** - REQUIRED for cleanup after work complete
