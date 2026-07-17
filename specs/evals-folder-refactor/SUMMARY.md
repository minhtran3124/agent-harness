# evals-folder-refactor — Summary

Lane: normal
Confidence: high
Reason: Directory rename (benchmarks/ → evals/) + live-reference updates; no auth/authz/data-loss/public-contract/high-blast file touched (run-tests.sh PYTESTS deliberately NOT changed).
Flags: existing-behavior
Affects: none
Input-type: harness improvement
Route: direct refactor (mechanical, reversible) — SUMMARY record; no PLAN (single-step rename)
Escalate: no

### Intent

> "toi muon refactor folder script test, tach rieng ra giua test script la test skill + workflow."
> Chosen structure (via clarification): rename `benchmarks/` → `evals/`, split into
> `evals/skills/` (single-skill evals) and `evals/workflow/` (workflow-stage evals). Keep the
> deterministic code tests untouched (no python moves, no `run-tests.sh` `PYTESTS` edit).

## What changed

Renamed `benchmarks/` → `evals/` and split it by eval target: `evals/skills/review-chain/`
(the `/correctness-review` + `/intent-review` eval) and `evals/workflow/intake-classifier/`
(the `/feature-intake` eval). Added `evals/README.md` documenting the split and its boundary
with the deterministic `tests/` + `scripts/test_*.py` suites. Updated only **live** references
to the new paths (scorer `DEFAULT_FIXTURES`, the intake README, the three
`skills/correctness-review/*` docs, this session's intake spec). Deterministic test layout
(`tests/`, `scripts/test_*.py`, `run-tests.sh`) is unchanged.

### Rationale

The skill/workflow evals were already isolated in `benchmarks/`; the ask was a clearer home and
name. Option 2 (rename + skills/workflow split) delivers that with **zero risk to CI**: it does
not touch `run-tests.sh` `PYTESTS` (a high-blast hard gate) and does not move the co-located
`scripts/test_*.py` files (which `import` their sibling module and would break out of `scripts/`).
Historical docs (research/reviews/old specs) and past run-records keep their `benchmarks/` prose —
rewriting point-in-time records would be revisionism (surgical-changes rule); the doc-truth lint
scans only CLAUDE.md/README.md/HARNESS.md/skills/README.md, none of which referenced `benchmarks/`.

### Alternatives considered

- Consolidate code tests under `tests/` (move `scripts/test_*.py` + edit `run-tests.sh`). Rejected: edits a high-blast hard-gate file and breaks sibling-module imports for marginal gain.
- Full reorg (both). Rejected: same hard-gate + import costs; the eval-side rename alone satisfies the request.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| move complete, benchmarks/ gone | `test -d evals/skills/review-chain && test -d evals/workflow/intake-classifier && ! test -d benchmarks` | 0 | dirs relocated |
| eval works at new path, gates respected | `python3 scripts/score_intake_eval.py --run evals/workflow/intake-classifier/results/baseline --strict` | 0 | scorecard emits; hard-gate 3/3 |
| scorer unit tests | `python3 -m pytest scripts/test_score_intake_eval.py -q` | 0 | 13 passed |
| doc-truth lint (no scanned doc broke) | `bash scripts/lint-doc-truth.sh` | 0 | referenced paths exist |

### Rollback

- `git revert <sha>` (pure rename + string updates; `git mv` is reversible)

### Harness-Delta

- none
