---
name: writing-plans
description: "Turn an agreed goal (and design or research, when they exist) into a short, executable plan of steps in specs/<slug>/plan.md. Use after intake, at every depth, before any code change."
allowed-tools: Read, Write, Grep, Glob, AskUserQuestion
---

# Writing Plans

Write `specs/<slug>/plan.md` at every depth from `${CLAUDE_PLUGIN_ROOT}/templates/specs/plan.md`.
At depth S it is one or two steps. `specs/` is local scratch and gitignored. Read
`specs/<slug>/intent.md`, and read
`specs/<slug>/design.md`, the design ADR in `docs/adr/` (`stage: design`) and `research-brief.md`
when they exist.

At depth S and M no design stage runs, so also write a short `specs/<slug>/design.md` from
`${CLAUDE_PLUGIN_ROOT}/templates/specs/design.md`: one or two sentences each under Context,
Options, Decision and Why; `none` under the other headings. Add each choice you make to
`specs/<slug>/decision.md`.

## Step shape

Each step is small enough for one fresh subagent and carries:

- **Files**: the paths it creates or changes.
- **Covers**: the acceptance criteria IDs from `intent.md` (`AC1`, `AC2`) that the step proves.
- **Effort**: `low`, `medium` or `high`, with one line on why.
- **Done-when**: a command and its expected result (exit code or output). A judgment such as
  "looks right" does not count.
- **Parallel group**: a letter. Steps that touch different files share a group and may run at the
  same time. Steps that touch the same file go in separate groups, in order.

## Steps to write the plan

1. Map the files to create or change and follow the existing patterns.
2. Put the checks first: for each behavior the goal needs, write the command that proves it.
3. Split the work into steps, test first where it applies. Give each its Files, Effort,
   Done-when and group.
4. Check that no two steps in one group share a file, and that every dependency comes in an earlier
   group.

Format:

```text
## Goal
<one sentence>

## Steps
### 1. <title>   (group A)
- Files: <paths>
- Covers: AC1
- Effort: medium — <why>
- Done-when: `<command>` exits 0 and prints <expected>
```

Next: `harness:implement`.

## Auto mode

- The caller names the mode in the prompt: `Mode: interactive` (default) or `Mode: auto`.
- Interactive: you may ask the owner with AskUserQuestion, one batch at a time, each question with a
  recommended answer.
- Auto: never ask the owner. On any ambiguity pick the recommended option and record it in
  `decisions[]`: `{title, context, options, decision, why, consequences, how_to_reverse,
  confidence: high|medium|low, needs_review: boolean}`. Do not write ADR files or `specs/` files:
  return the plan text, and the calling script writes `plan.md`.
- Set `needs_advisor: true` with `advisor_question` when you are BLOCKED, have low confidence, or a
  decision affects other tickets or a public contract. The calling script runs the advisor. Do
  not spawn agents (`docs/adr/0001-workflow-capabilities.md`).
