---
name: intake
description: "Readiness gate for one ticket (issue number, issue URL or free text). Judges READY, CONFIRM, GRILL or BLOCKED and picks a depth of S, M or L before any research, planning or edit. Use before starting work on a ticket."
allowed-tools: Read, Grep, Glob, AskUserQuestion, Bash(gh issue view *), Bash(git log *), Bash(git branch *), Bash(ls *), Bash(test -n *)
---

# Intake — is this ticket ready?

Judge one ticket and return a verdict. Do not edit files, plan or implement.

## Steps

1. Read the ticket. For an issue number or URL run `gh issue view <n> --comments`. For free text,
   use the text. Quote the owner's request verbatim in an intent line.
2. Look up facts yourself (code, docs, issue state, dependencies). Never ask the owner for a fact.
3. Judge the verdict, then the depth.

## Verdict

- **READY**: the goal fits one sentence; each acceptance criterion is checkable by a command or
  visible behavior; scope and out-of-scope are stated; dependencies are done or in the batch; no
  decision is left that belongs to a human; a `Verify:` row exists (a line starting `Verify:`
  anywhere in the ticket body or in a Confirmed decisions comment; no format check).
- **CONFIRM**: 1-3 small decisions remain. Write each as a question with a recommended answer,
  worded so that "yes" accepts it. A missing `Verify:` row is one of them: draft the row as the
  recommended answer. The accepted row goes into the Confirmed decisions comment.
  If the row logs in, check its login variables first: `references/verify-login.md`.
- **GRILL**: the ticket is important or its design tree is deep: auth or security, data migration
  or deletion, a public contract, quota or money, an irreversible action, cross-module
  architecture, or the label `grill`. Hand off: run the grilling skill.
- **BLOCKED**: the ticket is too large (propose a split) or a dependency is missing (name it).

## Depth

- **S**: the plan fits in the prompt. Go straight to `harness:implement`.
- **M**: add a `specs/<slug>/PLAN.md` (local scratch; `harness:writing-plans`), then `harness:implement`.
- **L**: add `harness:brainstorming` (the design is an ADR in `docs/adr/`) and `harness:xia2` research before the plan.

A bug fix goes to `harness:diagnosing-bugs` first: Read `${CLAUDE_PLUGIN_ROOT}/skills/diagnosing-bugs/SKILL.md` (it blocks the Skill tool).

## Output

Return this block to the caller:

```text
Intent: "<the owner's request, verbatim>"
Verdict: READY | CONFIRM | GRILL | BLOCKED
Depth: S | M | L
Deps: <ticket numbers, or none>
Questions: <numbered, each with a recommended answer, or none>
Reason: <one or two sentences>
```

Examples (short):

```text
Ticket has no Verify: row  -> Verdict: CONFIRM
Questions: 1. Add "Verify: bash tests/scripts/x.test.sh exits 0"? Recommended: yes.
Ticket has "Verify: bash scripts/run-tests.sh" -> Verdict: READY
```

## Auto mode

- The caller names the mode in the prompt: `Mode: interactive` (default) or `Mode: auto`.
- Interactive: you may ask the owner with AskUserQuestion, one batch at a time, each question with a
  recommended answer.
- Auto: never ask the owner. On any ambiguity pick the recommended option and record it in
  `decisions[]`: `{title, context, options, decision, why, consequences, how_to_reverse,
  confidence: high|medium|low, needs_review: boolean}`. Do not write ADR files.
- In auto mode, CONFIRM resolves itself: take each recommended answer and record it as a decision.
  A drafted `Verify:` row is a decision with `needs_review: true`; append its text to the
  ticket's confirmed text.
- Set `needs_advisor: true` with `advisor_question` when you are BLOCKED, have low confidence, or a
  decision affects other tickets or a public contract. The calling script runs the advisor. Do
  not spawn agents (`docs/adr/0001-workflow-capabilities.md`).
