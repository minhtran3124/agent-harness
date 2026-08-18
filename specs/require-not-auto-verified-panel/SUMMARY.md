# require-not-auto-verified-panel — Summary

Lane: high-risk
Confidence: high
Reason: changes `scripts/verify_summary.py` — the single source of truth for the lane→evidence mapping (`rules/auto-correct-scope.md`), consumed by `hooks/commit-quality-gate.sh` and `scripts/ci-strict-gate.sh`. Adding a required section is a governance change, not a code change.
Flags: strengthening-validation (new required evidence for the high-risk lane)
Affects: artifact-schema-summary — scripts/verify_summary.py → consumers hooks/commit-quality-gate.sh, scripts/ci-strict-gate.sh
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

"draft that doc-truth rule as a follow-up" — the rule that would mechanise the
`### Not auto-verified` panel added to `templates/SUMMARY.template.md` in PR #189, which
that PR's own panel honestly records as unenforced.

## What changed

The lane gate now checks for a `### Not auto-verified` section on the **high-risk lane
only**, and by default **warns without blocking** — see `### Rollout` below.
`_has_real_not_auto_verified()` accepts either a written-out claim or an explicit `- none`,
and rejects an absent section, a comment-only body, or the unedited template bullet.

Deliberately **not** checked on `tiny` or `normal`: those lanes keep the existing evidence
set, which leaves the 28 non-high-risk specs in the back catalogue valid.

`hooks/commit-quality-gate.sh` now relays `--lane` output on the passing path too, so the
advisory is actually visible to the committer.

### Rationale

The lane→evidence mapping is documented as living in exactly one place
(`rules/auto-correct-scope.md`: "Edit the mapping there, not only in prose"), so the
requirement belongs in `check_lane_evidence()` and not in a new lint. Putting it there
means enforcement reaches the commit hook and CI for free, with no second code path to
keep in sync.

High-risk only, because that is the lane where over-claiming is most costly, and it
matches the tier the `### Rollback` requirement already sits at.

### Alternatives considered

- **A new check in `scripts/lint-doc-truth.sh`** — rejected: that lint is whole-repo and
  has no notion of "changed files", so it would fail on all 80 legacy SUMMARYs at once.
  It is the wrong home for a per-spec evidence rule.
- **Enforce on every lane** — rejected: 80 of 81 existing SUMMARYs lack the section, and
  tiny-lane work does not carry a Rollback either. The ceremony would not match the risk.
- **Backfill all 52 legacy high-risk specs with `- none`** — rejected: it manufactures
  boilerplate that asserts "everything is verified" about work nobody re-examined. That is
  precisely the over-claim the panel exists to prevent.

### Deviations

- Rule 3 — Extended the `_lane_summary` test helper with a `not_verified` parameter and
  updated 5 existing high-risk fixtures. Without it, 3 existing tests fail: they build
  high-risk SUMMARYs that now lack required evidence. The parameter is explicit rather
  than defaulted-on, so a fixture that omits the section still exercises the new rule.
  `scripts/test_verify_summary.py`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| verify_summary tests | `python3 -m pytest scripts/test_verify_summary.py -q` | 0 | 69 passed, +6 new | |
| this spec satisfies its own rule | `python3 scripts/verify_summary.py --lane require-not-auto-verified-panel` | 0 | dogfood | |
| legacy `normal` spec still passes | `python3 scripts/verify_summary.py --lane compound-ddr-improvements` | 0 | lower lanes unaffected | |
| legacy `high-risk` spec warns, not blocks | `python3 scripts/verify_summary.py --lane at-a-glance-rollup-wording` | 0 | warn-first default | |
| enforcement still works when opted in | `env REQUIRE_NOT_AUTO_VERIFIED=1 python3 scripts/verify_summary.py --lane at-a-glance-rollup-wording` | 1 | the flip is real | |
| hook relays advisories on pass | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | 31 passed | |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | | |

Full suite run by hand: 305 passed, ALL GREEN (was 299; +6 new tests). Kept out of the
table on purpose — the strict gate re-runs each row under a 60s cap.

### Not auto-verified

- **That authors write an honest negative scope.** Reached traceability only. The gate
  accepts `- none`, so it is satisfiable in four keystrokes. It enforces that the question
  was *answered*, never that the answer is *true*. Closing this is not possible in code —
  completeness of a claim list is a judgment call, and the real defence stays human PR
  review. Recorded here rather than designed around.
- **That the tier labels are correct.** Reached nothing. Nothing parses
  "traceability/provenance/truth" out of the bullets or checks them against the Verify
  table. A row labelled `truth` that was never re-run passes.
- **The rollout blast radius beyond this repo.** Reached traceability. Measured here (0
  blocked by default, 52 under `REQUIRE_NOT_AUTO_VERIFIED=1`), but consumers of the harness
  carry their own `specs/` back catalogues that were not measured.
- **That anyone acts on the warning.** Reached nothing. Warn-first trades enforcement for
  goodwill: if the advisories are ignored, the catalogue never drains and the default is
  never flippable. Nothing measures whether the warning changes behaviour.

### Rollback

- Revert the rule: `git revert <sha of this commit>` — restores the previous
  `check_lane_evidence()` and the original test fixtures in one step.
- No data migration and no state change; nothing is written to disk by the rule.
- Partial loosening without a full revert: the rule is already opt-in-to-block. To silence
  the advisory too, return `[]` from `check_lane_warnings()`.

### Rollout — warn-first (decided)

The user chose **warn-first** over blocking immediately.

Default behaviour: a high-risk SUMMARY with no `### Not auto-verified` section prints an
advisory and exits **0**. Setting `REQUIRE_NOT_AUTO_VERIFIED=1` makes it blocking. Same
opt-in shape as `REQUIRE_VERIFY` / `REQUIRE_APP_GATES` / `RISK_CORROBORATION_STRICT`.

Measured, not assumed:

| Back catalogue (54 high-risk specs) | Blocked |
| --- | --- |
| Default (warn-first) | **0** |
| `REQUIRE_NOT_AUTO_VERIFIED=1` | 52 |

To flip the default once the catalogue has drained, change
`_not_auto_verified_is_blocking()` in `scripts/verify_summary.py` — one function, not each
call site.

A warning nobody reads is not a warning, so `hooks/commit-quality-gate.sh` was changed too:
it previously relayed `--lane` output **only on failure**, which would have swallowed every
advisory. It now relays advisory lines on the passing path as well.

### Harness-Delta

- none (this spec *is* the harness delta from PR #189's `### Harness-Delta`)
