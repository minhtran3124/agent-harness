# strict-gate-scripts-warn — Summary

Lane: high-risk
Confidence: high
Reason: changes `scripts/ci-strict-gate.sh`, the CI gate that decides which PRs must carry machine-verified proof. Widening its trigger set is a governance change affecting every future PR.
Flags: strengthening-validation (new gated path class)
Affects: ci-strict-gate trigger surface — scripts/ci-strict-gate.sh → consumer .github/workflows/harness-ci.yml
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- Request made in another language; per the user's standing English-only instruction for
     specs, the operative text is the English translation. Translation only, no scope change. -->

"Survey the cost of extending HARD_GATE_RE to `scripts/` and `rules/`." Then, after the
survey was presented: "Open the PR — `scripts/` only, warn-first like #190."

## What changed

`scripts/ci-strict-gate.sh` gains a second, non-blocking tier. `scripts/` (excluding
`scripts/test_*`) now triggers the same proof check as the hard-gate paths, but a failure
**reports and exits 0** instead of blocking. `REQUIRE_SCRIPTS_PROOF=1` promotes it to
blocking.

The existing hard-gate tier (`hooks/`, `settings.json`, `templates/`, `render_plan.py`) is
untouched and still blocks — covered by a regression test that the tiers do not leak.

### Rationale

`scripts/verify_summary.py` decides what every other gate accepts as evidence, yet was
itself never re-run by any gate. That is the largest hole in the truth tier: the arbiter
was unarbitrated.

Warn-first because the survey (below) showed 9 of the last 80 PRs would block on day one.
Blocking immediately would have converted a real improvement into a wall.

### Cost survey (the evidence for this shape)

Measured over the last 300 commits / 80 merged PRs on `simplify`:

| Path | Commits / 300 |
| --- | --- |
| `hooks/` (already gated) | 22 |
| `templates/` (already gated) | 3 |
| `settings.json` (already gated) | 1 |
| `scripts/` (added here) | 63 |
| `rules/` (rejected — already covered by the `workflow-engine` signal) | 12 |

Trigger rate goes 28/300 → 83/300 commits, roughly 3x. Per PR — the unit the gate actually
runs on — 15 more PRs are caught, of which **9 would have blocked** and 6 already carried
sufficient evidence.

### Alternatives considered

- **Include `rules/` as well** — rejected for two reasons, the second found only by reading
  the code rather than the survey:
  1. All 8 files are prose. No command's re-run proves a sentence correct, so the ceremony
     would produce no evidence. Only 4 PRs were affected anyway.
  2. **`rules/*.md` is already gated**, by a mechanism better suited to prose: it matches the
     `workflow-engine` signal in `hooks/risk-corroboration.sh` (lane corroboration) and in
     `scripts/check_review_receipt.py` (`--require-audit-if` forces a context-propagation
     audit). Adding it to `ci-strict-gate.sh` would be a third overlapping gate demanding
     the one kind of evidence prose cannot supply.
- **Block immediately (no warn tier)** — rejected: 9 of the last 80 PRs would have blocked
  with no migration path.
- **Gate all of `scripts/` including tests** — rejected: 21 of the 55 files under `scripts/`
  are `test_*.py`, and a test-only edit carries no production risk. Mirrors the existing
  `^hooks/` decision to exclude `tests/hooks/`.

### Deviations

- none

### Verify

<!-- Rows are pipe-free and individually <60s; ci-strict-gate re-runs each under a 60s cap. -->

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| gate contract tests | `bash tests/scripts/ci-strict-gate.test.sh` | 0 | 17 passed, +8 new | |
| gate script parses | `bash -n scripts/ci-strict-gate.sh` | 0 | | |
| warn tier reachable | `grep -q "WARN-ONLY" scripts/ci-strict-gate.sh` | 0 | | |
| test exclusion present | `grep -q "scripts/test_" scripts/ci-strict-gate.sh` | 0 | | |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | | |

Full suite run by hand: `scripts/run-tests.sh` → ALL GREEN (305 pytest + every bash suite,
including `ci-strict-gate.test.sh` 17 passed). Kept out of the table on purpose (60s cap).

**Mutation-tested**, per `docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md`
— green tests are not evidence until a broken implementation turns them red:

| Mutation | Result |
| --- | --- |
| Remove the `scripts/test_` exclusion | 2 tests FAIL |
| Make warn mode exit 1 (warn → block) | 3 tests FAIL |

### Not auto-verified

- **That the newly-gated PRs will actually add Verify rows.** Reached nothing. Warn-first
  only reports; nothing measures whether the 9 would-block PRs change behaviour. If the
  advisory is ignored, `REQUIRE_SCRIPTS_PROOF=1` never becomes flippable.
- **That a Verify row COVERS the scripts/ change it accompanies.** Reached traceability.
  The gate accepts any one passing high-risk row — a PR could rewrite `verify_summary.py`
  and satisfy it with an unrelated `lint` row. Coverage is a judgment call; documented in
  the script's `Does not verify:` header rather than designed around.
- **The 60s per-row cap under load.** Reached traceability. Measured locally at 24.1s for a
  7-row table, but a cold CI runner was not measured. Tripling the number of PRs that re-run
  rows raises TIMEOUT exposure, and no test covers that.

### Rollback

- Revert: `git revert <sha>` — restores the single-tier gate and the original test file.
- No state, no migration; the gate is stateless and reads only the diff.
- Partial: set `WARN_GATE_RE` to a never-matching pattern to disable the tier while keeping
  the code, or leave it warn-only indefinitely (the default).

### Harness-Delta

- **fix-direct** — `tests/lib.sh` has no `assert_contains`; calling a non-existent assertion
  printed `command not found` but the suite still reported all tests passed. A typo'd
  assertion name therefore produces a vacuously green test. Caught here by hand. Worth a
  guard (fail on unknown assertion), filed rather than fixed to keep this PR scoped.
