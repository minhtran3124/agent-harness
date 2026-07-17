# Research — decouple tech-stack from core (a project-owned `techstacks/`)

Requested 2026-07-17: rules/skills/templates are coupled to a tech stack (FastAPI). A new installer inherits that baggage. Target: a new top-level `techstacks/` folder each project fills with *its own* stack rules — independent, depended-on by nothing. Core rules/skills only **mention** the folder, never detail specific stack files.

All coupling points below verified on the current tree (v2.5.2).

## Where the coupling lives today (two distinct kinds)

**Kind A — illustrative FastAPI *examples* baked into generic rules** (they exist to show the *format*, but use a specific stack):
- `rules/plan-format.md` — 7 FastAPI mentions: worked task examples (TradeLog model, `alembic upgrade head`, pydantic, `app/services/…`).
- `rules/wave-parallelism.md` — 2: a FastAPI wave table example.
- `rules/auto-correct-scope.md` — 2: FastAPI error-factory / migration examples.
- Skills: `executing-plans`, `correctness-review/*-prompt.md`, `xia2` examples reference FastAPI-ish paths.
Each already carries a `> example — substitute your stack` marker, so the intent was always "illustrative, not prescriptive" — but the illustration itself is stack-specific.

**Kind B — the *actual per-project stack profile*** (real architecture/guidelines content):
- `rules/architecture.md` + `rules/guidelines.md` — declared "the **active stack profile** for this project", **auto-loaded every session** (deployed to `.claude/rules/`). For this meta-repo they are unfilled placeholders ("does not apply here" / "fill per stack"). The 2026-07-16 over-engineering review already flagged both as "unfilled placeholder auto-loaded every session → shrink to ~5-line pointers".
- `templates/stacks/{fastapi,_skeleton}/{architecture,guidelines}.md` — bundled stack profiles the project copies into `rules/architecture.md`/`guidelines.md`.

## Who references the stack surfaces

- `rules/architecture.md`, `rules/guidelines.md` → reference `templates/stacks/<stack>/` (copy-from source).
- `agents/PROJECT.template.md` → "active stack profile … from `templates/stacks/`".
- No script/hook/manifest hard-depends on `templates/stacks/` (bootstrap-xia2, which used to render from it, is gone). check_manifest does **not** inventory templates/stacks. `_skeleton/architecture.md` still mentions the removed `/bootstrap-xia2` (a stale ref to clean up regardless).

## What "decoupled" means concretely

1. Core (`rules/`, `skills/`, `templates/`) ships **zero** stack-specific content — no FastAPI, no bundled profile. It only *mentions* `techstacks/` generically.
2. `techstacks/` is a **project-owned root folder** (like `specs/`, `docs/solutions/`) — the project drops its own stack rules there; nothing in the harness depends on its contents.
3. The auto-loaded rules become thin pointers to `techstacks/` (which also lands the review's "shrink to pointers" recommendation).

## Constraints / things not to break

- `rules/behavior.md` (the SoT behavioral rule) is stack-agnostic already — untouched.
- The plan-format **schema** (task fields, guardrails) is stack-agnostic — only its *examples* are FastAPI; keep the schema, neutralize the examples.
- `agents/PROJECT.md` (this repo's, filled) points at convention docs — update its stack pointer.
- init-structure.sh scaffolds project-owned dirs — `techstacks/` (with a README) is a natural addition there.
- Deleting `templates/stacks/` must update its 3 referrers (architecture.md, guidelines.md, PROJECT.template.md) — no machine consumer, so safe.

## Open design questions for the owner (see design.md)

1. Folder name + location: `techstacks/` at repo root (project-owned) — confirm vs a different name.
2. Ship `techstacks/` empty with only a `README.md` convention doc (no example stack) — confirm the harness ships **no** stack content.
3. `rules/architecture.md` + `guidelines.md`: keep as thin auto-loaded pointers, or delete and point from one place?
4. FastAPI examples in the 3 rules: replace with **stack-neutral** examples, or remove and point at `techstacks/`?
