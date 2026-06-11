# xia2 — Project Configuration

This file provides project-specific signal mappings consumed by `xia2/SKILL.md`. It is a reusable template — regenerate it per project.

> **Maintenance:** auto-scan via `/bootstrap-xia2` (init or update mode), then human-review. Re-validate after major architectural changes.

---

## Project identity

Describe what this project is and how to locate it.

- **Name:** harness-skills
- **Stack:** Bash hooks + Python 3 scripts + Markdown skills, GitHub Actions CI
- **Repo root (relative to this file):** `../../`

---

## High-Blast-Radius Files

List the files that, when touched, force **Deep** review regardless of how small the change appears.

- `settings.json` — hook registration; any change here changes what runs every session
- `hooks/*.sh` — auto-run on every session/edit/commit trigger; bugs affect every workflow
- `skills/visual-planner/render_plan.py` — core skill engine; output consumed by plan-render pipeline
- `templates/SUMMARY.template.md` — schema machine-read by `hooks/risk-corroboration.sh` and the trust-metrics ledger; header field order and names are load-bearing
- `scripts/run-tests.sh` — CI contract; any change here changes what `harness-ci` validates on ubuntu + macos

> Add new entries when a single file becomes a bottleneck for many features. An empty list means the Deep override loses a key signal.

---

## Dependency Manifests

Name the files that declare dependencies, and which ones should trigger Deep when changed.

- `scripts/run-tests.sh` — the test entry point; changing what suites run is a contract change that **triggers Deep**
- `hooks/*.sh` — hook scripts are both implementation and "dependency" of the harness runtime; any addition/removal **triggers Deep**
- `.github/workflows/` — CI matrix definitions; changes affect reproducibility across ubuntu + macos

---

## Shared Runtime Contracts

Configuration objects, modules, or protocol shapes whose contract change affects many call sites.

- **SUMMARY header 4-field block** (`Lane` / `Confidence` / `Reason` / `Flags` in `templates/SUMMARY.template.md`) — `hooks/risk-corroboration.sh` greps the `Lane:` line to corroborate against staged diffs; the trust-metrics ledger reads all four fields; renaming or reordering any field breaks machine readers
- **Hook exit-code contract** — exit `0` = pass (allow), exit `2` = block (deny); any hook deviating from this breaks the `PreToolUse` gate silently
- **Hook table truthfulness** — `CLAUDE.md` hook table must match `settings.json` registrations; `scripts/lint-doc-truth.sh` enforces this at CI time (doc-truth lint)
- **Trust-metrics ledger columns** (`docs/harness-experimental/trust-metrics.md`) — `Date | Slug | Lane | Confidence | Flags | Escalated | Outcome | Notes` must remain stable for cross-task trend analysis

---

## Session/Transaction Primitives

This is a tooling/meta repo — there is no DB session layer. The analogous "scope" primitives are:

- **Git worktrees** (via `/using-git-worktrees`) — isolate feature work in a separate checkout; switching from main-tree to worktree is a scoping decision that affects all subsequent file edits
- **Hook registration in `settings.json`** — hooks fire globally per trigger; adding/removing a hook is the harness equivalent of changing transaction scope; treat as Deep
- **Project rule:** background/long-running skill steps must never write to `specs/` in the main-tree checkout while a worktree is active — risk of clobber; switching scope between worktree and main-tree mid-task is a Deep change

---

## Auth Surfaces

This repo has no HTTP auth layer. The analogous trust surface is:

- `hooks/risk-corroboration.sh` — the gate that blocks commits when Lane is under-declared relative to the staged diff; any weakening of its regex or exit-code logic is a security-equivalent change
- `hooks/commit-quality-gate.sh` — secrets scan + debug artifact check + targeted pytest; weakening is a hard gate

---

## Knowledge Bases

Files to read at Step 2b in addition to AGENTS.md/CLAUDE.md/README.md.

- `.claude/rules/architecture.md` — authoritative architecture reference (layers, models, services) for target FastAPI projects that use this harness
- `.claude/rules/guidelines.md` — code style, error handling, async, testing conventions for target projects
- `docs/solutions/` — solved problems with metadata
  - **Index:** read `docs/solutions/INDEX.md` first (single read, O(1)); fallback grep keys like `` module: `harness-bootstrap` ``, `` affects.*hooks/ ``
  - **Critical patterns:** `docs/solutions/critical-patterns.md` — always read regardless of domain
  - **Stale marker:** entries with `confidence: low` or missing `confirmed_at`, or `confirmed_at` older than 30 days, are potentially stale

---

## Recent Decisions Folder

Where recent design/decision records live, and how far back to look.

- **Path:** `specs/*/` (gitignored; local-only)
- **Schema:** one subfolder per slug (e.g. `specs/my-feature/`), containing `SUMMARY.md`, optionally `PLAN.md`, `design.md`, `research-brief.md`
- **Lookback:** 60 days

---

## Public API Contract Types

For the Quick condition: changes to these break the contract → fail Quick.

- Hook script interfaces: input env vars and exit codes consumed by `settings.json` trigger registration
- SUMMARY header field names and order (machine-read by `risk-corroboration.sh` and the ledger)
- Skill `SKILL.md` invocation contracts (the slash-command name and expected input/output shape)
- `render_plan.py` CLI flags (consumed by `hooks/render-plan-on-write.sh` and `view_plan.py`)

---

## Entry Point Patterns

For the Quick condition: any change inside these is **NOT** Quick.

- `hooks/` — all hook scripts; auto-run on every edit, commit, or session trigger
- `settings.json` — hook registration and permissions; governs all automated behavior
- `scripts/run-tests.sh` — CI entry point; defines what the test suite is
- `skills/*/SKILL.md` — skill prompt programs; define the entire workflow behavior
- `skills/visual-planner/render_plan.py` — deterministic plan renderer; core skill engine

---

## Notes for maintainers

- **High-blast list is the highest-leverage signal** — keep it current as new bottlenecks emerge.
- **Shared config contract evolves** — when adding new fields to the SUMMARY header or changing hook exit codes, treat it as a Deep change since downstream scripts rely on fixed shapes.
- **Client-consumed protocols** — adding new event types to a hook or changing SUMMARY field names is Deep (machine readers must be updated).
