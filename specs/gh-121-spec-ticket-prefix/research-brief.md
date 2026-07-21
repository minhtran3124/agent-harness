# Research Brief — Ticket-source prefix for spec folders (gh-121)

Depth mode: **Deep** (high-blast `hooks/*` + shared `run-tests.sh` test contract in verification scope; high-risk lane). Date: 2026-07-20.

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse existing — convention change rides entirely on existing infrastructure; new bash `.test.sh` cases auto-collect, zero engine/hook code changes |
| **Why this is the lightest credible path** | Every gate already parses `specs/[^/]+/` generically, and `run-tests.sh` auto-globs `tests/hooks/*.test.sh` + `tests/scripts/*.test.sh`, so both the convention and its proof land without touching a single high-blast file |
| **Confidence** | 90% |
| **Next step** | `/writing-plans` — doc sweep + feature-intake derivation rule + prefixed-slug test cases in existing (or new, auto-globbed) `.test.sh` files |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Meta-repo: Claude Code skill framework / governance harness (no application stack — `techstacks/` intentionally empty for this repo) |
| Primary language + runtime | Bash (hooks, tests) + Python 3 (gate engines: `check_lane_evidence.py`, `verify_summary.py`, `render_plan.py`) |
| Frameworks / platforms | Claude Code hooks (PreToolUse/PostToolUse contract: stdin JSON → exit code), pytest for python engines |
| Relevant packages | none added — no dependency manifests touched |
| Detectable versions | n/a (stdlib bash/python; suite runs via `scripts/run-tests.sh` on ubuntu + macos CI) |
| Important constraints | `rules/behavior.md` (surgical changes, not_observed != absent); doc-truth lint scans only 4 core docs; `run-tests.sh` is itself a high-blast hard-gate file |

---

## Feature Understanding and Assumptions

