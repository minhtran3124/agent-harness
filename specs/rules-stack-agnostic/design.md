# Design — stack-agnostic `rules/`

> Linear: **MIN-25** (project harness-skills). Intake: `specs/rules-stack-agnostic/SUMMARY.md` — Lane high-risk, confidence medium.

## 1. Problem

The `rules/` governance layer is hard-coupled to a Python / FastAPI / SQLAlchemy backend, so it cannot be reused as-is in a frontend repo, a Node/TypeScript backend, or any non-Python stack. Coupling heat map (mentions of `fastapi|sqlalchemy|pydantic|async def|alembic|pytest|asyncpg|repository|uvicorn`, verified on `v2`):

| File | Hits | Verdict |
|---|---|---|
| `rules/architecture.md` | 20 | stack-specific (whole file is FastAPI layering) |
| `rules/guidelines.md` | 10 | stack-specific (Python/async/SQLAlchemy) |
| `rules/plan-format.md` | 9 | universal rule + FastAPI examples |
| `rules/auto-correct-scope.md` | 6 | universal rules + SQLAlchemy/Pydantic examples |
| `rules/wave-parallelism.md` | 3 | universal + one FastAPI example |
| `rules/behavior.md` | 0 | already agnostic |
| `rules/orchestration.md` | 0 | already agnostic |

Key context (`docs/solutions/harness-bootstrap/meta-repo-signal-remapping-decisions.md`): `architecture.md` + `guidelines.md` **deliberately describe the *consuming* (target) project**, not this harness repo. The coupling is not an accident — it is a **single hardcoded stack profile** where a swappable one belongs. `xia2/PROJECT.md` is the established portability seam, with precedent for mapping stack categories to analogs.

## 2. Goal

A `rules/` layer that drops into any repo where the **universal governance is identical everywhere** and the **stack-specific guidance is generated per repo** — built on the existing `bootstrap-xia2` scan→draft→human-review mechanism (Option A), not a hand-maintained library of profiles for stacks that have no consumers yet.

## 3. Non-goals

- Authoring profiles for every language now. Ship the mechanism + the **FastAPI profile (current content, relocated)** as the first profile; others are generated or skeletoned on demand.
- Merging the stack profile into `xia2/PROJECT.md`. They answer different questions and stay separate.
- Touching `behavior.md` / `orchestration.md` content (already agnostic) beyond example tweaks if needed.

## 4. Architecture — the split

- **Universal layer** (ships identical to every repo): `behavior.md`, `orchestration.md` unchanged; `plan-format.md`, `auto-correct-scope.md`, `wave-parallelism.md` keep their rules/schemas/invariants language-neutral, with FastAPI snippets **tagged illustrative** (`example — substitute your stack`), not deleted.
- **Stack profile** (per-repo): `rules/architecture.md` + `rules/guidelines.md`. The files **stay at their current paths** (so `deploy-harness.sh`, which syncs the whole `rules/` dir into `.claude/`, and any consumer keep working). Their **content** changes per §4.1.
- **`xia2/PROJECT.md`** stays separate — risk signals ("what is risky here"), distinct from the profile ("how this stack is built").

### 4.1 What lives where (resolves the deploy interaction — the load-bearing decision)

`scripts/deploy-harness.sh` syncs the **entire** `rules/` dir into `.claude/`, so `rules/architecture.md` + `rules/guidelines.md` must always be present and valid. The FastAPI content is therefore **moved, then replaced** — not copied:

- **Authoritative FastAPI content → `templates/stacks/fastapi/{architecture.md,guidelines.md}`** (the bundled profile, byte-for-byte the pre-refactor content).
- **`rules/architecture.md` + `rules/guidelines.md` in this repo → a short, generic, stack-neutral skeleton** that (a) explains it is the active stack profile, (b) points at `templates/stacks/<stack>/` + `bootstrap-xia2` as the way to populate it, and (c) for this meta-repo, points harness-working agents at `skills/README.md` + `rules/behavior.md` — exactly as the `meta-repo-signal-remapping` decision already established.

This means **Phase 1 ships a working `rules/`** (valid generic skeletons, no FastAPI content duplicated). In a consuming repo, `bootstrap-xia2` (Phase 2) overwrites these two files from the matching `templates/stacks/<stack>/` profile (or a skeleton). The FastAPI guidance is never lost — it lives, intact, in `templates/stacks/fastapi/`.

## 5. Components

