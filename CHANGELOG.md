# Changelog

All notable changes to this harness are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions are tracked in the root `VERSION`
file. Bump on merge: **patch** for fixes/docs, **minor** for a new skill/hook or a changed
skill/hook contract, **major** for a breaking change to the workflow or a machine-read schema.

## [Unreleased]

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
