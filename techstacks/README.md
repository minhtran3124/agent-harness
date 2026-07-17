# techstacks/ — your project's tech-stack profile (project-owned)

This folder is **yours**. The harness core (rules, skills, templates) is deliberately
**stack-agnostic** — it ships no framework, no language, no architecture assumptions. Everything
specific to *your* stack lives here, and nothing in the harness depends on what you put in it.

## What to put here

Add one or more markdown files describing your stack. Suggested:

- `techstacks/architecture.md` — layers/responsibilities, request/data flow, where auth &
  validation live, key cross-cutting patterns, infrastructure (persistence, cache, hosting).
- `techstacks/guidelines.md` — code style, error handling, data access, async/perf, testing,
  logging conventions.
- `techstacks/conventions.md` — anything else agents should honor (naming, folder layout, PR rules).

Split however suits you — the harness reads the whole folder, not specific filenames.

## Prompts to answer (starter checklist)

**Layers / Responsibilities** — what are the named layers, and what is each allowed to do?
**Request / Data flow** — how does a request travel to a response? Where do auth, validation,
and error handling live?
**Key patterns** — what cross-cutting patterns does the codebase enforce (DI, factory,
soft-delete, …)?
**Infrastructure** — persistence, cache, messaging, hosting.
**Testing** — runner, structure, coverage target.

## How the harness uses it

- The auto-loaded `rules/architecture.md` and `rules/guidelines.md` are thin pointers to this
  folder — agents read `techstacks/*.md` before implementing, debugging, or reviewing.
- `xia2` classifies risk from built-in common signals (it does **not** need this folder).
- A project with no stack (e.g. a docs-only or tooling repo) can leave this folder with just this
  README — nothing breaks.

> The harness bundles **no** example stack. Write your own here; it stays independent of harness
> upgrades (a re-sync never overwrites this folder's contents).
