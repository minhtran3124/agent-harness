# Design — Remove bootstrap-xia2 by making xia2 common (no per-project config)

Status: proposed — **awaiting owner approval before execution** (this redefines the risk-classification source-of-truth, an escalation-class change per `rules/orchestration.md`). Companion: `research-brief.md`.

## Requirement (owner, 2026-07-17)

- Audience is **1–3 people** → cold-onboarding automation has little value.
- **Adapt across many projects by removing the project-specific layer entirely — make everything common/generic**, not by generating per-project config.
- **Keep the ability to init the structural files** (docs/solutions/critical-patterns.md, docs/solutions/INDEX.md, specs/STATE.md, specs/README.md, docs/solutions/README.md, agent-memory/README.md) so the rest of the workflow keeps working.
- **End goal: bootstrap-xia2 is gone and everything still works.**

This selects research **Option D (drop the PROJECT.md dependency) + preserve scaffolding** — the deepest cut, and the one that matches "biến thành common".

## Core idea

Today: `xia2` reads a per-project `PROJECT.md` (curated lists of high-blast files, manifests, contracts, auth surfaces, entry points, knowledge base, decisions folder) and **halts** if it's missing — which is why `bootstrap-xia2` exists (to generate that file).

After: `xia2` classifies from **common signals baked into the skill** — the same generic patterns `bootstrap-xia2`'s detection heuristics already enumerated, applied *live per change* instead of frozen into a curated file. No PROJECT.md, no gate-halt, no bootstrap. The two harness-convention signals it needs are **already common** and get hardcoded:
- **Knowledge base** → `docs/solutions/INDEX.md` (the harness convention — no per-project mapping needed).
- **Recent decisions** → `specs/` (the harness convention).

Precision trade-off: a project's *unusual* high-blast file that matches no common pattern won't be auto-flagged. For a 1–3 person team adapting across many repos, generic-good-enough beats per-project curation overhead — and the risk hooks (`risk-corroboration.sh`) + reviews remain the backstop.

## Component design

### 1. xia2/SKILL.md — replace PROJECT-CONFIG-GATE with a Common Signals section

Delete the `<PROJECT-CONFIG-GATE>` (halt-if-missing) and every `PROJECT.md > …` reference (lines 45, 46, 52, 93, 96, 99, 122, 142, 201). Add one **"Common signals (built-in)"** section defining the generic vocabulary xia2 classifies against:

| Signal | Common definition (built-in) |
|---|---|
| Dependency manifests | `package.json`, `requirements*.txt`, `pyproject.toml`, `go.mod`, `Gemfile`, `Cargo.toml`, `pom.xml`, `build.gradle`, `*.csproj` |
| Data-loss / migration | `migrations/`, `alembic/`, `*.sql` with DDL (`CREATE/ALTER/DROP TABLE`) |
| Entry points | `main.*`, `app.*`, `index.*`, `cmd/`, `routes/`, `controllers/`, `pages/`, `api/`, `handlers/` |
| Auth surfaces | paths/identifiers matching `auth\|login\|logout\|session\|jwt\|oauth\|password\|token\|rbac\|permission` |
| Public API contract | OpenAPI/`*.proto`/GraphQL schema files; route decorators (`@app.\|@router.\|@Get\|@Post`) |
| High-blast (generic) | CI config (`.github/workflows/`), settings/config files, hooks, DI containers, shared base classes — by common name **and** the "imported by many" signal via `code-review-graph` when available |
| Knowledge base | `docs/solutions/INDEX.md` (harness convention — hardcoded) |
| Recent decisions | `specs/` (harness convention — hardcoded) |

The Decision Procedure (Deep / Quick / Standard) keys off these live-detected signals instead of a curated list. No behaviour change to the *output* shape — only the *source* of the signals.

Rename the skill's framing from "portable via swapping PROJECT.md" to "portable via common signals" (SKILL.md:9 intro).

