---
name: finishing-a-development-branch
description: Verify a finished branch, push it, and open a pull request with a structured body. Use when a branch is finished. Opens the PR only: never merges, force-pushes, discards work, or amends commits.
allowed-tools: Read, Write, Grep, Glob, Bash
---

# Finishing a Development Branch

## Steps

1. Find the branch, its base and the changes: `git branch --show-current`,
   `git diff --stat <base>...HEAD`. Ask the owner only if the base is unclear (interactive mode).
2. Verify. Run the repository's test command (`agents/PROJECT.md`, *Test execution*), or the
   targeted tests for the change. Fix failures and retry at most twice. Never push a failing branch.
3. Push without force: `git push -u origin <branch>`.
4. Open one PR against the base with `gh pr create`. Return the URL and stop. A human reviews and
   merges.

## PR body

Use these sections, in this order:

- **Summary**: what changed, in two or three sentences.
- **Why**: the problem or ticket (`Closes #n`).
- **Changes**: the behavior changes a reviewer should know, not a file list.
- **Decisions**: link the ADR files or artifact when present; otherwise list the decisions from
  the run, with how to reverse each.
- **Testing**: the real commands run and their counts (for example `pytest: 42 passed`).
- **Risk**: what could break and how likely.
- **How to revert**: the exact command (for example `git revert <sha>`).
- **Notes**: follow-ups, limitations, open questions.

## Safety

Never merge, force-push, run `git add -A`, `git clean`, discard work or amend a commit. Stage
named files only.

## Auto mode

- The caller names the mode in the prompt: `Mode: interactive` (default) or `Mode: auto`.
- Interactive: you may ask the owner with AskUserQuestion, one batch at a time, each question with a
  recommended answer.
- Auto: never ask the owner. On any ambiguity pick the recommended option and record it in
  `decisions[]`: `{title, context, options, decision, why, consequences, how_to_reverse,
  confidence: high|medium|low, needs_review: boolean}`. Do not write ADR files.
- Set `needs_advisor: true` with `advisor_question` when tests keep failing, you have low
  confidence, or a decision affects other tickets or a public contract. The calling script runs the
  advisor. Do not spawn agents (`docs/adr/0001-workflow-capabilities.md`).
