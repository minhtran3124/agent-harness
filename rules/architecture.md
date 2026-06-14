# Architecture Profile — Active Stack

This file is the **active stack architecture profile** for this project.
Agents should read it before implementing, debugging, or reviewing.

---

## For This Meta-Repo (harness-skills)

This is the Claude Code harness repo — it ships skills, hooks, rules, and templates,
not an application backend or frontend. Harness-working agents should use:

- `skills/README.md` — skill inventory, workflow, and handoff map (architecture/SoT)
- `rules/behavior.md` — behavioral guidelines (SoT for all agents)

Stack-specific application architecture does not apply here.

---

## Stack Profiles

Stack-specific content lives in `templates/stacks/<stack>/architecture.md`.
The `/bootstrap-xia2` skill generates or refreshes that file from a repo scan
and copies the relevant profile here when setting up a new project.

Available bundled profiles (see `templates/stacks/` for the full list):

- `templates/stacks/<stack>/architecture.md` — one file per stack; browse `templates/stacks/` for the bundled profile(s)

---

## Generic Architecture Outline (fill in for your project)

When adopting this harness for an application project, replace this file's content
with your stack profile, or run `/bootstrap-xia2` to generate one. Prompts to answer:

**Layers / Responsibilities**
- What are the named layers (e.g. entry point, business logic, data access)?
- What is each layer allowed to do, and what is explicitly off-limits?

**Request / Data Flow**
- How does a request enter the system and travel through the layers to a response?
- Where does auth, validation, and error handling live?

**Key Patterns**
- What cross-cutting patterns does the codebase enforce (e.g. DI, factory, soft-delete)?

**Infrastructure**
- What persistence, cache, messaging, and hosting components are in use?
