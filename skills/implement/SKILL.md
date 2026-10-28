---
name: implement
description: "Carry out an agreed plan: each step runs in an isolated git worktree through a fresh coding subagent, then its Done-when command is run and the files touched are handed back. Use after the plan (or the S-depth prompt) is agreed."
allowed-tools: Read, Write, Grep, Glob, Agent, Task, Bash
---

# Implement

Turn plan steps into commits. Review is not part of this skill: `/code-review` and the
`intent-review` skill run afterwards.

## Steps

1. Read the plan: `specs/<slug>/PLAN.md` for depth M and L, the prompt for depth S. List the
   steps with their Files, Effort, Done-when and parallel group.
2. Run the groups in order. Inside a group, steps that touch different files may run in parallel.
   Never run two steps that touch the same file at the same time.
3. For each step start a fresh `coding` subagent (Sonnet; High effort steps may use a stronger
   model) in its own isolated git worktree. Use the template in `implementer-prompt.md`.
   A workflow agent's worktree starts from the main checkout HEAD, so tell it the base
   to check out first (`docs/adr/0001-workflow-capabilities.md`).
4. When the subagent returns, run the step's Done-when command yourself in that worktree.
5. If it fails, send the failure output to a fresh subagent for one fix. Repeat at most 3
   rounds. After the third failing round stop and report the step as BLOCKED.
6. Merge each passing worktree branch into the working branch. Re-run the Done-when commands
   of the group on the merged result.

## Hand back

Return, for each step: status (`DONE` or `BLOCKED`), commits (sha and subject), files touched, and
the Done-when output. List any blockers. Do not paste file contents.

## Auto mode

- The caller names the mode in the prompt: `Mode: interactive` (default) or `Mode: auto`.
- Interactive: you may ask the owner with AskUserQuestion, one batch at a time, each question with a
  recommended answer.
- Auto: never ask the owner. On any ambiguity pick the recommended option and record it in
  `decisions[]`: `{title, context, options, decision, why, consequences, how_to_reverse,
  confidence: high|medium|low, needs_review: boolean}`. Do not write ADR files.
- Set `needs_advisor: true` with `advisor_question` when a step is BLOCKED after 3 rounds, you have
  low confidence, or a decision affects other tickets or a public contract. The calling script
  runs the advisor. Do not spawn agents when running inside a workflow agent
  (`docs/adr/0001-workflow-capabilities.md`).
