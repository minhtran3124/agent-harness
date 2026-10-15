# ste100-harness-prose — Research Brief

Written 2026-10-14. Pins: repo a5d4292 + uncommitted; asd-ste100 0.4.0 at upstream 3944283c18; Claude Code 2.1.299

Depth: **Deep** (intake lane high-risk). No upgrade or change after evidence. External surface:
yes. The change vendors third-party code, and the pilot runner relies on version-specific Claude
Code CLI flags.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | adapt upstream (vendor asd-ste100 with three recorded deltas) + reuse existing (`review_package.py`, `rerun.py` runner shape) |
| **Why this is the lightest credible path** | The skill and linter already exist and match upstream byte for byte. Three harness checks need small deltas. The controller's review packet already has one builder script to extend. |
| **Confidence** | 85% |
| **Next step** | `writing-plans` for Phases 1–2, using the deltas and wiring points below |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Claude Code harness (skills, rules, hooks, scripts); no application stack |
| Primary language + runtime | Markdown prose; Python 3.12 (stdlib) and Bash for scripts/tests |
| Frameworks / platforms | Claude Code 2.1.299; Codex advisory adapter |
| Relevant packages | asd-ste100 0.4.0 (MIT), stdlib-only `ste-lint.py` |
| Detectable versions | `skills-lock.json` hash 911447778fee; upstream HEAD 3944283c18 (2026-10-14) |
| Important constraints | `CLAUDE.md` gate verifiability; `harness-manifest.json` skill inventory; `scripts/deploy-harness.sh` derived-tree rules; `specs/ste-terminology-evidence/DECISION.md` |

## Feature Understanding and Assumptions

- **Requested feature:** design.md D1–D7. This plan covers Phase 1 (vendor + wiring + linter
  ratchet) and Phase 2 (pilot) only.
- **What success appears to mean:** design.md Success criteria.
- **Assumptions from the request:** the vendored copy may carry small harness deltas if each one
  is recorded in `UPSTREAM.md`.
- **Assumptions still needing confirmation:** none that change the recommendation.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | A probe worktree (HEAD a5d4292 + `skills/asd-ste100/` + manifest entry, 2026-10-14) ran five skill-walking checks. `check-allowed-tools.sh` fails: SKILL.md has no `allowed-tools`. `check_runtime_neutral_sources.py` fails: 2 `deployed-skill-path` findings in `README.md` lines 65 and 68 (`~/.claude/skills/` install text). `lint-doc-truth.sh` fails: 3 derived-tree findings, `scripts/ste-lint.py` at SKILL.md:91, SKILL.md:139, README.md:38. `check_manifest.py` passes once `asd-ste100` is in `harness-manifest.json` `skills`. `check-plugin-validate.sh` passes. |
| `Local` | `scripts/check_manifest.py:93-99` requires every `skills/*/SKILL.md` to appear in `harness-manifest.json` `skills`. |
| `Local` | `skills/subagent-driven-development/scripts/review_package.py` builds the controller's `BASE..HEAD` review package (commits, stat, diff). SKILL.md:57-60 uses it before the task review. This is the natural place to append lint counts. |
| `Local` | `scripts/deploy-harness.sh:83,182` syncs all of `skills/`, so `skills/asd-ste100/scripts/ste-lint.py` reaches consumers (confirms design A2 at provenance tier). `CONSUMER_SCRIPTS` (lines 45-53) is the allow-list for root `scripts/`; `check_ste_baseline.py` stays harness-only and is not added. |
| `Local` | `tests/scripts/context-propagation-regression.test.sh` checks the live implementer and reviewer sources and delegates to `scripts/render_skill_prompt.py --check-all`. New wiring assertions follow its `implementer_read_ok` pattern. |
| `Local` | `scripts/run-tests.sh` runs `lint-doc-truth.sh` (line 36), `check-allowed-tools.sh` (48), and `check_manifest.py` (52). It also collects every unit test under `scripts/`, `runtime/`, and `skills/` (line 179). |
| `Local` | `skills/compound/SKILL.md` "Write canonical records" (line 35) is where records are written. That is the wiring point for D4. |
| `Local` | `specs/ste-terminology-evidence/experiment/rerun.py:204-260` runs trials as `claude -p --model M --safe-mode --dangerously-skip-permissions --tools Read,Write,Edit,Bash --output-format json --no-session-persistence` in a fresh directory and scores files on disk. |
| `Upstream` | `github.com/danyuchn/asd-ste100-skill`: default branch `master`, MIT, HEAD 3944283c18 (2026-10-14). Local `SKILL.md` and `scripts/ste-lint.py` sha256 match upstream at 3944283c18 (measured 2026-10-14 sha256sum). The repo is active: 3 commits on 2026-10-14. |
| `Docs` | `claude --help` (2.1.299, read 2026-10-14) lists `-p`, `--model`, `--safe-mode`, `--tools`, `--output-format`, `--no-session-persistence`, `--max-budget-usd`. Every flag `rerun.py` uses still exists. |
| `Inference` | `--safe-mode` starts "with all customizations" disabled, so a trial cannot load project skills. The workflow arm must put the old or new `feature-intake` text in the trial sandbox as a file and tell the agent to follow it (classification Steps 2–4 only). That is design A1's fallback, so it becomes the primary method. |

