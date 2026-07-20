# lint-doc-truth-widen-scope

Lane: normal
Confidence: high
Reason: Widens a CI-gating lint's scope. `scripts/lint-doc-truth.sh` is not on the high-blast list (`harness-manifest.json` → `hard_gates.detectable.high-blast` covers settings.json, hooks/*, render_plan.py — not this), the change is additive and reversible, and the blast radius was measured before implementing (2 findings, both illustrative). No hard gate tripped.
Affects: scripts/lint-doc-truth.sh (CI lint scope), agents/PROJECT.template.md, agents/test-runner.md, tests/scripts/lint-doc-truth.test.sh (new)

## Intent

Close the second of the two "documented guarantee with no enforcing call site" instances found
in PR #119: the doc-truth lint's `DOCS=` allowlist did not cover `agents/` or `rules/`.

## What changed

`DOCS=` now includes `agents/*.md rules/*.md` — **4 docs → 17**. Wrapped in
`shopt -s nullglob` / `shopt -u nullglob`: the loop reports a non-existent entry as
`core doc missing`, so an unmatched glob in a repo with an empty `rules/` would have been a
false failure.

Two illustrative paths that the widened scope surfaced (`tests/services/test_x.py` in
`agents/PROJECT.template.md`, `tests/test_x.py` in `agents/test-runner.md`) were rewritten in the
repo's existing placeholder convention (`test_<entity>`, per `rules/plan-format.md`) rather than
special-cased in the lint. They were never meant to resolve; now they say so.

New hermetic suite `tests/scripts/lint-doc-truth.test.sh` — the script had **no tests at all**.

## Rationale

The scope was chosen by what an agent actually loads, not by what looked important:
`rules/*.md` auto-loads every session via `.claude/rules/`, and `agents/*.md` is read by every
execution subagent. A dangling path in either misleads exactly as much as one in `CLAUDE.md`.
This is not hypothetical — it is how the stale `skills/xia2/PROJECT.md` pointers in three
`agents/` files survived until a manual audit in PR #119.

Fixing the two example paths via the placeholder convention (rather than an exclusion list in
the lint) keeps the lint's rules uniform and makes the docs self-describing: `test_<entity>`
reads as "substitute your own" to a human *and* to the linter.

## Alternatives

- **Add an ignore-list to the lint** for the two example paths — rejected: an exclusion list is
  itself an unenforced claim that drifts, and it would have hidden the fact that those paths were
  never real.
- **Widen to `templates/`, `techstacks/`, `docs/` too** — rejected for now: much larger surface
  with a different false-positive profile (`docs/` holds research prose full of illustrative
  paths). Deliberately left out of scope rather than silently included.
- **Skip the test suite** — rejected: a widening with no test is exactly the failure mode this
  whole PR chain is about. Mutation-tested to prove it is not vacuous.

## Deviations

- Rule 2 — Added `tests/scripts/lint-doc-truth.test.sh`. The script had no test coverage, and
  without a scope guard a future edit could narrow `DOCS=` back with nothing catching it. Not
  literally requested; required for the change to be durable.

### Verify

| Check | Command | Exit | Notes |
|---|---|---|---|
| Lint script syntax | `bash -n scripts/lint-doc-truth.sh` | 0 | |
| Widened lint passes on this repo | `bash scripts/lint-doc-truth.sh` | 0 | 17 docs, zero findings |
| New lint suite | `bash tests/scripts/lint-doc-truth.test.sh` | 0 | 7 passed |
| Full harness suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN; new suite auto-discovered |
| Scope actually widened | `bash -c 'shopt -s nullglob; d=(CLAUDE.md README.md HARNESS.md skills/README.md agents/*.md rules/*.md); test ${#d[@]} -eq 17'` | 0 | 4 → 17 |

**Mutation note:** narrowing `DOCS=` back to the original four docs makes
`tests/scripts/lint-doc-truth.test.sh` report `5 passed, 2 FAILED` (both SCOPE cases). Separately,
appending a reference to a non-existent `rules/this-does-not-exist.md` in `rules/behavior.md`
makes the lint exit 1 — proving the widening catches real drift, not just that it runs. Neither
is listed as a re-runnable row because both require an intentional source edit.

### Rollback

- `git revert <sha>` — reverts lint scope, the two doc edits, and the new suite together.
- Narrow the scope alone without a revert: drop `agents/*.md rules/*.md` from `DOCS=` in
  `scripts/lint-doc-truth.sh`. The two SCOPE tests will then fail, which is intended — delete
  them in the same change if the narrowing is deliberate.

## Harness-Delta

`fix-direct` — closes the second of the two instances recorded in
`specs/skills-readme-truth-sync/SUMMARY.md`. Both are now enforced:
`check_lane_evidence.py` by Check 1.6 (PR #120), and the doc-truth scope by this change.
