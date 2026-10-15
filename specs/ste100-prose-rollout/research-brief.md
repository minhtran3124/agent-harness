# ste100-prose-rollout — Research Brief

Written 2026-10-15. Pins: repo 48e7e05 + uncommitted

Depth: **Deep** (intake lane `high-risk`; workflow-engine hard gate). No upgrade or downgrade:
the evidence found no new Deep signal and the lane already sets the maximum.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse existing: extend `check_ste_baseline.py` and `review_package.py`, copy the Phase 1 propagation-test pattern, and build one small new module for A1. |
| **Why this is the lightest credible path** | Every guardrail has an existing script, test file and propagation-test pattern to extend. Only the per-hunk qualifier diff is new code. |
| **Confidence** | 85% |
| **Next step** | `writing-plans`. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Harness / skill framework (Markdown prompts, bash hooks, Python helper scripts) |
| Primary language + runtime | Python 3 (stdlib only) and bash |
| Frameworks / platforms | Claude Code skills/agents/hooks; pytest for `scripts/test_*.py` and `skills/*/scripts/test_*.py` |
| Relevant packages | none external. `skills/asd-ste100/scripts/ste-lint.py` (vendored) |
| Detectable versions | none load-bearing |
| Important constraints | 600-word ceiling (`scripts/audit_skill_prompts.py`); `synonym-rotation` excluded; `weakening-validation` gate; `scripts/` deploys to consumers only through the `CONSUMER_SCRIPTS` allow-list |

---

## Feature Understanding and Assumptions

