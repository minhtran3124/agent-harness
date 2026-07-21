# Changelog

All notable changes to this harness are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions are tracked in the root `VERSION`
file. Bump on merge: **patch** for fixes/docs, **minor** for a new skill/hook or a changed
skill/hook contract, **major** for a breaking change to the workflow or a machine-read schema.

## [Unreleased]

- feat(rules): path-scope the contextual rules (`plan-format`, `wave-parallelism`, `auto-correct-scope`) via `paths:` frontmatter — loaded on demand instead of every session (~55% off the always-on rule payload); consuming skills gained explicit Read steps (write-flows don't trigger `paths:` injection — verified empirically on v2.1.216). Phase 3 (orchestration.md core split) deferred. Research: `docs/research/2026-07-21-dynamic-rule-loading-research.md`

## [2.14.0] — 2026-07-21

- feat(rules): path-scope contextual rules for on-demand loading (PR #141)

## [2.12.0] — 2026-07-21

- refactor(create-pr): drop File Changes table, reviewer-first Summary, conditional Diagram (PR #139)

## [2.11.0] — 2026-07-21

- refactor: remove dormant protected-path guard (PR #133)

## [2.10.0] — 2026-07-21

- feat: add ticket-source prefix for spec folders (gh-/lin-) (PR #126)
- feat: remove unused agent memory (PR #131)

## [2.9.1] — 2026-07-20

- chore(lint): widen doc-truth scope to agents/ and rules/ (4 → 17 docs) (PR #122)

## [2.9.0] — 2026-07-20

- feat(hooks): wire check_lane_evidence into the commit gate (Check 1.6) (PR #120)

## [2.8.0] — 2026-07-20

- docs(skills): sync workflow docs with current code (PR #119)

## [2.7.1] — 2026-07-17

- compound: skill-eval playbook + harness test/doc-lint gate scope (PR #116)

## [2.7.0] — 2026-07-17

- refactor(evals): rename benchmarks/ -> evals/, split skills vs workflow (PR #114)

## [2.6.7] — 2026-07-17

- feat(benchmarks): intake-classifier eval + blind baseline (PR #112)

## [2.6.6] — 2026-07-17

- docs(specs): backfill ### Verify block for entropy-trend SUMMARY (PR #110)

## [2.6.5] — 2026-07-17

- docs(solutions): refresh 4 stale KB entries against ground truth (PR #108)

## [2.6.4] — 2026-07-17

- docs(solutions): automation-readiness design gate (option A) (PR #106)

## [2.6.3] — 2026-07-17

- docs(techstacks): clarify AI-consumed / project-authored (keep at root) (PR #104)

## [2.6.2] — 2026-07-17

- feat(scripts): verify-row lint (pipe-free + <60s Verify commands) (PR #102)

## [2.6.1] — 2026-07-17

- docs(compound): crystallize 3 session lessons (PR #100)

## [2.6.0] — 2026-07-17

- feat(harness): decouple tech-stack into a project-owned techstacks/ folder (PR #98)

## [2.5.2] — 2026-07-17

- fix(deploy): prune deleted-skill orphans from .claude (safe-by-construction manifest) (PR #96)

## [2.5.1] — 2026-07-17

- feat(install): fold init-structure into install-harness (one command) (PR #94)

## [2.5.0] — 2026-07-17

- Promote v3 → main: remove bootstrap-xia2 (xia2 zero-config) (PR #92)

## [2.4.0] — 2026-07-17

- docs: correct branch-isolation-guard trigger in 5 stale sites (PR #88)

## [2.3.0] — 2026-07-17

- Promote v3 → main: Phase 2 waves 2 + 3 (PR #86)

## [2.2.2] — 2026-07-17

- Promote v3 → main: Phase 2 wave 1 + v3 CI wiring (PR #80)

## [2.2.1] — 2026-07-17

- docs(reviews): Phase 2 deep review — verify each deletion target (supersedes audit line items) (PR #77)

## [2.2.0] — 2026-07-16

- feat(hooks): mechanize the ESCALATIONS deny-on-no-response gate (review C5) (PR #75)

## [2.1.0] — 2026-07-16

- fix(hooks): strip comments before risk-corroboration keyword scan (review C4) (PR #73)

## [2.0.1] — 2026-07-16

- fix(ci): rewire post-merge bookkeeping to main (review C3) (PR #71)

## [2.0.0] — 2026-07-16

Milestone: the **v2 line** (0.3.0 → 0.14.0) is promoted to `main` and tagged
[`v2.0.0`](https://github.com/minhtran3124/agent-harness/releases/tag/v2.0.0) — the
rebuilt risk-and-trust harness. Highlights across the line: lane-based routing enforced
at write time (`branch-isolation-guard.sh`), `harness-manifest.json` as the single source
for hard gates, evidence-over-assertion verify/rollback gates, the `/intent-review` third
oracle, self-summarizing plans (visual-planner At-a-glance block), event-sourced post-merge
bookkeeping, conflict-guarded re-sync, the product-contract map, stack-agnostic `rules/`, and
tracked `specs/`. See the per-version sections below for the full merge history.

Folded in from Unreleased at tag time:

- feat(q3): product-contract map (Level A) — `contracts` block in `harness-manifest.json`, `scripts/check-contract-impact.sh` advisory mapper, `check_manifest.py` path validation, and a contract-impact reminder section in `harness-audit.sh` (MIN-64)
- fix(install-harness): a tty-less re-sync without `--yes` now prints the actionable "Re-run with `--yes`" message instead of dying on a raw `/dev/tty: Device not configured`; `--overwrite-conflicts` now implies `--yes` (it already named the destructive outcome), so `curl … | bash -s -- --overwrite-conflicts` works non-interactively. Covered by `tests/scripts/install-tty-gate.test.sh`
- fix(deploy-harness): `rules/behavior.md` is now conflict-guarded like the other project-owned files — a customized copy is kept and the incoming version saved as `rules/behavior.md.harness-incoming`, instead of being overwritten silently

## [0.14.0] — 2026-07-15

- fix: conflict-guarded re-sync — stop clobbering bootstrap-xia2 outputs (PR #50)

## [0.13.0] — 2026-07-15

- feat(visual-planner): self-summarizing PLAN.md — At-a-glance block (#54) (PR #63)

## [0.12.0] — 2026-07-15

- correctness-review: find by six parallel angles; fix four aborts in harness-status.sh (PR #51)

## [0.11.0] — 2026-07-13

- feat(branch-isolation): every lane cuts a branch before implementing — close the tiny-lane hole (PR #52)

## [0.10.0] — 2026-07-13

- fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback (PR #53)

## [0.9.0] — 2026-07-09

- docs: clarify harness prompts (root docs + sub-agents + rules) (PR #48)

## [0.8.1] — 2026-07-08

- feat(q3): product-contract map (Level A) — contract-level blast radius [MIN-64] (PR #46)

## [0.7.3] — 2026-07-04

- feat: entropy has a trend — 6-check harness-audit + per-merge JSONL log (v0.3 Wave 4) (PR #42)

## [0.7.2] — 2026-07-04

- chore(hygiene): v0.3 Wave 6 — plan statuses shipped + research docs committed (PR #40)

## [0.7.1] — 2026-07-04

- fix(evidence): verify gates reject trivial proof — v0.3 Phase 3 (PR #38)

## [0.7.0] — 2026-07-04

- feat(governance): harness-manifest single source for hard gates — v0.3 Phase 2 (PR #35)

## [0.6.0] — 2026-07-03

- feat(ci): event-sourced post-merge bookkeeping — v0.3 Phase 1 (PR #34)

## [0.5.0] — 2026-07-03

- docs(skills): fix doc-truth drift across skill files — v0.3 Wave 0c (PR #33)

## [0.4.0] — 2026-07-03

- fix(hooks): session-knowledge resolves repo root via git (DR-2) — v0.3 Wave 0b (PR #32)

## [0.3.0] — 2026-07-03

- fix(hooks): close commit-gate command-matching bypass (DR-1) — v0.3 Wave 0a (PR #31)

## [0.2.0] — 2026-06-14

### Changed
- **Stack-agnostic `rules/` (MIN-25).** The `rules/` governance layer is no longer FastAPI-only.
  Universal rules ship identical everywhere; stack-specific guidance is a swappable profile:
  - FastAPI content moved verbatim to `templates/stacks/fastapi/{architecture,guidelines}.md`;
    `rules/architecture.md` + `rules/guidelines.md` are now stack-neutral skeletons (deploy still
    ships valid files).
  - `rules/plan-format.md`, `auto-correct-scope.md`, `wave-parallelism.md` keep FastAPI snippets
    only inside blocks tagged `example — substitute your stack`; in-prose stack tokens genericized.
  - **`bootstrap-xia2` now renders the stack profile per repo** — detect stack → bundled
    `templates/stacks/<stack>/` profile as a human-reviewed draft, else the generic
    `templates/stacks/_skeleton/` fallback; never a wrong-stack profile. (skill-contract change → minor)



First versioned snapshot of the harness — the skill framework, governance rules, hooks, CI, and
the research-driven gap-closure work.

### Added
- **Skill chain** — intake → brainstorm → research (xia2) → plan → execute → review
  (correctness + intent oracles) → compound → finish, plus `visual-planner` and `bootstrap-xia2`.
- **Machine gates** — `risk-corroboration`, `commit-quality-gate`, `blast-radius-check`,
  `branch-guard`, `check-untracked-py`, `ruff-on-edit`, `render-plan-on-write`, `scope-gate`,
  `state-breadcrumb`, `session-knowledge` (wired); `auto-test-on-change`,
  `protected-path-guard` (dormant).
- **CI** — `harness-ci.yml` runs `scripts/run-tests.sh` (bash contract tests + python units) and
  `scripts/ci-strict-gate.sh` (strict-in-CI proof gate for hard-gate paths) on ubuntu + macos.
- **Gap-closure (from 6 research docs)** — ratchet backlog in `/compound` (P1-B);
  `scripts/harness-audit.sh` advisory drift detector (P1-C); MCP boundary-of-trust note (P2-H);
  review-chain micro-benchmark re-run via the read-only `reviewer` agent, 5/5 catch (P3-I);
  `scripts/check_lane_evidence.py` lane→evidence single source (P3-J); story-size warning in
  `check_plan_format.py` (P3-K); `protected-path-guard` break-glass hook (P3-L).
