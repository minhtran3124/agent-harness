---
name: brainstorming
description: "Decide what to build when the goal is clear but the approach is not. Use when the user is weighing two or more ways to do something, says they are unsure how to approach it, or asks for a design or a recommendation — and NOT when the approach is already settled and what is missing is knowledge of the codebase or a library, which is xia2. Produces an approved specs/<slug>/design.md."
allowed-tools: Read, Write, Grep, Glob, Agent, Task
---

# Brainstorming Ideas Into Designs

Turn an unclear or high-risk idea into an approved design. `feature-intake` decides whether this
skill runs. If no intake lane exists, run `feature-intake` first.

<HARD-GATE>
Do not write code, scaffold, or invoke an implementation skill until the user approves the
presented design. If scope becomes smaller, ask for re-routing. Do not silently skip this gate.
</HARD-GATE>

## Flow

1. Inspect the current project, relevant docs, recent changes, and applicable decisions under
   `docs/solutions/`. If the request spans subsystems that share no files, data model, or
   user-facing flow, decompose it into separate specs before refining details.
2. Map the open decisions as a design tree. The tree holds purpose, constraints, success
   criteria, and boundaries. Approach choice belongs to step 3. Section detail belongs to step 4.
   The frontier is each decision whose prerequisites the user already settled. Ask the whole
   frontier in one numbered round. Give a recommended answer for each question, worded so that
   "yes" accepts it. Then wait. Facts are your job. Find each fact yourself, or dispatch a
   subagent when the search is larger than a few reads. Never ask the user for a fact.
   Decisions are the user's. Put each decision to the user and wait. If a decision goes
   unanswered or evasive twice, name the gap, record the recommended answer as an assumption,
   and move on. Repeat with the new frontier. Step 2 ends when the frontier is empty and the
   user confirms a shared understanding. A plain "yes" to the whole last round is that
   confirmation. Otherwise ask for it. Act only after that. Use a visual artifact only when
   seeing the answer is materially clearer than reading it.
3. Present 2–3 viable approaches, their trade-offs, and a recommendation. Remove unrequested
   scope (YAGNI) before asking for approval.
4. Present the design in proportionate sections: architecture, components/data flow, error
   behavior, and tests. Confirm each section with the user. Revise when needed.
5. Before writing the spec, restate the agreed purpose, constraints, and chosen approach in 2–3
   sentences. Check this restatement against the actual answers from steps 2–4, not against your
   memory of them. Confirm the restatement with the user, so drift surfaces before it is
   committed. Read `references/design-template.md` and write `design.md` to that template. Write
   the approved result to `specs/<slug>/design.md`.
   In a multi-phase spec, record non-blocking unknowns in specs/<slug>/QUESTIONS.md from templates/QUESTIONS.template.md.
   Then read `references/spec-review-loop.md` and complete its
   review/user-review gates.
6. Invoke only `xia2`, passing the spec directory, then `writing-plans`. This is the terminal
   handoff sequence. Do not substitute another implementation or design skill.

## Design constraints

- Prefer units with one purpose, explicit interfaces, and independently testable behavior.
- Follow existing patterns. Include only targeted cleanup that serves this change. Do not add
  unrelated refactors.
- A design may be short for a genuinely small scope. Once this skill is selected, the design
  still requires approval.
