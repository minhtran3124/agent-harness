# gh-258-open-questions-register — Research Brief

Depth: **Deep** (intake lane `high-risk`, mapped per `rules/research-depth.md`). No upgrade or
downgrade: the evidence below found no new Deep signal beyond the intake's (no `hooks/`, no
dependency, no external surface). Design: `specs/gh-258-open-questions-register/design.md`
(approved 2026-10-09).

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | build from scratch, small: one new stdlib script and template; reuse the existing gate, deploy, test-harness and rewrite machinery unchanged |
| **Why this is the lightest credible path** | no existing parser reads bullet-field blocks or plan status in a way the CI shell section can call without importing a high-blast module, and every wiring point (CI gate, deploy allow-list, path rewrite, doc-truth lint, test lib) already exists |
| **Confidence** | 85% |
| **Next step** | `writing-plans` for `specs/gh-258-open-questions-register/` |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | harness meta-repo: Markdown skills/rules, bash hooks and CI scripts, stdlib Python helpers |
| Primary language + runtime | Bash; Python 3 stdlib (CI uses `actions/setup-python@v5`, `python-version: '3.x'`) |
| Frameworks / platforms | none; tests are bash (`tests/lib.sh`) and pytest |
| Relevant packages | pytest only, for tests (installed in CI's `strict-gate` job; shared venv in `scripts/run-tests.sh`) |
| Detectable versions | no manifest pins Python; scripts use `str \| None` annotations, so 3.10+ in practice (Inference) |
| Important constraints | CLAUDE.md: run `bash scripts/run-tests.sh` before changing `scripts/`; ci-strict-gate block tier covers `templates/`; doc-truth lint fails on missing paths; SKILL.md 600-word ceiling |

## Feature Understanding and Assumptions

- **Requested feature:** #258 item 3, an optional `specs/<slug>/QUESTIONS.md` register of
  non-blocking open questions plus a warn-first, traceability-tier check that a phase does not ship
  while a question closing at it is open.
- **What success appears to mean:** SC-1..SC-6 in `design.md`: exit codes per the error table, the
  CI section reached by specs-only shipping PRs and never bypassing existing tiers, the consumer
  copy reading the consumer's `specs/`, wiring pinned by contract tests, suite green.
- **Assumptions from the request:** settled in design D1–D7 (slug-based `closes-at`, standalone
  script, warn default, CI section before the early exit, malformed registers are findings,
  blocking questions stay in `ESCALATIONS.md`, cwd root).
- **Assumptions still needing confirmation:** none that change the recommendation. One planning
  detail is open: what the CI section does when `scripts/check_open_questions.py` is absent from
  the checkout (see Risks).

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/ci-strict-gate.sh`: `DIFF=$(git diff --name-only "$BASE"...HEAD …)` then `[ -z "$DIFF" ] && exit 0`, then the tier selection ending in `exit 0  # no gated paths touched`. The new section fits between them. |
| `Local` | `.github/workflows/harness-ci.yml` job `strict-gate`: `actions/checkout@v4` with `fetch-depth: 0`, then `git fetch origin "$BASE_REF"`, so `git merge-base` and `git show <mb>:<path>` have full history. |
| `Local` | `scripts/deploy-harness.sh`: `CONSUMER_SCRIPTS=(` allow-list (6 entries today), whose header says "Add a row only when a consumer-facing skill/rule references it"; the Python rewrite block maps `scripts/<name>` to `.claude/scripts/<name>` only for names in that list. |
| `Local` | `scripts/resolve_finish_context.py` `main()`: `--root` defaults to `Path.cwd()`; the harness-only `check_manifest.py` / `check_frontmatter_contract.py` resolve from `__file__` instead. |
| `Local` | `scripts/lint-doc-truth.sh` deploys to a temp target and fails when a consumer doc names a `scripts/*` helper that is not in the derived tree, so a finish-skill mention without the `CONSUMER_SCRIPTS` row fails CI. |
| `Local` | `scripts/check_skill_tool_conformance.py`: every runnable command in a skill body must match its `allowed-tools`; `finishing-a-development-branch` declares bare `Bash`, so a new command needs no grant change. |
| `Local` | `scripts/audit_skill_prompts.py`: `SKILL_WORD_CEILING = 600`. `wc -w` on 2026-10-09: finishing 501, brainstorming 430 (measured 2026-10-09 `wc -w`). |
| `Local` | `tests/scripts/ci-strict-gate.test.sh`: fixture repos via `mkrepo` (copies only `verify_summary.py` into `scripts/`), `commit_run` diffs against the pre-commit SHA; reusable for the three new cases if `mkrepo` also copies the new script. |
| `Local` | `tests/scripts/consumer-subset.test.sh`: deploys with `--target` into a temp dir and asserts the allow-listed helpers land in `.claude/scripts/`; the new case can run the deployed copy with `cwd` set to the temp target. |
| `Local` | `tests/scripts/finishing-branch-contract.test.sh`: `grep -q` presence checks on the finish SKILL.md; the new assertion follows the same shape. |
| `Local` | `scripts/run-tests.sh`: pytest discovers `find scripts runtime skills -name 'test_*.py'`, so `scripts/test_check_open_questions.py` is picked up with no runner change. |
| `Local` | `hooks/commit-gate.sh` `check_escalations` parses ESCALATIONS blocks with a line grep (`^[-*]?[[:space:]]*decision:[[:space:]]*pending`); no shared Python block parser exists. |
| `Local` | `skills/visual-planner/render_plan.py` `parse_frontmatter` parses PLAN frontmatter robustly, but it is a core skill engine (high-blast in the manifest); importing it from a new CI section adds coupling to a high-blast file. |
| `Local` | `find specs -name QUESTIONS.md` on the `spec-format` checkout: no results (2026-10-09). |
| `Inference` | The CI section can read a plan's status with a frontmatter-bounded `awk` (lines between the first two `---`) at both `HEAD` and the merge base, avoiding any import. |

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `scripts/ci-strict-gate.sh`,
  `scripts/deploy-harness.sh`, `scripts/resolve_finish_context.py`, `scripts/lint-doc-truth.sh`,
  `scripts/check_skill_tool_conformance.py`, `scripts/audit_skill_prompts.py`,
  `templates/ESCALATIONS.template.md`, `templates/structure/specs-README.md`,
  `skills/finishing-a-development-branch/SKILL.md`, `skills/brainstorming/SKILL.md`,
  `tests/scripts/{ci-strict-gate,consumer-subset,finishing-branch-contract}.test.sh`,
  `.github/workflows/harness-ci.yml`.
- **Existing abstractions or extension points:** the `CONSUMER_SCRIPTS` allow-list plus its path
  rewrite; the ci-strict-gate `DIFF` variable and its `$BASE`; the `tests/lib.sh` `t` / `pass` /
  `fail` / `assert_rc` helpers and `_CLEANUP_DIRS`; pytest auto-discovery.
- **Conventions worth preserving:** a module docstring with `Verifies:` / `Does not verify:` and
  the exit-code contract (as in `check_skill_tool_conformance.py`); stdlib only; `--root` option;
  an env flag that turns warn into block (`REQUIRE_NOT_AUTO_VERIFIED`, `REQUIRE_SCRIPTS_PROOF`);
  warn output that still says what is missing (`gate_fail` comment in ci-strict-gate).
- **What can likely be reused:** all wiring and test scaffolding above, unchanged in shape.
- **What appears missing locally:** a parser for `## OQ-n` bullet blocks, and a plan-status read
  usable from the CI shell section. Both are new, small and local.

## Upstream Findings

- **Repositories inspected:** `tamnd/rupg` `spec/24-open-questions.md` (read during the #258
  review, 2026-10-08): never-reused IDs, raised-by doc, closing milestone, decided-by, stated
  default, closed section with one-line evidence, appended progress notes.
- **Pattern or capability already present upstream:** the register shape; rupg enforces it by
  convention, not by a check.
- **Files, modules, or areas worth modeling:** the field set and the "non-blocking unless stated"
  rule, which design D6 maps onto the existing `ESCALATIONS.md` split.
- **How closely the upstream pattern matches this repo:** the fields match; rupg's milestones map
  to this repo's per-phase spec slugs (design A2).
- **Any upstream gaps or uncertainties:** rupg was cloned shallow, so how its register evolved over
  time was not seen (#258 scope note).

## Docs Findings

No external surface: the change adds no dependency, integrates no external system and uses no
version-specific API (stdlib, bash, git plumbing already used by the gate).

## Recommendation

- **Primary recommendation:** build a stdlib `scripts/check_open_questions.py` with its own
  block parser, and give the CI section a frontmatter-bounded `awk` status read; reuse all
  existing wiring and test scaffolding.
- **Why this is the lightest credible path:** every integration point already exists and the doc
  lint, conformance check and test runner pick the new files up without changes; the only new
  logic is the parser and the shipping detection.
- **Why the next-best alternative lost:** importing `render_plan.parse_frontmatter` into the gate
  couples a CI script to a high-blast core engine for a one-field read; reusing the
  `check_escalations` grep style in bash cannot express the per-block validation that design D5
  requires.
- **What would change this recommendation:** a second consumer needing the same block parser
  (then extract a shared module), or a decision to move enforcement into `hooks/` (approach 3).

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - *Script absent in a checkout.* If the CI section runs where `scripts/check_open_questions.py`
    does not exist (an old fixture, a consumer copying the gate), an unguarded call fails the
    gate. Planning must pick: fail loudly or skip with a message. Fixtures in
    `ci-strict-gate.test.sh` must copy the script in `mkrepo`.
  - *Frontmatter variance.* An `awk` status read must stop at the closing `---` and handle
    `status:` with trailing spaces or CRLF; a plan with no frontmatter is "not shipped".
  - *This PR's own CI tier.* Adding `templates/QUESTIONS.template.md` puts the PR in the
    ci-strict-gate block tier, so the high-risk SUMMARY needs Verify rows that re-run clean.
  - *Doc-truth lint ordering.* The finish-skill mention and the `CONSUMER_SCRIPTS` row must land
    in the same commit or wave, or the lint fails between them.
- **Evidence gaps:** the CI job behavior was read from the workflow file, not observed in a run
  (Actions billing limit; local `ci-strict-gate.sh` runs substitute).
- **Version uncertainties:** none material; no version-specific API.
- **Follow-up questions for the user:** none that change the recommendation.

## Source Pack

- **Local files read:** `scripts/ci-strict-gate.sh`, `scripts/deploy-harness.sh`,
  `scripts/resolve_finish_context.py`, `scripts/lint-doc-truth.sh`,
  `scripts/check_skill_tool_conformance.py`, `scripts/audit_skill_prompts.py`,
  `scripts/run-tests.sh`, `scripts/resolve-base-ref.sh`, `hooks/commit-gate.sh`
  (`check_escalations`), `skills/visual-planner/render_plan.py` (`parse_frontmatter`),
  `templates/ESCALATIONS.template.md`, `templates/structure/specs-README.md`,
  `skills/finishing-a-development-branch/SKILL.md`, `skills/brainstorming/references/design-template.md`,
  `tests/scripts/ci-strict-gate.test.sh`, `tests/scripts/consumer-subset.test.sh`,
  `tests/scripts/finishing-branch-contract.test.sh`, `.github/workflows/harness-ci.yml`,
  `specs/codex-support/ROADMAP.md`, `docs/solutions/harness/gate-config-must-read-index.md`,
  `docs/solutions/harness/ratchet-matches-spelling-not-property.md`, `docs/solutions/critical-patterns.md` (headings).
- **Upstream repositories or pages checked:** https://github.com/tamnd/rupg/tree/main/spec (`24-open-questions.md`, `00-README.md`).
- **Official docs domains or pages checked:** - none (local-only; no external surface)

## Evidence Boundary

> Confirmed from artifacts: the ci-strict-gate early-exit structure and `DIFF` computation; CI
> checkout depth; the `CONSUMER_SCRIPTS` allow-list and rewrite; cwd-root precedent; doc-truth
> and conformance behavior; word counts; test scaffolding; absence of any `QUESTIONS.md`.
> Inferred from patterns: that a frontmatter-bounded `awk` is enough for the status read; that
> `ratchet-matches-spelling-not-property` applies to the contract greps (they pin wording, which
> is acceptable for prose contracts but not for behavior, so behavior is pinned by pytest and the
> fixture-repo cases instead).
> Not checked: an actual GitHub Actions run of the modified gate; consumer repos other than the
> deploy-test temp target.
