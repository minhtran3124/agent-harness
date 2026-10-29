---
name: brainstorming
description: "Decide what to build when the goal is clear but the approach is not. Use when the user is weighing two or more ways to do something, says they are unsure how to approach it, or asks for a design or a recommendation — and NOT when the approach is already settled and what is missing is knowledge of the codebase or a library, which is xia2. Depth L writes specs/<slug>/design.md and records the design as an ADR in docs/adr/."
allowed-tools: Read, Write, Grep, Glob, AskUserQuestion
---

# Brainstorming — from idea to design

Explore the options and converge on one design. Intake decides whether this skill runs: depth L.

## Steps

1. Read the project, the relevant docs, recent changes and `docs/solutions/`. If the request spans
   parts that share no files or data, split it into separate designs.
2. Settle purpose, constraints and success criteria. Look facts up yourself. Ask the owner only
   for decisions.
3. Present 2-3 viable approaches with trade-offs and a recommendation.
4. Depth L: write the design to `specs/<slug>/design.md` (local scratch, gitignored) from
   `references/design-template.md`, and add one entry to `specs/<slug>/decision.md`. Also record
   it as an ADR with `stage: design`: fill `decisions[]` from the same template; the ADR stage of
   `decision-record` writes it to `docs/adr/`. Depth S and M skip this skill: `writing-plans`
   writes their short `design.md`.
5. Next steps: `harness:xia2` for research if unknown code or libraries are involved, then `harness:writing-plans`.

No code until the design is agreed. There is no mandatory review round. For an L design the
advisor checks the result (the calling script runs it).

## Auto mode

- The caller names the mode in the prompt: `Mode: interactive` (default) or `Mode: auto`.
- Interactive: you may ask the owner with AskUserQuestion, one batch at a time, each question with a
  recommended answer worded so "yes" accepts it.
- Auto: never ask the owner. At every approach choice or ambiguity pick the recommended option and
  record it in `decisions[]`: `{title, context, options, decision, why, consequences,
  how_to_reverse, confidence: high|medium|low, needs_review: boolean}`. Do not write ADR files or
  `specs/` files: return the design text, and the calling script writes `design.md`.
- Set `needs_advisor: true` with `advisor_question` when you are BLOCKED, have low confidence, or a
  decision affects other tickets or a public contract. The calling script runs the advisor. Do
  not spawn agents (`docs/adr/0001-workflow-capabilities.md`).
