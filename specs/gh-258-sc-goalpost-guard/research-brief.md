# gh-258-sc-goalpost-guard — Research Brief

Depth: **Deep**, mapped from the intake lane `high-risk` per `rules/research-depth.md`. The evidence
below found no reason to change it. Design: `specs/gh-258-sc-goalpost-guard/design.md`, approved
2026-10-09, decisions D1–D7.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Build a small new piece inside `scripts/verify_summary.py` and reuse its parsers; reuse the item-3 section of `ci-strict-gate.sh` as the template for the new CI section. |
| **Why this is the lightest credible path** | Both table parsers (`parse_sc_table`, `_parse_verify_rows`) and the exit-code mapping already exist. The only new logic is the history walk and the comparison. |
| **Confidence** | 85% |
| **Next step** | Run `writing-plans` for `specs/gh-258-sc-goalpost-guard/`. |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Harness meta-repo: Markdown skills, bash CI scripts, stdlib Python helpers. |
| Primary language + runtime | Python 3 stdlib (CI uses `setup-python` `3.x`), bash, git. |
| Frameworks / platforms | None. Tests use pytest and `tests/lib.sh`. |
| Relevant packages | pytest, for tests only. |
| Detectable versions | No pins. `verify_summary.py` uses `from __future__ import annotations`. |
| Important constraints | `verify_summary.py` is the evidence authority for the commit-gate lane check, `ci-strict-gate.sh` and the finish flow, so existing modes must not change. It ships to consumers. The finish skill has a 600-word ceiling (budget; 528 measured 2026-10-09 with `wc -w`). |

## Feature Understanding and Assumptions

- **Requested feature:** #258 item 5. Warn when a failed SC's `Check` or `Expected` changes (or the SC is removed) in the same branch, unless `### Deviations` names it.
- **What success appears to mean:** design SC-1 to SC-5.
- **Assumptions from the request:** settled in D1–D7.
- **Assumptions still needing confirmation:** none that would change the recommendation.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/verify_summary.py`. `main()` without `--check` rewrites `Exit` cells with the real exit codes (`_rewrite_table`), which is the failure record D1 relies on. `--check` does not write. `run_checks` records `124` on a timeout. `main(argv, specs_root=None)` is the existing test seam. `_REPO_ROOT` is derived from the script's own location (line 35), so the new mode must not use it (D7). |
| `Local` | `parse_sc_table(plan_text)` returns `{SC-n: "<exit>" or "ERROR: …"}` and reads `Expected` from `cells[3]`. `Check` is `cells[2]`, which the function does not return, so a new helper is needed. `_parse_verify_rows` returns `criterion` from the fifth cell. |
| `Local` | `verify_summary.py` does not call git anywhere today; the new mode adds its first git calls. The pattern to copy is `scripts/resolve_finish_context.py` `git(root, *args)`: `subprocess.check_output(["git", *args], cwd=root, text=True, stderr=DEVNULL)`. |
| `Local` | `scripts/ci-strict-gate.sh` item-3 section: placed after `DIFF` and before `exit 0  # no gated paths touched`, using `MERGE_BASE=$(git merge-base "$BASE" HEAD …)`. Its exit-code mapping (rc 1 counts only under REQUIRE; any other non-zero is an error that blocks only under REQUIRE) and its per-cause BLOCKED lines are the template for the new section (design D5). |
| `Local` | `tests/scripts/ci-strict-gate.test.sh`. `mkrepo` copies `verify_summary.py` and `check_open_questions.py` into a fixture repo. `commit_run <repo> [VAR=val…]` runs the gate against the pre-commit SHA. No existing case touching `specs/` asserts that the output is empty, so a new summary line from the section breaks none of them (grep for `silently`). |
| `Local` | `scripts/test_verify_summary.py` tests through `vs.main([...], specs_root=…)` with `write_summary(tmp_path, …)`. It has no git fixtures. `scripts/test_check_review_receipt.py` has a `_git(repo, *args)` helper that builds real temp repos, which is the model for the history tests. |
| `Local` | `specs/*/SUMMARY.md`: 53 of 120 use a `Criterion` column (`grep -l "\| Criterion \|"`, 2026-10-09), so the failure-record signal exists across the repo. |
| `Local` | `.github/workflows/harness-ci.yml` `strict-gate` job uses `fetch-depth: 0` and fetches the base ref, so the history walk has full history (design A3). |
| `Inference` | A branch that edits an SC whose row never failed produces no finding, so false positives need both a committed failing row and a later SC edit without a Deviations entry. Historical precision was not measured (see Evidence gaps). |

## Local Findings

