---
name: brainstorming
description: "Use when feature-intake routes here (high-risk lane, a real design fork, or ambiguous direction) - explores user intent, requirements and design before implementation. Lane routing decides WHETHER to brainstorm; this skill governs HOW."
---

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

**When this skill applies:** `/feature-intake` is the routing authority — it sends work here on the high-risk lane, on a real design fork (≥2 viable approaches), or when direction is ambiguous. Tiny- and normal-lane work with clear intent skips brainstorming by design (see `skills/README.md` and `rules/orchestration.md` → Artifact policy); do not pull it back in because the change "feels creative". If you land here without an intake lane, run `/feature-intake` first.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<HARD-GATE>
Once routed here: do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. Simplicity discovered mid-brainstorm does not lift the gate — if the work turns out smaller than intake judged, say so and let the user re-route; never silently skip to implementation.
</HARD-GATE>

The design can be short — a few sentences for genuinely small scopes — but once this skill is active it MUST be presented and approved before implementation.

## Checklist

You MUST create a task for each of these items and complete them in order:

1. **Explore project context** — check files, docs, recent commits
2. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
3. **Propose 2-3 approaches** — with trade-offs and your recommendation
4. **Present design** — in sections scaled to their complexity, get user approval after each section
5. **Write design doc** — save to `specs/<slug>/design.md`
6. **Spec review loop** — dispatch spec-document-reviewer subagent with precisely crafted review context (never your session history); fix issues and re-dispatch until approved (max 5 iterations, then surface to human)
7. **User reviews written spec** — ask user to review the spec file before proceeding
8. **Research existing code** — invoke xia2 skill to discover what already exists before designing the implementation
9. **Transition to implementation** — invoke writing-plans skill to create implementation plan

**Showing rather than telling.** When a question is genuinely visual — mockups, wireframes, layout comparisons, side-by-side designs, architecture diagrams — publish an Artifact instead of describing it in text. The test, per question: **would the user understand this better by seeing it than reading it?** A question *about* a UI topic is not automatically a visual question — "what does personality mean here?" is conceptual (answer in the terminal); "which wizard layout works better?" is visual (show it). Requirements questions, tradeoff lists, and scope decisions stay in the terminal.

**The terminal state is invoking writing-plans.** The transition sequence is: invoke xia2 first (to research what already exists), then invoke writing-plans. Do NOT invoke frontend-design, mcp-builder, or any other skill. The ONLY skills you invoke after brainstorming are xia2 → writing-plans, in that order.

## The Process

**Understanding the idea:**

- Check out the current project state first (files, docs, recent commits)
- Search `docs/solutions/` for past architectural decisions in this domain:
  ```bash
  grep -r "problem_type: decision" docs/solutions/ -l
  ```
  Read relevant decision files before proposing approaches — avoid re-proposing already-rejected alternatives.
- Before asking detailed questions, assess scope: if the request describes multiple independent subsystems (e.g., "build a platform with chat, file storage, billing, and analytics"), flag this immediately. Don't spend questions refining details of a project that needs to be decomposed first.
- If the project is too large for a single spec, help the user decompose into sub-projects: what are the independent pieces, how do they relate, what order should they be built? Then brainstorm the first sub-project through the normal design flow. Each sub-project gets its own spec → plan → implementation cycle.
- For appropriately-scoped projects, ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Only one question per message - if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**

- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Presenting the design:**

- Once you believe you understand what you're building, present the design
- Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced
- Ask after each section whether it looks right so far
- Cover: architecture, components, data flow, error handling, testing
- Apply YAGNI ruthlessly — cut every feature the user did not ask for before presenting
- Be ready to go back and clarify if something doesn't make sense

**Design for isolation and clarity:**

- Break the system into smaller units that each have one clear purpose, communicate through well-defined interfaces, and can be understood and tested independently
- For each unit, you should be able to answer: what does it do, how do you use it, and what does it depend on?
- Can someone understand what a unit does without reading its internals? Can you change the internals without breaking consumers? If not, the boundaries need work.
- Smaller, well-bounded units are also easier for you to work with - you reason better about code you can hold in context at once, and your edits are more reliable when files are focused. When a file grows large, that's often a signal that it's doing too much.

**Working in existing codebases:**

- Explore the current structure before proposing changes. Follow existing patterns.
- Where existing code has problems that affect the work (e.g., a file that's grown too large, unclear boundaries, tangled responsibilities), include targeted improvements as part of the design - the way a good developer improves code they're working in.
- Don't propose unrelated refactoring. Stay focused on what serves the current goal.

## After the Design

**Documentation:**

- Write the validated design (spec) to `specs/<slug>/design.md`
  - Slug convention: specs/README.md
  - (User preferences for spec location override this default)
- Use elements-of-style:writing-clearly-and-concisely skill if available
**Spec Review Loop:**
After writing the spec document:

1. Dispatch spec-document-reviewer subagent (see spec-document-reviewer-prompt.md)
2. If Issues Found: fix, re-dispatch, repeat until Approved
3. If loop exceeds 5 iterations, surface to human for guidance

**User Review Gate:**
After the spec review loop passes, ask the user to review the written spec before proceeding:

> "Spec written to `<path>`. Please review it and let me know if you want to make any changes before we start writing out the implementation plan."

Wait for the user's response. If they request changes, make them and re-run the spec review loop. Only proceed once the user approves.

**Implementation:**

- Invoke the xia2 skill and pass the spec directory path (e.g., `specs/<slug>/`) so xia2 saves its research brief alongside `design.md`. Example invocation context: *"Research the feature described in `specs/<slug>/design.md`. Save the research brief to `specs/<slug>/research-brief.md`."*
- After xia2 delivers its research brief, invoke the writing-plans skill to create a detailed implementation plan
- Do NOT invoke any other skill. xia2 → writing-plans is the only transition sequence.