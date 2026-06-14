# Review-Chain Benchmark Run — 2026-06-14 reviewer-agent

- **Measured skills:** `/correctness-review`, `/intent-review`
- **Skill commit sha:** `bad391a` (v2 HEAD; reviewer prompts + `agents/reviewer.md` unchanged
  since the `4d3a401` baseline — no review-skill edits in the P1-B/P2-H gap-closure work).
- **Date:** 2026-06-14
- **Runner:** manual v1 (see `../README.md`). Full matrix — 5 fixtures × 2 oracles = 10
  reviewer dispatches, each blind to `truth.md` (the dispatch prompt forbids reading it).
- **Reviewer agent note (closes baseline caveat #2):** this run dispatched the **registered
  `reviewer` agent type** (`subagent_type: reviewer`, tools `Glob, Grep, Read, Bash` — Write /
  Edit / Agent excluded). The 06-12 baseline could only use a read-only-*instructed*
  `general-purpose` agent because the agent type was not registered then. So this run measures
  the **structural read-only wiring**, not just the prompts. Every dispatch completed with read
  tools only; no reviewer attempted a write (it structurally cannot). The catch-rate holds under
  the structural guarantee.

## Per-fixture results (expected oracle)

| Fixture | Defect class | Expected oracle | Caught-by | Verdict | Tokens |
|---|---|---|---|---|---|
| none-deref | None deref (Optional unguarded) | /correctness-review | /correctness-review | **caught** (P1, `user.email` unguarded, right fix) | ~35.2k |
| missing-await | Missing await (async) | /correctness-review | /correctness-review | **caught** (P0, `count_active` not awaited, right fix) | ~34.9k |
| soft-delete-filter | Soft-delete filter missing | /correctness-review | /correctness-review | **caught** (P1, `deleted_at IS NULL` missing, right fix) | ~35.1k |
| excess-scope | Unrequested refactor (excess) | /intent-review | /intent-review | **caught** (excess, `get_profile`→`get_profile_with_stats` refactor) | ~35.6k |
| intent-gap | Validation gap (1 of 2 endpoints) | /intent-review | /intent-review | **caught** (gap, `update_watchlist` missing guard; quoted the "BOTH" clause) | ~35.5k |

Verdict ∈ {caught, caught-wrong-reason, missed, false-positive}.

## Headline numbers

- **Catch rate: 5/5** — every planted defect caught by its expected oracle, right location, right
  fix. **Matches the 06-12 baseline (5/5).** No regression after P1-B/P2-H; now also confirmed
  under the structural read-only agent.
- **Hard false positives: 0** — no reviewer reported a defect that is not real. Absence claims
  were labeled `unknown` rather than asserted (IDOR on none-deref, `get_profile_with_stats`
  contract on excess-scope, schema-dependent `None.strip()` on intent-gap).
- **Approx tokens per pass:** correctness-review ~34.9–36.1k, intent-review ~35.2–35.6k
  (subagent output tokens; ~354k total for the 10-dispatch matrix — below the baseline's ~445k
  because the `reviewer` agent runs a tighter read-only surface than the general-purpose agent).

## Cross-oracle behavior (the off-oracle pass on each fixture)

Consistent with the baseline's documented behavior:

- **Intent oracle on the 3 correctness fixtures:**
  - `none-deref` → ✅ **CLEAN — faithful to intent**; correctly declined to count the None-deref
    as an intent finding (no intent clause covers the not-found case — dropped per quote-intent
    discipline). Exact lane discipline.
  - `missing-await` → flagged the missing `await` as **drift** ("does not return the count the
    user asked for") + the `count < 0` clamp as minor **excess**. Both real — a bonus second
    catch of the same defect via the intent lens, plus a true unrequested clamp. Matches baseline.
  - `soft-delete-filter` → flagged the missing soft-delete as a **gap** (with an explicit caveat
    that `intent.md` does not literally state deletion semantics — honest uncertainty, not an
    assertion) + the `order_by` as minor **excess**. Slightly more aggressive than baseline but
    caveated; the order_by excess matches baseline.
- **Correctness oracle on the 2 intent fixtures (confirms baseline caveat #1 — these fixtures
  are not correctness-clean):**
  - `excess-scope` → real latent P1 None-deref (`SettingsResponse.model_validate(None)` on
    `get_settings`); `get_profile_with_stats` contract risk labeled `unknown`. Matches baseline.
  - `intent-gap` → real P0 BOLA/IDOR on `update_watchlist` (no `user_id` ownership filter; the
    create path scopes by user, update does not) + latent None-deref on `model_validate(None)` +
    inconsistent validation. Schema-dependent bits labeled `unknown`. Richer than baseline but
    all findings real or `unknown`.

## Notes

- **Misses:** none.
- **Caught-wrong-reason:** none — every expected-oracle catch named the right defect, location,
  and fix.
- **What this run adds over the baseline:** closes **caveat #2** — the structural read-only
  `reviewer` agent is now exercised and the 5/5 catch-rate holds under it (the prior baseline
  measured prompts only). **Caveat #1** (two intent fixtures carry real latent correctness bugs)
  still stands — the off-oracle correctness passes reconfirm it; fixture revision to make the
  intent fixtures runtime-clean is still the open follow-up.
- **Scope reminder:** this measures only these two skills against these five planted defect
  classes — not the full chain, not real-world catch rate, not defect classes absent from the
  fixture set (`not_observed != absent`). 5/5 here means "these prompts + the read-only reviewer
  agent caught these five seeded, realistic-but-known defects," nothing broader.
