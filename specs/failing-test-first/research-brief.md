# failing-test-first — Research Brief

Written 2026-10-15. Pins: repo c88ce16 + uncommitted; git 2.43.0

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | build from scratch (small), reusing the existing advisory and test patterns |
| **Why this is the lightest credible path** | No local helper runs a command at another commit; the check slots into `verify_summary.py`'s existing lane-warning path, and the tests copy the `REQUIRE_NOT_AUTO_VERIFIED` cases |
| **Confidence** | 85% |
| **Next step** | `writing-plans` for specs/failing-test-first, adding the helper's internal timeout (Risks, R1) as a plan task detail |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Prompt-and-script harness (skills, rules, hooks, scripts) |
| Primary language + runtime | Python 3 (scripts), Bash (hooks, test drivers) |
| Frameworks / platforms | pytest (via `scripts/run-tests.sh`), git 2.43.0 locally; CI on ubuntu + macOS |
| Relevant packages | none new; standard library only (`subprocess`, `tempfile`, `os`, `signal`) |
| Detectable versions | git 2.43.0 (`git --version`, 2026-10-15) |
| Important constraints | `CLAUDE.md`: run `bash scripts/run-tests.sh` before changing `scripts/`; `ci-strict-gate.sh` blocks `templates/` diffs without a high-risk SUMMARY whose Verify rows re-run clean, and warns on `scripts/`; Verify rows must be pipe-free and under 60 s |

---

## Feature Understanding and Assumptions

- **Requested feature:** E5 — bug-fix runs record a red row (test fails at the pre-fix commit) and
  a green row (passes at HEAD); `verify_summary.py` checks the pair, advisory by default.
- **What success appears to mean:** the five Success criteria in `design.md`.
- **Assumptions from the request:** design D1–D8 as approved on 2026-10-15.
- **Assumptions still needing confirmation:** none that change the recommendation. R1 below adds
  an implementation detail inside D7's failure handling.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `git worktree add --detach` + `git worktree remove --force` on this repo (1218 tracked files) took 0.098 s (measured 2026-10-15 local run), against the 60 s (budget) row limit |