- **Requested feature:** Phase 3 of the STE adoption: four guardrails (A1–A4), then the rewrite of 43 prose files in nine waves (`design.md`).
- **What success appears to mean:** the design Success criteria: the A1/A4 tests pass, the reviewer instruction is in place, the tiny-lane line is in place, no file's hard count rises against `48e7e05`, the in-scope sum is below 267, and every file has a meaning verdict.
- **Assumptions from the request:** the Phase 2 pilot result holds for the other files (design A1, accepted risk).
- **Assumptions still needing confirmation:** where the A1 module lives (Recommendation below).

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/deploy-harness.sh` L39–51: `scripts/` is **not** synced to consumers; only `CONSUMER_SCRIPTS` (7 files) travel. A new `scripts/check_scope_qualifiers.py` would not exist in a consumer. |
| `Local` | `skills/subagent-driven-development/scripts/review_package.py` deploys with its skill, and it reaches `ste-lint.py` through `Path(__file__).parents[2]`. A sibling module in the same directory deploys with no allow-list change. |
| `Local` | `scripts/check_ste_baseline.py` `main()`: `Skip` → prints `skipped` and returns 0 in every mode; `--strict` and `--update` are a mutually exclusive group. `--against` must join neither group or be allowed with `--strict`. |
| `Local` | `scripts/test_check_ste_baseline.py` L94–121: four `*_skips_and_exits_0` tests assert `--strict` exit 0 on a skip (A4 reverses these on purpose). |
| `Local` | `skills/subagent-driven-development/scripts/test_review_package.py`: 9 tests on `## STE lint`, using a temp git repo and monkeypatched linter. The A1 section tests copy this harness. |
| `Local` | `tests/scripts/context-propagation-regression.test.sh` L154–206: per-consumer `grep -q` presence checks plus `ste_mutant` mutation cases. A2 adds one presence check and one mutation case here. |
| `Local` | `tests/scripts/research-depth-drift.test.sh`: registry `rules/research-depth.md`, copies `skills/xia2/SKILL.md` and `skills/xia2/references/research-brief-template.md`. It does **not** read `skills/feature-intake/SKILL.md`, so removing the feature-intake section breaks no drift test. B2 (`research-depth.md`) and B5 (`xia2/SKILL.md`) must keep its anchor keywords. |
| `Local` | `rules/research-depth.md` L3–6 holds all four rules the feature-intake section repeats (high-risk → Deep, normal → Standard, tiny → Quick only if every condition passes, up on evidence never down). |
| `Local` | 32 test files reference in-scope prose paths (grep of `tests/scripts/*.sh`, `tests/hooks/*.sh`, `scripts/test_*.py` on 2026-10-15). Examples: `inline-policy-drift.test.sh` (Rule 4 list in `auto-correct-scope.md`, B1), `scorer-threshold-contract.test.sh` (B6), `finishing-branch-contract.test.sh` (B8), `compound-contract.test.sh` (B9), `brainstorming-contract.test.sh` and `writing-plans-contract.test.sh` (B4). |
| `Local` | `agents/*.md` are the **source** for `scripts/render_agent_definitions.py` (L181, L326). No rendered copy is committed (`git ls-files` for `*.toml`/`rendered`: none found). Frontmatter `name`/`description` is a contract (`scripts/test_check_frontmatter_contract.py`). |
| `Local` | Word counts (measured 2026-10-15 `wc -w`): `session-retro` 599, `feature-intake` 599, `finishing-a-development-branch` 584 — at or near the 600 budget. |
| `Upstream` | tessl registry skill "preservation verifier" (`conorbronsdon/avoid-ai-writing`): a structural check first, then a separate semantic review for negation, conditions, causality and uncertainty. Same split as A1 (cue diff, advisory) + A2 (reviewer). |
| `Upstream` | arXiv 2307.13989 (negation-aware evaluation): similarity metrics score a sentence and its negation as near-equal. Supports keeping the semantic reviewer as the gate rather than a similarity score. |
| `Inference` | `not` and `no` are absent from the design's word list. They are too frequent in rule prose to diff per hunk without noise; the reviewer instruction covers them. Keep the list as designed. |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `scripts/check_ste_baseline.py` + `scripts/test_check_ste_baseline.py`; `skills/subagent-driven-development/scripts/review_package.py` + `test_review_package.py`; `skills/subagent-driven-development/task-reviewer-prompt.md`; `tests/scripts/context-propagation-regression.test.sh`; `scripts/audit_skill_prompts.py`; `scripts/run-tests.sh` L84 (runs `check_ste_baseline.py` warn-only); `scripts/deploy-harness.sh`.
- **Existing abstractions or extension points:** `ste_section(base, head)` returns a section string, and `main()` appends it — a `qualifier_section(base, head)` slots in the same way. `compare(counts, baseline)` takes any baseline dict — `--against` only needs a second loader (`git show <ref>:scripts/ste-baseline.json`) that feeds the same function.
- **Conventions worth preserving:** `Verifies:` / `Does not verify:` docstring lines; error → one-line `unavailable (<reason>)` with exit 0 in review tooling; whitespace-collapsed error text; `0o600` package file.
- **What can likely be reused:** the temp-repo test fixture in `test_review_package.py`; `ste_mutant` in the propagation test.
- **What appears missing locally:** a per-hunk diff parser. `review_package.py` reads the diff only as text.

---

## Upstream Findings

- **Repositories inspected:** tessl registry `conorbronsdon/avoid-ai-writing` (preservation verifier); arXiv 2307.13989.
- **Pattern or capability already present upstream:** cue-word check plus semantic review. No diff-based qualifier tool was found.
- **Files, modules, or areas worth modeling:** the two-step split only. No code to adapt.
- **How closely the upstream pattern matches this repo:** the split matches; the implementation is a prompt there and a diff script here.
- **Any upstream gaps or uncertainties:** no measured recall for cue-word lists on instruction prose.

---

## Docs Findings

No external surface: no dependency, external system or version-specific API. Not applicable.

---

## Recommendation

