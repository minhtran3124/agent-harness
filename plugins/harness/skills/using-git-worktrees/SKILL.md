---
name: using-git-worktrees
description: Set up or verify an isolated git worktree from the right base for a manual run. Use when starting manual work. Workflows do not need it; they use `isolation: 'worktree'`.
allowed-tools: Read, Bash(git *), Bash(ls *), Bash(${CLAUDE_SKILL_DIR}/scripts/detect-isolation.sh*), Bash(bash ${CLAUDE_SKILL_DIR}/scripts/detect-isolation.sh*)
---

# Using Git Worktrees

Work on a change in its own worktree so the main checkout stays clean. This is for manual runs.
A Workflow gives each agent `isolation: 'worktree'` instead.

## Steps

1. Run `${CLAUDE_SKILL_DIR}/scripts/detect-isolation.sh`.
   - `linked-worktree`: you are already isolated. Report the path and branch. A detached head
     needs a branch before you finish.
   - `submodule`: follow that repository's own policy.
   - `main-worktree`: create one (step 2).
2. Create it from the right base. Use the harness worktree tool (`EnterWorktree`) if present.
   Otherwise: `git worktree add .worktrees/<name> -b <type>/<slug> <base>`. Use an ignored parent
   directory, and never nest a worktree inside another.
3. Check the base. A workflow agent's worktree starts from the main checkout HEAD, not from the
   base you want (`docs/adr/0001-workflow-capabilities.md`). Compare `git rev-parse HEAD` with
   `git rev-parse <base>` before any edit. If they differ, run `git reset --keep <base>`, which
   stops instead of discarding local changes.
4. Run the project's baseline tests and report any failure before you start.

## Auto mode

- The caller names the mode in the prompt: `Mode: interactive` (default) or `Mode: auto`.
- Interactive: you may ask the owner with AskUserQuestion, one batch at a time, each question with a
  recommended answer.
- Auto: never ask the owner. On any ambiguity (base branch, location) pick the recommended option
  and record it in `decisions[]`: `{title, context, options, decision, why, consequences,
  how_to_reverse, confidence: high|medium|low, needs_review: boolean}`. Do not write ADR files.
- Set `needs_advisor: true` with `advisor_question` when you are BLOCKED, have low confidence, or a
  decision affects other tickets or a public contract. The calling script runs the advisor. Do
  not spawn agents (`docs/adr/0001-workflow-capabilities.md`).
