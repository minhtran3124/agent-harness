---
name: finishing-a-development-branch
description: Use when implementation is complete and tests pass — runs the targeted test suite, then pushes the branch and opens a PR against the base branch. Creates the PR only; it never merges and never discards work.
---

# Finishing a Development Branch

## Overview

Complete development work by verifying tests, then opening a pull request.

**Core principle:** Verify tests → Push → Open PR → Report URL.

This skill **only creates a PR**. It never merges, never force-pushes, and never discards work — a human reviews and merges the PR.

**Announce at start:** "I'm using the finishing-a-development-branch skill to open a PR for this work."

## The Process

### Step 1: Verify Tests

Invoke the **test-runner** sub-agent to run the test suite. Pass it the list of files changed on the current branch so it can target the minimal relevant test set.

#### 1a. Identify changed files

```bash
git diff --name-only $(git merge-base HEAD main)...HEAD -- '*.py'
```

Use these paths to determine which test files to run (e.g. changes to `app/repositories/user.py` → run `tests/repositories/test_user.py`).

#### 1b. Run tests

Launch the **test-runner** sub-agent with the project's test runner. Use whatever this repo
actually uses — detect it, don't assume a stack. For **this** repo (harness-skills) that is:

```bash
bash scripts/run-tests.sh
```

For an application repo, run the targeted test files with the project's runner (e.g.
`pytest <test_files> -x`, `npm test`, `go test ./...`); fall back to the full suite when no
targeted subset applies.

#### 1c. Report results

Present a structured summary:

```
Test Report
───────────────────────────────
Result:  ✅ N passed / ❌ N failed
Files:   tests/path/to/test_file.py, ...
Runner:  test-runner sub-agent
───────────────────────────────
```

#### 1d. Handle failures

- **All pass** → proceed to Step 2.
- **Failures** → report the tracebacks, attempt to fix the failing code, then re-invoke the test-runner to confirm the fix. Repeat up to **2 retries**. If tests still fail after retries, stop and ask the user how to proceed (fix manually, skip tests, or abort).

Do NOT skip this step. Never push code with failing tests.

### Step 2: Determine Base Branch

```bash
# Try common base branches
git merge-base HEAD main 2>/dev/null
```

If the base branch is not mentioned in chat, default to `main`. Only ask ("This branch split from `main` — is that correct?") if there is a concrete signal it split from something else.

### Step 3: Push and Open PR

1. **Mark the plan shipped** — run Step 4. This updates `specs/<slug>/PLAN.md`, which is **tracked** in git, so stage and commit the status change with the work (it lands in the branch/PR). If no plan matches, skip silently.
1b. **`CHANGELOG.md` + `VERSION` — who bumps depends on whether this repo has the post-merge automation.** Check for `.github/workflows/post-merge-maintenance.yml` (paired with `scripts/bookkeeping.sh`):
   - **Automation present (the harness-skills meta-repo):** do **NOT** bump by hand. The workflow owns it end-to-end — on merge it runs `bookkeeping.sh`, which bumps `VERSION`, inserts the dated CHANGELOG section, and appends the trust-metrics + audit-log rows, all parsed from the merged `SUMMARY.md`. A manual pre-bump double-counts: `bookkeeping.sh` bumps again from the value you set (skipping a version) and orphans your `## [Unreleased]` bullet. This matches `feature-intake` → "Do NOT hand-append the ledger. CI records it on merge." Your job is a correct `SUMMARY.md`, then review the bookkeeping PR after merge.
   - **Automation absent (a consuming project — the harness deploys this skill but not `bookkeeping.sh`/the workflow):** bump manually, as there is nothing else to do it. When the change is user-visible (a new/changed skill or hook, a schema change, a fix worth announcing), add a bullet under `## [Unreleased]` and bump root `VERSION` per the CHANGELOG's own rule (patch = fix/docs · minor = new/changed skill or hook contract · major = breaking workflow/schema change). Skip for purely internal docs/research. Commit these with the work so the PR carries them.

   See `docs/solutions/harness/manual-version-bump-collides-with-event-sourced-bookkeeping.md` (the double-bump this scoping prevents).
2. Push to remote: `git push -u github <current_branch>`.
3. Invoke the **create-pr** skill to generate `.pr-body.md`.
4. Create the PR with `gh pr create` against `<base_branch>`, using the generated template content for the body.
5. Return the PR URL to the user. **Stop here** — do not merge.

If a PR already exists for this branch, push the new commits and report the existing PR URL instead of creating a duplicate.

### Step 4: Mark the plan shipped

Runs as the first action of Step 3, before the push.

> Why this step exists: `status:` in `specs/<slug>/PLAN.md` records the plan lifecycle (`proposed` → `active` at execution start → `shipped` here). This is the **`shipped`** transition — a **committed** signal (`specs/` is tracked, so the transition is committed with the rest) that anyone reading the branch/PR can see the feature reached a PR. The edit auto-re-renders `PLAN.html` via `render-plan-on-write.sh` (`PLAN.html` itself is gitignored). Leaving it stale is the root cause of status drift across `specs/`.

#### 4a. Resolve the plan for this branch

```bash
branch=$(git branch --show-current)
slug=${branch#*/}                       # strip the <type>/ prefix (feat|fix|docs|chore|refactor|test|perf|ci) — see using-git-worktrees Branch Naming
ls specs/"$slug"/PLAN.md 2>/dev/null || ls specs/*/PLAN.md
```

- Exact match → use `specs/<slug>/PLAN.md`.
- No exact match → pick the `specs/*/PLAN.md` whose frontmatter `slug:` or title best matches the branch. If ambiguous, ask the user which plan this branch implements.
- No plan at all → **skip Step 4** (don't block the push).

#### 4b. Set status + append log

In the resolved `PLAN.md`:

1. Set the frontmatter to `status: shipped`. Canonical values are **only** `proposed | active | paused | shipped` — never invent others (`complete`, `done`, `ready-for-execution` are invalid and get silently dropped by the renderer).
2. Append one entry to the `## Status Log` (or numbered `## N. Status Log`) section, using today's date:

   ```markdown
   - YYYY-MM-DD — shipped via `<branch>` (PR #NNN)
   ```

Stage and commit this edit — `specs/` is tracked, so the status update lands in the branch/PR and persists for anyone who reads it (only the derived `PLAN.html` is gitignored).

## Quick Reference

| Step | Action | Blocker? |
|------|--------|----------|
| 1 | Run tests | Yes — must pass to proceed |
| 2 | Detect base branch | No — default to `main` |
| 3 | Push + open PR (no merge) | No |
| 4 | Mark plan `shipped` + log | No — skip if no plan matches |

## Red Flags

**Never:**
- Push code with failing tests
- **Merge the PR** — this skill only opens it; a human merges
- Force-push (`--force`) without explicit user request
- Use `git add -A` or `git add .` (may include secrets or junk files)
- Discard or `git clean` work — this skill never deletes work
- Amend an existing commit — always create a new one

**Always:**
- Run tests before pushing
- Stage files by name, not by wildcard
- Show the PR URL after creation
- Default to `main` as base branch when not specified
- Set the matching plan's `status: shipped` using only canonical status values, and commit it (`specs/` is tracked, so the transition is committed with the work)

## Integration

### Skills

- **create-pr** skill — creates a PR template and fills it with the current branch

### Sub Agents

- **test-runner** sub-agent — runs tests and reports results