## Local Findings

- **Relevant files:** `skills/subagent-driven-development/{SKILL.md,implementer-prompt.md,task-reviewer-prompt.md,scripts/review_package.py}`, `skills/compound/SKILL.md`, `harness-manifest.json`, `skills/README.md`, `scripts/{run-tests.sh,check-allowed-tools.sh,check_manifest.py,check_runtime_neutral_sources.py,lint-doc-truth.sh,deploy-harness.sh}`, `tests/scripts/context-propagation-regression.test.sh`, `specs/ste-terminology-evidence/experiment/rerun.py`.
- **Extension points:**
  - `review_package.py` can append a `## STE lint` section: hard counts at BASE and HEAD for each changed `.md` under `skills/`, `rules/`, `agents/`. It can find the linter with `Path(__file__).parents[2] / "asd-ste100/scripts/ste-lint.py"`, which resolves under both `skills/` and a consumer's `.claude/skills/`. It must print `ste-lint: unavailable (<reason>)` instead of crashing, so that design's "counts absent → not a pass" can fire.
- **Conventions worth preserving:**
  - A `Verifies:` / `Does not verify:` header on each new check script.
  - The mutation-case pattern in the propagation tests.
  - Byte-identical vendoring except for deltas listed in `UPSTREAM.md`.
- **Reuse:** the `rerun.py` structure (fixture builder, `run_trial`, `observe`, `fisher`, `--score-only`) for the pilot runner. The `ste-lint.py --json` fields `hard_count` and `violations[].rule`.
- **Missing locally:** a test for `review_package.py` (none found under `skills/subagent-driven-development/scripts/`, searched `ls`); `test_task_brief.py` is the pattern to copy.

## Upstream Findings

- **Repositories inspected:** `danyuchn/asd-ste100-skill` (GitHub API commits and repo metadata; raw files at 3944283c18).
- **Pattern present upstream:** the full skill, the linter with `--json`, `--baseline`, `--disable`, `--selftest`, and the examples.
- **Match to this repo:** content matches. Packaging does not: no `allowed-tools`, and a README with `~/.claude/skills/` install paths.
- **Gaps:** upstream changes often. `UPSTREAM.md` must pin a commit, and re-vendoring is manual (design D3).

## Docs Findings

- **Official sources checked:** `claude --help` from the installed Claude Code 2.1.299.
- **Version-matched status:** matched to the installed CLI.
- **Built-in support:** headless `-p` with `--output-format json` and `--max-budget-usd` (a cost cap the old runner did not use. Recommend adding it).
- **Caveats:** `--safe-mode` disables project customizations (see the Inference row).

## Recommendation