- **Requested feature:** Spec folders carry a ticket-source prefix (`gh-<issue#>-<slug>`, `lin-<TICKET-ID>-<slug>`, plain `<slug>` fallback); all referencing docs synced; gates verified compatible (issue #121; design approved in `design.md`).
- **What success appears to mean:** `/feature-intake` derives prefixed names; docs state one convention; `bash scripts/run-tests.sh` green including new prefixed-slug regression cases; zero gate regressions on grandfathered folders.
- **Assumptions from the request:** Decisions E001/E002 + convention-only enforcement are fixed (human-recorded in `ESCALATIONS.md`).
- **Assumptions still needing confirmation:** none material — the one load-bearing claim ("gates are slug-shape-agnostic") was verified twice (my grep + independent spec-review re-grep).

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | All 10 parsers match the folder segment generically: `^specs/[^/]+/` (commit-quality-gate:58,86), `specs/[^/]+/SUMMARY\.md` + `cut -d/ -f2` (bookkeeping:57), `(^|/)specs/[^/]+/SUMMARY\.md$` (ci-strict-gate:38), `specs/*` case (branch-isolation-guard:35), `specs/*/PLAN.md` globs (blast-radius:37, render-plan-on-write:17), path-join on slug (check_lane_evidence.py:187, verify_summary.py:9), generic globs (harness-audit, lint-doc-truth:44) |
| `Local` | `run-tests.sh` **auto-globs** `tests/hooks/*.test.sh` and `tests/scripts/*.test.sh` — a new `.test.sh` file is collected with no runner edit; python tests require an explicit `PYTESTS` edit (high-blast) — avoided by writing bash tests |
| `Local` | Hermetic test harness exists: `tests/lib.sh` (`new_repo`, `stage`, `run_hook`, assert helpers, mktemp + cleanup); existing fixtures use plain slugs (`specs/x/`, `specs/demo/`, `specs/my-feature/`) — prefixed variants slot in directly |
| `Local` | `docs/solutions/harness/test-and-doc-lint-gate-scope.md` (confirmed 2026-07-17): doc-truth lint scans only `CLAUDE.md`, `README.md`, `HARNESS.md`, `skills/README.md`; `specs/**` skipped by design → the doc sweep can't break the lint via specs paths, and only the 4 core docs' path references are mechanically checked |
| `Upstream` | github/spec-kit issue #407 requests exactly this (ticket-ID-configurable branch + `specs/{branch}` folder derivation) — validates prefix-at-creation + branch-inherits-folder-name as the ergonomic pattern |
| `Upstream` | Machine-readable prefix pattern (`REQ-001-*` folders) used for programmatic traceability in agentic spec workflows — same rationale as ours |
| `Inference` | No competing in-flight decision: `ls -1t specs/` + grep of recent `design.md`s (phase2-wave2, plan-at-a-glance) show slug mentions only in passing |

---

## Local Findings

- **Relevant files:** the design's §3 checklist (3 templates, 4 rules, ~13 skill docs/prompts) plus `tests/hooks/{commit-quality-gate,risk-corroboration,branch-isolation-guard,blast-radius-check,render-plan-on-write}.test.sh` and `tests/scripts/{bookkeeping,ci-strict-gate,harness-audit,lint-doc-truth}.test.sh`.
- **Existing abstractions:** `tests/lib.sh` hermetic-repo helpers — the entire regression suite for prefixed slugs is `stage "$repo" "specs/gh-999-fixture/SUMMARY.md" …` variants of existing cases.
- **Conventions worth preserving:** co-located `scripts/test_*.py` stay in `scripts/` (import-sibling pattern); historical specs keep old paths (surgical-changes rule — grandfathering aligns with it).
- **What can likely be reused:** everything — no new engine, no new hook, no new dependency.
- **What appears missing locally:** only (a) the derivation rule text in `feature-intake/SKILL.md`, (b) the canonical convention statement, (c) prefixed-slug test cases. That is the whole feature.

## Upstream Findings

- **Repositories inspected:** github/spec-kit (AGENTS.md + issue #407), Fission-AI/OpenSpec discussion #768 (monorepo spec naming), agentic-workflow prefix patterns (REQ-*).
- **Pattern present upstream:** ticket-prefixed spec folders derived at creation time, branch name = folder name — matches our §2 exactly.
- **Gaps:** spec-kit treats the format as *configurable*; we deliberately hard-code one vocabulary (`gh-`/`lin-`) per the YAGNI non-goal. No upstream code to import — pattern-level validation only.

## Docs Findings

- **N/A with justification:** no external library, dependency, or versioned platform API is involved; the "official docs" axis has no target. Claude Code hook contract is exercised unchanged.

---

## Recommendation

- **Primary recommendation:** Reuse existing (convention + tests on existing infrastructure); build nothing.
- **Why lightest credible path:** the two riskiest-looking parts of issue #121 dissolve on evidence — hooks need **no** changes (all parsers shape-agnostic, verified twice) and test wiring needs **no** `run-tests.sh` edit (auto-glob). Remaining work is prose (doc sweep + intake rule) plus fixture-level test cases.
- **Why the next-best alternative lost:** adding a naming-enforcement gate (warn) was declined by the human (E002/enforcement decision) and is logically weak with a plain-slug fallback; python-based tests would force a high-blast `PYTESTS` edit for zero added power.
- **What would change this recommendation:** discovery of a parser that keys on slug *shape* (e.g. a regex assuming no digits/case in the first segment) — none found; the test suite is the tripwire.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** low. Doc sweep is wide but gloss-level; risk of drift mitigated by pointing docs at the canonical statement. CI doc-truth lint only checks the 4 core docs, so most of the sweep is judgment-verified, not machine-verified (residual risk accepted by design).
- **Evidence gaps:** none load-bearing.
- **Version uncertainties:** none.
- **Follow-up questions:** none — decisions are recorded.

## Source Pack

- **Local files read:** `scripts/run-tests.sh`, `tests/lib.sh`, `tests/hooks/*` + `tests/scripts/*` (listing + fixture greps), `hooks/*.sh` + `scripts/*.{sh,py}` (specs-parsing grep), `templates/structure/specs-README.md`, `specs/README.md`, `docs/solutions/harness/test-and-doc-lint-gate-scope.md`, `docs/solutions/INDEX.md` + `critical-patterns.md` (session-loaded), `specs/gh-121-spec-ticket-prefix/{design,SUMMARY,ESCALATIONS}.md`
- **Upstream:** [spec-kit AGENTS.md](https://github.com/github/spec-kit/blob/main/AGENTS.md) · [spec-kit issue #407](https://github.com/github/spec-kit/issues/407) · [OpenSpec discussion #768](https://github.com/Fission-AI/OpenSpec/discussions/768)
- **Official docs:** none applicable (no external dependency).

## Evidence Boundary

> Confirmed from artifacts: parser shape-agnosticism (grep, all 10 parsers, line-cited; independently re-verified by spec reviewer); test auto-glob behavior (`run-tests.sh` read); hermetic fixture pattern (`tests/lib.sh` read); doc-truth lint scope (solution doc, confirmed 2026-07-17, cross-checked against `lint-doc-truth.sh:44`).
> Inferred from patterns: that no *other* consumer outside the repo parses spec folder names (e.g. external dashboards) — none referenced anywhere in-repo.
> Not checked: nothing load-bearing. (`post-merge-maintenance.yml` was initially deferred, then verified: it contains no specs-path parsing of its own — it only invokes `scripts/bookkeeping.sh`, whose slug extraction was already confirmed generic.)