- **Relevant files:** `scripts/verify_summary.py`, `scripts/test_verify_summary.py`, `scripts/ci-strict-gate.sh`, `tests/scripts/ci-strict-gate.test.sh`, `skills/finishing-a-development-branch/SKILL.md`, `tests/scripts/finishing-branch-contract.test.sh`, `scripts/resolve_finish_context.py` (the git helper pattern), `scripts/test_check_review_receipt.py` (the temp-repo pattern).
- **Extension points:** the argparse block in `verify_summary.main` (add `--sc-history` and `--base`); a new history function that takes `repo_root`; a new `ci-strict-gate.sh` section next to the item-3 one; finish step 3, which already carries the item-3 check.
- **Conventions worth preserving:**
  - existing modes stay byte-for-byte the same (`--check`, `--lane`, the rewrite mode);
  - stdlib only;
  - exit 2 for a usage error;
  - an env flag turns warn into block, as `REQUIRE_NOT_AUTO_VERIFIED` and `REQUIRE_QUESTIONS_CLOSED` do;
  - a warn line still says what is missing.
- **What can be reused:** both parsers, the item-3 CI section shape and its exit mapping, the temp-repo test helper pattern, `commit_run` with env arguments.
- **What is missing locally:** a git history walk, and a parser that returns `Check` per SC.

## Upstream Findings

- **Repositories inspected:** `tamnd/rupg`, `spec/02-the-goal.md` §2.10 and `spec/21-testing.md` §21.15, read in the #258 review on 2026-10-08. They contain "We do not change the target in the same change that reports the miss", plus a ratchet: a published number may go down only with a register entry that says why.
- **Pattern already present upstream:** a written rule, enforced by review rather than by a tool.
- **What to model:** the "acknowledged entry required" shape, which maps to D4 (a Deviations entry naming SC-n).
- **How closely it matches this repo:** the rule matches; the mechanism here is new.
- **Upstream gaps:** no tooling upstream to copy.

## Docs Findings

There is no external surface: no dependency, no external system, and no version-specific API. Only stdlib and git plumbing that this repo already uses.

## Recommendation

- **Primary recommendation:** add a `--sc-history` branch to `verify_summary.main`, backed by:
  - a pure function taking `(repo_root, slug, base)`;
  - a small `_git` helper copied from the `resolve_finish_context.py` pattern;
  - a new `parse_sc_rows` helper returning `{SC-n: (check, exit_token)}`.

  Mirror the item-3 CI section with its own `SC_*` flags and BLOCKED lines.
- **Why this is the lightest credible path:** every parser and the CI exit mapping already exist and are tested. The new code is the walk, the comparison and the wiring.
- **Why the next-best alternative lost:** a separate script, `check_sc_history.py`, would duplicate both parsers and add a new consumer-shipped file, and the issue's target names `verify_summary.py`. Importing `render_plan.py` to read the SC table would couple the evidence authority to a high-blast engine.
- **What would change this recommendation:** a decision to read the plan from the working tree instead of from git (it would lose the history), or a move of the gate into `hooks/`.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - *Changing the evidence authority.* `verify_summary.py` decides what every other gate accepts. The new mode must leave the existing modes untouched: SC-4 re-runs the existing pytest cases. The `--sc-history` flag must reject combination with `--check` and `--lane`.
  - *Repository root.* Using `_REPO_ROOT` would read the harness repo instead of a temp repo or a consumer root; D7 rules this out. Tests must run git in a temp repo, never against this worktree.
  - *History cost.* `git show` runs once per commit per file. Spec histories are short today (tens of commits), so this is a prediction, not a measurement.
  - *CI noise.* The new section prints a one-line summary for every slug whose PLAN or SUMMARY changed, including in fixtures; no existing test asserts silence for those.
  - *This PR's own tier.* It changes `scripts/` (warn tier) and a skill. The SUMMARY needs Verify rows that re-run clean, and pytest rows need pytest on `python3` (use the shared venv locally).
- **Evidence gaps:** how often real branches commit a failing SC row and then edit that SC was not measured; precision is unknown. A history scan over existing specs could measure it, but is out of scope.
- **Version uncertainties:** none material.
- **Follow-up questions for the user:** none that would change the recommendation.

## Source Pack

- **Local files read:** `scripts/verify_summary.py` (parsers, `run_checks`, `_rewrite_table`, `main`), `scripts/test_verify_summary.py` (structure), `scripts/resolve_finish_context.py` (`git` helper), `scripts/test_check_review_receipt.py` (`_git` helper), `scripts/ci-strict-gate.sh` (item-3 section), `tests/scripts/ci-strict-gate.test.sh` (`mkrepo`, `commit_run`, the "silently" cases), `skills/finishing-a-development-branch/SKILL.md`, `tests/scripts/finishing-branch-contract.test.sh`, `.github/workflows/harness-ci.yml`, `rules/plan-format.md` (SC schema, Criterion column).
- **Upstream repositories or pages checked:** https://github.com/tamnd/rupg/tree/main/spec (`02-the-goal.md` §2.10, `21-testing.md` §21.15).
- **Official docs domains or pages checked:** - none (local-only; no external surface)

## Evidence Boundary

> Confirmed from artifacts: how Exit cells are written and what each parser returns; that
> `verify_summary.py` has no git calls today; the item-3 CI section's structure and exit mapping;
> the shape of the existing tests; CI history depth; how many SUMMARYs use the Criterion column.
> Inferred from patterns: that the false-positive rate is low, because a finding needs a
> committed failing row and a later edit without a Deviations entry.
> Not checked: historical precision over real branches; a real GitHub Actions run of the new
> section.