### 2. Delete `xia2/PROJECT.md` + `xia2/PROJECT.template.md`

No longer read. (No optional-override layer — the owner asked to remove project-specific entirely. A future `.xia2-signals` override can be added if a project ever needs it; out of scope now.)

### 3. Preserve scaffolding — relocate templates + a tiny deterministic init

- **Move** `skills/bootstrap-xia2/templates/*` (6 files) → `templates/structure/`.
- **Add `scripts/init-structure.sh`** (~30 lines, create-if-missing, idempotent, tested): for each `(template → destination)` row, write the template only if the destination is absent; report `created` / `exists`. This is the mechanical residue of bootstrap's scaffolding step, as code instead of skill-prose.
- `install-harness.sh` never writes the project root (verified — deliberate invariant), so scaffolding stays a **one-line opt-in** a consumer runs once: `bash .claude/scripts/init-structure.sh` (or the harness deploys the script and README documents it). For THIS repo it's a no-op (all 6 destinations exist).
- The two stack-profile rows that bootstrap also scaffolded (`rules/architecture.md`, `guidelines.md`) drop out of scaffolding: in the common model those stay as the repo's own files / the `_skeleton` generic (templates/stacks/ untouched by this change).

### 4. Delete `skills/bootstrap-xia2/` entirely (after the template relocation)

### 5. Rewrite every reference (the "everything still works" guarantee)

- `xia2/SKILL.md:28,86,238` — gate + "run /bootstrap-xia2" → common-signals (no bootstrap).
- `rules/architecture.md:20,26`, `rules/guidelines.md:6` — drop "generated by /bootstrap-xia2"; state these are edited directly or start from `templates/stacks/_skeleton/`.
- `agents/README.md`, `agents/PROJECT.template.md` — drop bootstrap-render references; `agents/PROJECT.md` becomes a plain maintained file (already filled for this repo).
- `README.md:83` — resync-guard wording ("bootstrap-xia2-generated files kept") → generic "locally-generated files kept".
- `harness-manifest.json:94` — remove `bootstrap-xia2` from the skill inventory (check_manifest).
- `CLAUDE.md`, `skills/README.md` — drop bootstrap-xia2 from the skill list / workflow map; note xia2 is now config-free.

### 6. agents/PROJECT.md in the common model

Keep it as a **static, maintained** convention index (it's already filled + mostly generic — points at rules/behavior.md, skills/README.md, run-tests.sh). Its bootstrap-refresh coupling is dropped; drift is a manual edit. For consumers, it ships as a reasonable generic default they may tweak.

## What must NOT break (verification targets)

- `/xia2` runs and classifies with **no PROJECT.md present** (the whole point).
- Structural init recreates all 6 files in a bare repo (init-structure test).
- doc-truth lint (no dangling path refs), check_manifest (inventory consistent), full suite green.
- `session-knowledge.sh` still finds `docs/solutions/INDEX.md`; `/compound` still writes it — unaffected (those were always common).

## Risks

- **Redefine-the-system change** — alters the risk-classification source of truth (curated → common). Escalation-class; hence owner-approval-gated before execution. Reversible via `git revert` (skill prose + one script; no data migration).
- **Precision loss** on project-specific high-blast files not matching common patterns — mitigated by the risk hooks + reviews, and acceptable per the stated audience.
- **xia2 is a core skill** — the rewrite is prose-only but central; the plan will keep the Decision Procedure's output contract identical and only swap the signal source.
- Consumer onboarding gains a one-line `init-structure.sh` step in place of `/bootstrap-xia2` — net simpler, documented in README.

## Execution shape (for the plan, on approval)

Single high-risk lane, ~2 waves: (1) relocate templates + add init-structure.sh + test; rewrite xia2 to common signals; delete PROJECT.md/template + bootstrap skill; update all references. (2) full-suite + machine-verified evidence, incl. a "xia2 classifies with no PROJECT.md" check and an init-structure round-trip in a temp repo.
