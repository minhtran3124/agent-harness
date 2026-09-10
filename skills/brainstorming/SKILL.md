---
name: brainstorming
description: "Decide what to build when the goal is clear but the approach is not. Use when the user is weighing two or more ways to do something, says they are unsure how to approach it, or asks for a design or a recommendation — and NOT when the approach is already settled and what is missing is knowledge of the codebase or a library, which is xia2. Produces an approved specs/<slug>/design.md."
allowed-tools: Read, Write, Grep, Glob, Agent, Task
---

# Brainstorming Ideas Into Designs

Turn an unclear or high-risk idea into an approved design. `feature-intake` decides whether this
skill runs; if no intake lane exists, run it first.

<HARD-GATE>
Do not write code, scaffold, or invoke an implementation skill until the user has approved the
presented design. If scope becomes smaller, ask for re-routing; do not silently skip this gate.
</HARD-GATE>

## Flow

1. Inspect the current project, relevant docs, recent changes, and applicable decisions under
   `docs/solutions/`. If the request spans subsystems that share no files, data model, or
   user-facing flow, decompose it into separate specs before refining details.
2. Ask one clarifying question per message until purpose, constraints, success criteria, and
   boundaries are clear enough to act on — steps 3–4 still catch any gap through approach
   trade-offs and per-section confirmation, so don't over-probe. If a question goes unanswered or
   evasive twice, name the gap and move on. Use a visual artifact only when seeing the answer is
   materially clearer than reading it.
3. Present 2–3 viable approaches, their trade-offs, and a recommendation. Remove unrequested
   scope (YAGNI) before asking for approval.
4. Present the design in proportionate sections: architecture, components/data flow, error
   behavior, and tests. Confirm each section with the user; revise when needed.
5. Before writing the spec, restate the agreed purpose, constraints, and chosen approach in 2–3
   sentences, checked against the actual answers from steps 2–4 rather than recalled from memory,
   and confirm it with the user so drift surfaces before it's committed. Write the approved result
   to `specs/<slug>/design.md`. Then read `references/spec-review-loop.md` and complete its
   review/user-review gates.
6. Invoke only `xia2`, passing the spec directory, then `writing-plans`. This is the terminal
   handoff sequence; do not substitute another implementation or design skill.

## Design constraints

- Prefer units with one purpose, explicit interfaces, and independently testable behavior.
- Follow existing patterns. Include only targeted cleanup that serves this change; do not add
  unrelated refactors.
- A design may be short for a genuinely small scope, but approval is still required once this
  skill has been selected.