1. **Bundled profile templates** — `templates/stacks/<stack>/{architecture.md,guidelines.md}`. Seed `templates/stacks/fastapi/` by moving the current `rules/architecture.md` + `rules/guidelines.md` content **verbatim** (zero new authoring; nothing lost). `templates/` is already in both the `install-harness.sh` PAYLOAD and the `deploy-harness.sh` sync set, so nesting `stacks/` under it ships automatically — **no installer change needed**.
2. **`rules/` skeleton replacement** — replace this repo's `rules/architecture.md` + `rules/guidelines.md` with the generic skeleton from §4.1 (keeps `deploy-harness.sh` valid; Phase-1-shippable).
3. **`bootstrap-xia2` generator** (Phase 2) — detect the consuming repo's stack; if a bundled template matches, use it as the human-reviewed draft; otherwise emit a **skeleton + human-review checklist** (the same flow it already uses for `PROJECT.md`). Never silently emit a wrong-stack profile.
4. **Doc/reference updates** — review the spots that encode the FastAPI assumption or name these files: `skills/xia2/PROJECT.md` (lines describing `architecture.md`/`guidelines.md` as "for target FastAPI projects"), `benchmarks/review-chain/fixtures/soft-delete-filter/truth.md` (cites `.claude/rules/architecture.md → Soft Deletes` + `rules/guidelines.md`), `CLAUDE.md`, `skills/README.md`. **This review is for prose/conceptual drift, not path fixes** — verified no core doc references these two files by path today (so it is not a no-op of "fix broken links"; it is "does this prose still hold after the split"). No edit to `scripts/lint-doc-truth.sh` itself is required; the lint only checks literal paths and skips `<>`-placeholders, so new prose must use placeholder (`templates/stacks/<stack>/`) or real paths.

## 6. Data flow

```
install / bootstrap-xia2
  → detect consuming repo stack
  → write rules/architecture.md + rules/guidelines.md   (from templates/stacks/<stack>/, or skeleton)
  → write/refresh xia2/PROJECT.md                        (existing behavior)
  → human-review checklist
```

## 7. Error handling / fallback

Unknown or ambiguous stack → emit the skeleton profile + a review checklist, flagged for human completion (fallback "C"). Never guess a stack and ship the wrong profile.

## 8. Meta-repo self-profile (decided)

Resolved in §4.1, not deferred: this repo's `rules/architecture.md` + `rules/guidelines.md` become the **generic skeleton** that points harness-working agents at `skills/README.md` + `rules/behavior.md` (consistent with the `meta-repo-signal-remapping` decision) and points at `templates/stacks/<stack>/` + `bootstrap-xia2` for populating a real stack profile. The FastAPI content moves to `templates/stacks/fastapi/`. This repo does **not** keep FastAPI content in `rules/`.

## 9. Phasing

- **Phase 1 — universal/stack split (cheap, immediate portability).** Relocate FastAPI content to `templates/stacks/fastapi/`; tag the illustrative examples in `plan-format`/`auto-correct-scope`/`wave-parallelism`; update consumers (lint, CLAUDE.md, README, installer). The shared rules become portable even before the generator exists.
- **Phase 2 — generator.** Extend `bootstrap-xia2` to detect the stack and emit the profile (template match or skeleton fallback).

## 10. Success criteria / testing

- **Coupling, stated precisely** (a naive grep is wrong — §4 deliberately *keeps* tagged examples):
  - `rules/architecture.md` + `rules/guidelines.md` (now skeletons) → **0** stack-specific tokens.
  - `behavior.md` + `orchestration.md` → 0 (already true).
  - `plan-format.md` / `auto-correct-scope.md` / `wave-parallelism.md` → every remaining FastAPI token sits **inside a block tagged `example — substitute your stack`**; no untagged stack assumption in the rule prose. (Criterion is "no untagged coupling," not "zero tokens.")
- **Nothing lost (git-baseline diff):** `git show <pre-refactor-sha>:rules/architecture.md | diff - templates/stacks/fastapi/architecture.md` is empty (and likewise for `guidelines.md`). The baseline is git history, since the content is moved out of the working tree. **Pin `<pre-refactor-sha>` to the actual `v2` commit before the relocation lands** when writing the PLAN, so the check is reproducible in CI.
- `rules/architecture.md` + `rules/guidelines.md` still exist as valid generic skeletons after Phase 1, so `deploy-harness.sh` syncs a working `.claude/rules/` (no consumer gets an empty/broken rules dir).
- A documented, repeatable way to add a new stack profile without editing the shared rules.
- `bootstrap-xia2` produces a profile (template or skeleton) for a fresh repo (Phase 2).
- `scripts/run-tests.sh` green (it runs `lint-doc-truth.sh`) — locally and on the `harness-ci` matrix (ubuntu + macos).