- **Primary recommendation:** reuse existing. A2, A3 and A4 extend existing files and tests. A1 is new code, but it belongs **beside `review_package.py`** as `skills/subagent-driven-development/scripts/scope_qualifiers.py`, not at `scripts/check_scope_qualifiers.py` as the design names it.
- **Why this is the lightest credible path:** `review_package.py` runs in consumer repos. A module under `scripts/` does not deploy there (allow-list, `deploy-harness.sh` L39–51), so the consumer's review package would always print `unavailable`. A sibling module deploys with the skill and needs no allow-list row and no path rewrite. This is a change to the approved design path (D-level detail in A1), so it needs a user decision before `writing-plans` (Rule 4: reversing a settled design detail).
- **Why the next-best alternative lost:** keep `scripts/check_scope_qualifiers.py` and add it to `CONSUMER_SCRIPTS` plus a path rewrite in `deploy-harness.sh`. It works, but it touches `deploy-harness.sh` (a file the Phase 1 Rule 4 stop already flagged) for no gain.
- **User decision (2026-10-15): keep `scripts/check_scope_qualifiers.py`, harness-only.** No deploy change. In a consumer, `review_package.py` finds no module (it looks for `Path(__file__).parents[3] / "scripts" / "check_scope_qualifiers.py"`, which is `.claude/scripts/` there) and prints `scope-qualifiers: unavailable`. The reviewer meaning check (A2) still runs. The design is unchanged, so no `DC` entry.
- **What would change this recommendation:** if the module had to run outside SDD (for example from `run-tests.sh`), `scripts/` would be the right home.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - Literal-grep contract tests (32 files) break on a rewrite. Mitigation: each wave runs `bash scripts/run-tests.sh`; the fix is in prose, never the test.
  - Drift-lint anchor keywords (`research-depth-drift`, `inline-policy-drift`, `scorer-threshold-contract`) silently lose a keyword match → test fails, which is the intended catch.
  - Frontmatter `description:` lines steer skill and agent routing. A rewrite there changes triggering, which the pilot did not measure. Recommend: leave frontmatter unchanged in every wave.
  - At-ceiling files (`session-retro`, `feature-intake`, `finishing`) cannot absorb sentence splits. Keep hard sentences long and list them.
  - `--against` reads `git show 48e7e05:...`; a rebase of the stacked branch changes "start of this PR" (design re-pin rule).
  - `check_ste_baseline.py` `--strict`/`--update` mutual exclusion: `--against` must work with `--strict`.
- **Evidence gaps:** recall of the eight-word list on real rewrites is unmeasured (design A3; the replay test is a single case).
- **Version uncertainties:** none.
- **Follow-up questions for the user:** none (A1 location decided 2026-10-15).

---

## Source Pack

- **Local files read:** `scripts/check_ste_baseline.py`, `scripts/test_check_ste_baseline.py`, `skills/subagent-driven-development/scripts/review_package.py`, `skills/subagent-driven-development/scripts/test_review_package.py`, `skills/subagent-driven-development/task-reviewer-prompt.md`, `scripts/deploy-harness.sh`, `scripts/run-tests.sh`, `tests/scripts/context-propagation-regression.test.sh`, `tests/scripts/research-depth-drift.test.sh`, `scripts/render_agent_definitions.py`, `scripts/audit_skill_prompts.py`, `rules/research-depth.md`, `skills/feature-intake/SKILL.md`, `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`, `docs/solutions/harness/wave-boundary-verify-evidence.md`, `specs/ste100-harness-prose/design.md`, `specs/ste100-harness-prose/DECISION.md`, `scripts/ste-baseline.json`
- **Upstream repositories or pages checked:** https://tessl.io/registry/skills/github/conorbronsdon/avoid-ai-writing/preservation-verifier, https://arxiv.org/pdf/2307.13989
- **Official docs domains or pages checked:** - none (local-only; no external surface)

---

## Evidence Boundary

> Confirmed from artifacts: deploy allow-list excludes new `scripts/` files; review_package deploys with its skill; `--strict` exits 0 on skip and four tests pin it; research-depth drift test does not read feature-intake; research-depth.md holds all four mapping rules; agents/*.md are render sources with no committed rendered copy; 32 test files reference in-scope prose.
> Inferred from patterns: `not`/`no` would be noisy in the word list; frontmatter rewrites carry routing risk.
> Not checked: the exact keyword anchors each contract test needs per file (the implementer finds them by running the suite each wave); recall of the qualifier word list.