- **Primary:** adapt upstream. Vendor `SKILL.md`, `LICENSE`, `references/`, `examples/`, and
  `scripts/ste-lint.py` from 3944283c18 into `skills/asd-ste100/`, with three recorded deltas:
  1. Add `allowed-tools: Read, Bash(python3 *)` to the SKILL.md frontmatter.
  2. Do not vendor `README.md`. It is human install docs, and it trips the runtime-neutral scan.
     The `UPSTREAM.md` file links to it instead.
  3. Change the SKILL.md references `scripts/ste-lint.py` to a form `lint-doc-truth.sh` accepts in
     the derived tree. Confirm the exact form during the task by re-running `lint-doc-truth.sh`.
- Add `asd-ste100` to `harness-manifest.json` `skills`.
- Put the lint counts into `review_package.py`, not into prose steps for the controller. A
  deterministic script is testable and always runs where the review package is built. This
  implements design D4 ("the controller runs the linter") without a new prose step.
- Pilot workflow arm: put the skill text in the trial sandbox (`--safe-mode`), Steps 2–4 only,
  with `--max-budget-usd` per trial.
- **Why the next-best alternative lost:** a byte-identical vendor fails three harness checks
  (Evidence Ledger row 1). Using the `npx skills` install does not deploy to consumers (design D3).
- **What would change this:** if upstream adds `allowed-tools` and drops the install paths, the
  deltas shrink to the path fix.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - A delta-3 form that passes `lint-doc-truth.sh` may not resolve for an agent in a consumer repo.
    Check it against the deploy smoke test.
  - Changing `review_package.py` changes what every task reviewer sees. Keep the section short and
    only add it when prose files changed.
  - The implementer and reviewer prompt edits must still pass `render_skill_prompt.py --check-all`.
- **Evidence gaps:** not checked whether `examples/linter-edge-cases.md` (an intentionally invalid
  fixture) trips `lint-doc-truth.sh` or the Codex packaging probe. Recommend not vendoring it,
  or running the full suite on the vendoring task.
- **Version uncertainties:** upstream moves fast. Pin to 3944283c18.
- **Follow-up questions for the user:** none.

## Source Pack

- **Local files read:** `.agents/skills/asd-ste100/{SKILL.md,README.md,scripts/ste-lint.py}`, `skills-lock.json`, `harness-manifest.json`, `scripts/{deploy-harness.sh,check-allowed-tools.sh,check_manifest.py,run-tests.sh}`, `skills/subagent-driven-development/{SKILL.md,scripts/review_package.py}`, `skills/compound/SKILL.md`, `tests/scripts/context-propagation-regression.test.sh`, `specs/ste-terminology-evidence/{DECISION.md,experiment/rerun.py,experiment/RERUN.md}`, `specs/codex-support/neutralization-inventory.json`, `agents/task-reviewer.md`
- **Upstream repositories or pages checked:** `https://api.github.com/repos/danyuchn/asd-ste100-skill`, `https://api.github.com/repos/danyuchn/asd-ste100-skill/commits`, `https://raw.githubusercontent.com/danyuchn/asd-ste100-skill/3944283c18/SKILL.md`, `.../scripts/ste-lint.py`
- **Official docs domains or pages checked:** `claude --help` (Claude Code 2.1.299, local)

## Evidence Boundary

> Confirmed from artifacts:
> - The three failing checks and the two passing checks (probe worktree run).
> - The local copy is byte-identical to upstream 3944283c18 for SKILL.md and ste-lint.py.
> - The CLI flags exist.
> - `review_package.py` is the controller's packet builder.
> - `deploy-harness.sh` syncs `skills/`.
>
> Inferred from patterns:
> - `--safe-mode` prevents skill loading in trials.
> - `Path(__file__).parents[2]` resolves in consumer repos.
>
> Not checked:
> - The exact delta-3 path form.
> - Whether `examples/linter-edge-cases.md` affects any check.
> - A real headless pilot trial (design A1, proven by the runner dry run).