| `Local` | `scripts/run-tests.sh:191` collects every `test_*.py` under `scripts/`, `runtime/` and `skills/` with `find`; a new `scripts/test_run_at_commit.py` runs without a list edit |
| `Local` | `scripts/deploy-harness.sh:419-420` passes `CONSUMER_SCRIPTS` to `rewrite_derived_paths`, so a `scripts/run_at_commit.py` reference in skills/rules is rewritten to `.claude/scripts/run_at_commit.py` in the consumer tree once the script is in the list |
| `Local` | `tests/scripts/consumer-subset.test.sh:32` loops over the deployed consumer scripts by name; the new script is one more name in that loop |
| `Local` | `scripts/test_verify_summary.py:594-638` holds the `REQUIRE_NOT_AUTO_VERIFIED` warn-first cases (monkeypatched env, `check_lane_warnings` assertions), the pattern for the new cases |
| `Local` | `hooks/commit-gate.sh:285-289` relays `!` lines from a passing `--lane` run; no hook change is needed |
| `Local` | `skills/subagent-driven-development/implementer-prompt.md:43` reads "Write tests. Follow TDD if the task says to." — the insertion point for the bug-fix instruction |
| `Local` | `skills/feature-intake/SKILL.md:26` and `templates/SUMMARY.template.md:19` hold the input-type lists |
| `Local` | `rules/auto-correct-scope.md:39-45` is the lane-evidence box; the source cites `scripts/verify_summary.py`, and deploy rewrites it |
| `Local` | `scripts/verify_summary.py:568-578`: `run_checks` uses `subprocess.run(shell=True, timeout=60)`; on timeout it kills the direct child and records 124 |
| `Local` | No script, runtime module or hook creates a git worktree: `grep -rln 'worktree add' scripts runtime skills hooks tests` matched only `skills/using-git-worktrees/SKILL.md` and two shell tests |
| `Docs` | `git worktree --help` (git 2.43.0, local): `add --detach` and `remove --force` exist; `prune` removes registry entries whose directory is gone |
| `Inference` | When `run_checks` times out, the killed process is the shell or the helper; the helper's `finally` does not run on SIGKILL, so a temporary worktree and its `.git/worktrees/` entry can be left behind |
| `Upstream` | none found (no upstream search for an equivalent "run a test at a past commit" gate helper beyond `git bisect run`, whose 125 "skip" code the design's 125 matches) |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `scripts/verify_summary.py`
  (`check_lane_warnings` :387, `_check_lane_targets` :523, `check_lane_evidence` :469,
  `run_checks` :552), `scripts/test_verify_summary.py`, `scripts/deploy-harness.sh`
  (`CONSUMER_SCRIPTS` :45, rewrite :419), `tests/scripts/consumer-subset.test.sh`,
  `templates/SUMMARY.template.md`, `skills/feature-intake/SKILL.md`,
  `skills/subagent-driven-development/implementer-prompt.md`, `rules/auto-correct-scope.md`.
- **Existing abstractions or extension points:** the warn-first advisory pair
  (`check_lane_warnings` for the warning, `check_lane_evidence` for the opt-in error); the
  `CONSUMER_SCRIPTS` list, which also drives path rewriting.
- **Conventions worth preserving:** opt-in env vars read as "set and not `0`/`false`"
  (`_not_auto_verified_is_blocking`, :362); `Verifies:` / `Does not verify:` docstrings on
  traceability-tier checks; advisory lines printed with a leading `!`.
- **What can likely be reused:** the env-parsing helper shape, the warning test pattern, the
  consumer-subset loop.
- **What appears missing locally:** a helper that runs a command at another commit; a `bug fix`
  input type.
- **Stale knowledge:** `docs/solutions/harness/test-and-doc-lint-gate-scope.md` (confirmed
  2026-07-17) says `run-tests.sh` runs a hand-written `PYTESTS` list; the current file collects
  tests with `find` (`scripts/run-tests.sh:188-191`). Do not follow the old advice to edit
  `PYTESTS`. A `compound` update can correct the record.

---

## Upstream Findings

- **Repositories inspected:** none (local-only feature).
- **Pattern or capability already present upstream:** `git bisect run` uses exit 125 to mean
  "this commit cannot be tested", the same meaning the design gives the helper's own failures.
- **Files, modules, or areas worth modeling:** none.
- **How closely the upstream pattern matches this repo:** the exit-code convention only.
- **Any upstream gaps or uncertainties:** none that affect the design.

---

## Docs Findings

No external surface: the change adds no dependency and integrates no external system. It relies
on `git worktree add --detach` / `remove --force`, present since git 2.17 and confirmed in the
local git 2.43.0 help; CI runners ship newer git.

---

## Recommendation

- **Primary recommendation:** build the helper and the check as designed, reusing the warn-first
  pattern and its tests.
- **Why this is the lightest credible path:** every integration point already exists (advisory
  path, relay, consumer list, path rewrite, test discovery), so the new code is one ~60-line
  script and one check function.
- **Why the next-best alternative lost:** approaches B and C in `design.md` leave the red evidence
  as an unchecked claim; the user approved A.
- **What would change this recommendation:** worktree creation too slow for the 60 s row limit in
  real consumer repos (A2); this repo measured 0.098 s.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - **R1 — leftover worktree on a `run_checks` timeout.** A SIGKILL from the 60 s timeout skips
    the helper's `finally`. Mitigation for the plan: the helper applies its own timeout to the
    test command, shorter than the row limit (50 s budget), kills the test, removes the worktree,
    and exits 124. The red-row rule already rejects 124, so a timed-out test never counts as red.
    The helper also runs `git worktree prune` before it starts, to clear entries whose directory
    is gone.
  - **R2 — concurrent runs.** Two helpers at once use separate `mkdtemp` directories, so they do
    not collide; git serializes registry writes.
  - **R3 — `--check` cwd.** `run_checks` runs rows from the repo root; the helper must resolve the
    repo with `git rev-parse --show-toplevel` from its cwd, not from its own file location, so it
    works from `.claude/scripts/` in a consumer (compare `docs/solutions/harness/hook-root-must-not-come-from-install-location.md`).
- **Evidence gaps:** worktree timing in a large consumer repo (A2, accepted risk).
- **Version uncertainties:** none material.
- **Follow-up questions for the user:** none.

---

## Source Pack

- **Local files read:** `scripts/verify_summary.py`, `scripts/test_verify_summary.py`,
  `scripts/deploy-harness.sh`, `scripts/run-tests.sh`, `tests/scripts/consumer-subset.test.sh`,
  `hooks/commit-gate.sh`, `templates/SUMMARY.template.md`, `skills/feature-intake/SKILL.md`,
  `skills/subagent-driven-development/implementer-prompt.md`, `rules/auto-correct-scope.md`,
  `docs/solutions/INDEX.md`, `docs/solutions/harness/test-and-doc-lint-gate-scope.md`,
  `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md`.
- **Upstream repositories or pages checked:** - none found
- **Official docs domains or pages checked:** - none (local-only; no external surface)

---

## Evidence Boundary

> Confirmed from artifacts: the integration points and line numbers in the Evidence Ledger; worktree timing on this repo; test discovery by `find`.
> Inferred from patterns: SIGKILL leaves a worktree behind (R1); concurrent runs do not collide (R2).
> Not checked: worktree timing on a large repo; behavior on macOS CI (runs in CI only).
