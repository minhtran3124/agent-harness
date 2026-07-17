---
problem_type: knowledge
module: scripts/run-tests.sh / scripts/lint-doc-truth.sh
tags: run-tests, pytests-explicit, ci-collection, doc-truth-lint, lint-scope, high-blast, rename-refactor, surgical-scope
severity: standard
applicable_when: Adding a python test to the harness, or renaming/moving a tracked directory — before assuming CI will pick up the test, or that a rename will break the doc-truth lint.
affects:
  - scripts/run-tests.sh
  - scripts/lint-doc-truth.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-17
---
## Applicable When

You added a `scripts/test_*.py` and expect CI to run it, or you are about to rename/move a tracked
directory and need to know which references the lint will actually flag.

## Pattern

Two harness gates have a **narrower scope than they look** — know the exact boundary before you act:

- **`run-tests.sh` runs an explicit `PYTESTS` list, not pytest auto-discovery.** A new
  `scripts/test_*.py` is **not** run by CI (or the local suite) until its path is added to the
  `PYTESTS=` variable in `run-tests.sh`. Symptom: you add 13 tests, the suite still reports the old
  count. And `run-tests.sh` is a **high-blast hard-gate file** — editing it to register the test
  forces a `high-risk` lane + human confirmation. So a scorer/tool test can be *written and passing*
  (via its SUMMARY Verify row / manual pytest) yet still be a deferred CI-wiring task.
- **`lint-doc-truth.sh` checks path references in only 4 core docs:** `CLAUDE.md`, `README.md`,
  `HARNESS.md`, `skills/README.md` (plus the CLAUDE.md hook-table ↔ settings.json cross-check). It
  does **not** scan `docs/**`, `specs/**` (skipped by design), `evals/**`, or skill prompt files.

## How to Use

- Wiring a python test into CI = a deliberate `high-risk` edit to `run-tests.sh` `PYTESTS`. Plan it
  as such; don't assume co-located `test_*.py` "just runs".
- Before a big rename, `grep -rl <oldpath>` the repo, then split refs into **live** (code, the 4
  linted docs, the moved dir's own contents, active skill docs) vs **historical** (research/reviews,
  old specs, past run-records). Update only live refs; leaving point-in-time paths in historical docs
  is correct (surgical-changes) and safe — the doc-truth lint scans none of them. This is how
  `benchmarks/` → `evals/` moved with zero lint breakage.

## Gotchas

- The co-located `scripts/test_*.py` files live in `scripts/` (not `tests/`) because they
  `import` their sibling module directly — moving them out breaks the import without a
  `conftest.py` path shim. That co-location is intentional, not drift.

## Related
- docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md
