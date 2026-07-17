# Design — `techstacks/`: project-owned stack profiles, core stays agnostic

Status: **proposed — awaiting owner confirmation** on the 4 questions in §Decisions (redefine-system change: touches auto-loaded rules + removes the bundled stack model). Companion: `research-brief.md`.

## The model

```
<repo root>
├── techstacks/                 ← NEW. PROJECT-OWNED. Depended on by nothing.
│   ├── README.md               ← shipped: the only harness content here — explains the convention
│   └── <your-stack>.md         ← the project adds its own: architecture, guidelines, conventions
├── rules/                      ← core. STACK-AGNOSTIC. only *mentions* techstacks/
├── skills/                     ← core. stack-neutral examples only
└── templates/                  ← harness doc templates (SUMMARY.template.md …) — NO stack profiles
```

- **`techstacks/` is like `specs/` and `docs/solutions/`**: a root, project-owned folder scaffolded create-if-missing by `init-structure.sh`. The harness ships only `techstacks/README.md` (the convention: "put your stack's architecture / guidelines / conventions here as `techstacks/*.md`; the harness reads this folder but ships nothing stack-specific").
- **Core only points at the folder, never at files inside it.** rules/skills say "your stack profile lives in `techstacks/` — read it before implementing", and stop there. No `techstacks/fastapi.md`, no per-file detail. A project with no stack (like this meta-repo) leaves it with just the README.

## Decisions (proposed; confirm before build)

1. **Name + location:** `techstacks/` at repo root, project-owned. (Distinct from `templates/`, which stays harness-owned doc templates.) → **proposed: yes.**
2. **Ship no stack content:** `techstacks/` ships only `README.md`. Delete `templates/stacks/{fastapi,_skeleton}/` — the harness bundles zero profiles; `_skeleton`'s "how to fill" guidance folds into `techstacks/README.md`. → **proposed: yes** (this is the decoupling).
3. **`rules/architecture.md` + `rules/guidelines.md`:** collapse each to a **thin auto-loaded pointer** (~5 lines) that says "this project's stack architecture / engineering guidelines live in `techstacks/` — read that folder; the harness ships none". Keep the two files (they are auto-load slots + referenced by agents/PROJECT) but strip all placeholder/FastAPI content. → **proposed: thin pointers** (also lands the over-engineering-review recommendation).
4. **FastAPI examples in `rules/plan-format.md` / `wave-parallelism.md` / `auto-correct-scope.md`:** replace with **stack-neutral** illustrations (generic `src/<module>`, `tests/test_<module>`, "your test runner", "your migration command") — keep the examples (they teach the format/rule) but remove the FastAPI specificity. → **proposed: neutralize, don't delete.**

## Component changes (on approval)

1. **Create `techstacks/README.md`** — the convention doc (what goes here, suggested files `architecture.md`/`guidelines.md`/`conventions.md`, that it's project-owned and harness-independent). Absorbs the useful "prompts to answer" from the old `_skeleton`.
2. **`rules/architecture.md`** → thin pointer to `techstacks/`. **`rules/guidelines.md`** → thin pointer to `techstacks/`.
3. **`rules/plan-format.md`, `wave-parallelism.md`, `auto-correct-scope.md`** → neutralize FastAPI examples to stack-agnostic ones.
4. **Delete `templates/stacks/`** (fastapi + _skeleton).
5. **`agents/PROJECT.template.md`** → stack pointer targets `techstacks/`, not `templates/stacks/`. **`agents/PROJECT.md`** (this repo) → same pointer update.
6. **Skills** — neutralize gratuitous FastAPI examples in `executing-plans`, `correctness-review/*-prompt.md` where they're illustrative; leave stack-neutral logic alone.
7. **`init-structure.sh`** → scaffold `techstacks/README.md` (create-if-missing) alongside specs/, docs/solutions/, agent-memory/. **`templates/structure/`** gains the `techstacks-README.md` source.
8. **References**: CLAUDE.md (Stack line), README.md, skills/README.md — mention `techstacks/` where they described `templates/stacks/`.
9. **Tests**: init-structure test asserts `techstacks/README.md` scaffolds; a grep-guard that core `rules/` carry no FastAPI/stack-specific tokens (regression fence for "stays agnostic").

## Why this shape

- **True decoupling:** a new installer gets core rules that name *no* stack, plus an empty `techstacks/` they fill (or ignore). Nothing in the harness reads a specific stack file, so there is no coupling to break.
- **One canonical home per fact:** the stack lives in exactly one place (`techstacks/`), pointed at from the few auto-loaded rules — the same "one home + pointers" principle issue #67 Phase 3 targets.
- **Lands two prior findings:** the review's "shrink architecture.md/guidelines.md to pointers", and the wave-3 instinct that bundled stack profiles are speculative (we already cut 3 of 5; this cuts the last 2 and the whole `templates/stacks/` concept).

## Risks

- Redefine-system (architecture direction + auto-loaded rules) → owner-gated. Reversible via `git revert` (prose + one folder move; no data/schema migration).
- Auto-loaded `rules/architecture.md`+`guidelines.md` shrink changes what every session sees — but they were placeholders; net context *drops*.
- `.claude/` deployed copies drift until next authorized re-sync (local-only).
- A consuming project that previously copied a `templates/stacks/` profile into `rules/architecture.md` keeps working (their filled file is protected/hand-maintained); only the *bundled source* goes away — documented in the README.

## Out of scope

Migrating any real project's stack content (there is none in this meta-repo). Renaming `templates/` itself. Auto-detecting stack (xia2 already does that generically, config-free).
