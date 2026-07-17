# Review-Chain Benchmark Run — 2026-06-12 baseline

- **Measured skills:** `/correctness-review`, `/intent-review`
- **Skill commit sha:** `4d3a401` (after wave-3 task 2.2 — read-only reviewer framing + the
  `not_observed != absent` finding requirement both in effect).
- **Date:** 2026-06-12
- **Runner:** manual v1 (see `../README.md`). One pass per fixture per oracle (5 fixtures × 2
  oracles = 10 reviewer dispatches), each blind to `truth.md`.
- **Reviewer agent note:** the new `reviewer` agent type (Track 1, `agents/reviewer.md`) is
  **not** registered in this session's agent registry, so these dispatches used a read-only-
  *instructed* `general-purpose` agent. This run therefore measures the upgraded **prompts**,
  not the agent-type tool-whitelist wiring. The structural read-only guarantee is unmeasured
  here (`not_observed != absent`: untested, not "working").

## Per-fixture results (expected oracle)

| Fixture | Defect class | Expected oracle | Caught-by | Verdict | Tokens (corr / intent) |
|---|---|---|---|---|---|
| none-deref | None deref (Optional unguarded) | /correctness-review | /correctness-review | **caught** (P1, right location) | ~45k / ~44k |
| missing-await | Missing await (async) | /correctness-review | /correctness-review | **caught** (P0, right location) | ~44k / ~44k |
| soft-delete-filter | Soft-delete filter missing | /correctness-review | /correctness-review | **caught** (P1, right location) | ~45k / ~44k |
| excess-scope | Unrequested refactor (excess) | /intent-review | /intent-review | **caught** (excess, get_profile refactor) | ~45k / ~45k |
| intent-gap | Validation gap (1 of 2 endpoints) | /intent-review | /intent-review | **caught** (gap, update_watchlist) | ~52k / ~44k |

## Headline numbers

- **Catch rate: 5/5** (each planted defect caught by its expected oracle, right location).
- **Hard false positives: 0** (no reviewer reported a defect that is not real).
- **Approx tokens per pass:** correctness-review ~44–52k, intent-review ~44–45k (subagent
  output tokens; ~445k total for the 10-dispatch matrix).

## Cross-oracle behavior (the off-oracle pass on each fixture)

The non-expected oracle was also run on each fixture, to measure lane discipline:

- **Correctness on the 3 intent/correctness-clean expectations:** stayed in its lane on the
  intent fixtures — it did **not** report the excess scope or the validation gap (correctly
  "not my job"). It *did* surface a real **latent** `model_validate(None)` None-deref in both
  `excess-scope` and `intent-gap` (the modified/updated handlers pass a possibly-`None` repo
  result to Pydantic). See caveat below — these are real secondary bugs I did not intend to
  plant, not false positives.
- **Intent on the 3 correctness fixtures:**
  - `none-deref` → ✅ clean (correctly no intent divergence; noted the None-deref as an
    out-of-scope correctness concern without counting it).
  - `missing-await` → flagged the missing `await` as `drift` ("the method does not return the
    count the user asked for") **and** the `if count < 0` clamp as a minor `excess`. Both are
    real — a bonus second catch of the same underlying defect plus a true unrequested clamp.
  - `soft-delete-filter` → flagged the unrequested `order_by(created_at desc)` as a minor
    `excess` (report-only). True but low-signal.

## `not_observed != absent` discipline (qualitative)

The rule showed up in every pass that made an absence claim:
- none-deref correctness flagged a possible IDOR but labeled it **unknown** ("the project's
  authz convention is not visible here") rather than asserting it.
- soft-delete correctness labeled "could not read `base.py` to confirm a soft-delete helper" as
  unknown, not cleared.
- missing-await intent labeled the `self.repo` → `SubscriptionRepository` binding as
  not_observed rather than a false gap.
- intent-gap intent explicitly justified its gap as **sourced** ("the full `update_watchlist`
  body is present in the diff and contains no validation, so this is an absence, not merely
  not-observed") — exactly the discipline the rule asks for.

## Caveats & limitations (honesty rules)

1. **Two intent fixtures are not correctness-clean.** `excess-scope` and `intent-gap` each
   contain a real latent None-deref (`model_validate(None)`) that correctness-review caught.
   The benchmark's "exactly one planted defect per fixture" claim holds for the *expected*
   oracle but is violated for the correctness oracle on those two. Fixture revision should make
   the intent fixtures runtime-clean so the off-oracle pass is a true false-positive probe.
2. **Agent-type wiring unmeasured.** Track 1's structural read-only guarantee was not exercised
   (see reviewer agent note above). A future run after the `reviewer` agent is registered
   should re-measure with `subagent_type: reviewer`.
3. **Scope of the claim.** This measures only these two skills against these five planted
   defect classes — NOT the full chain, NOT real-world catch rate, NOT defect classes absent
   from the fixture set (`not_observed != absent`). 5/5 here means "these prompts caught these
   five seeded, realistic-but-known defects," nothing broader.
4. **Single run, no re-runs** (per protocol). This is the regression baseline: a future edit to
   either review skill that drops below 5/5 on this set is a regression to investigate.
