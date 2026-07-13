# Review-Chain Benchmark Run — 2026-07-13 · FIND-A + Altitude pass

- **Measured:** `/correctness-review`'s FIND-A finder (`correctness-reviewer-prompt.md`) after two
  edits: (a) the bug-class list reframed as a stack-adaptive checklist, (b) a new **Altitude**
  pass. Correctness oracle only, all 5 fixtures. `/intent-review` unchanged and **not run** here.
- **Baseline:** `results/2026-06-baseline.md` — 5/5, **0 hard false positives**, correctness pass
  CLEAN on the two v2 intent fixtures.
- **Fixture version:** v2 · **Runner:** manual · **Agent:** `subagent_type: reviewer` (opus).
- **Blind:** reviewers were forbidden `benchmarks/`. Greps were pathspec-scoped after the first
  `intent-gap` attempt self-reported contamination (an unscoped `git grep` pulled ~10 lines of
  `truth.md` into context). **That attempt was discarded and re-run clean; the clean run is scored.**

## This run happened in two rounds. Both are recorded.

**Round 1 — the altitude pass as first written: REGRESSION.** It invited architectural commentary
("special cases layered on shared infrastructure", "convention already present nearby"), which
broke the correctness reviewer's own lane rule (*"style/naming/maintainability — quality
reviewer's job"*). Result: `excess-scope`, which the baseline verified **CLEAN**, came back with
**3 "bugs"** — one of them straight from the altitude pass, and one that admitted in its own text
*"redundant, **not** double-executing"* and was reported as a bug anyway. `none-deref` gained a
second false positive from the altitude pass, on the same auth wiring the fixture names as the FP.

**Round 2 — altitude gated on a runtime failure: regression closed.** The gate: *an altitude
finding must name a concrete input/state → wrong outcome that the code as written still allows.
No trigger, no finding — a design opinion is the quality reviewer's job.* Round 2 is what is
scored below.

## Per-fixture results (Round 2)

| Fixture | Expected | Findings | Planted defect caught? | Hard FPs |
|---|---|---|---|---|
| missing-await | caught | **1** (exactly the planted one) | ✅ `:17`, right fix | **0** |
| excess-scope | CLEAN | **0** | — | **0** |
| intent-gap | CLEAN | 2 (both **real** — see below) | — | **0** |
| none-deref | caught | 2 | ✅ `:19` | **1** |
| soft-delete-filter | caught | 3 | ✅ `:13` | **2** |

## Headline

- **Catch rate 3/3 on the correctness fixtures — no recall regression.** The altitude edit did not
  cost recall.
- **The altitude pass is clean: it contributed ZERO false positives across all 5 fixtures.** After
  the gate it declined every time it could not name a trigger — *"No additional altitude finding
  buys its way in"*, *"design opinions … are suppressed per the gate"*, *"Reporting it twice would
  be padding"*. On `missing-await` and `soft-delete` it correctly **converged onto the planted
  defect** instead of inventing a fourth finding.
- **3 hard false positives remain, and they are NOT from the altitude pass** — baseline had 0.
  They come from the base bug-class hunt:
  - `none-deref`: the IDOR claim on `dependencies=[Depends(get_current_user)]` (P0).
  - `soft-delete-filter`: the unstable `ORDER BY` (P3) and the unbounded result set (P2).
  Each is named **in advance** by its fixture's `truth.md` as what a false positive looks like.

## Unresolved: what causes the 3 residual FPs

**I cannot attribute them, and I am not going to guess.** Candidates, none eliminated:

1. the bug-class reframing in this same commit loosened the finder;
2. the baseline ran a read-only-*instructed* `general-purpose` agent, this run ran the
   `reviewer` agent type — different tools, plausibly different behavior;
3. run-to-run variance: this benchmark is **n = 1 per fixture**, and a single sample cannot
   separate a prompt regression from noise.

Distinguishing (1) from (2)/(3) needs repeat runs, which the protocol's "do not re-run until it
passes" rule deliberately makes expensive. Recorded as **open**, not as "fine".

**Mitigation that already exists (but is UNMEASURED here):** all three FPs rest on code the
reviewer could not read — the unreadable `get_current_user`, the unreadable `Watchlist` model.
The SCORE stage now caps such findings at **50**, below the 80 threshold, which would route all
three to *advisory* instead of the fix-loop. **This run measured FIND-A alone, not the pipeline**
(`not_observed != absent`), so that is a design claim, not a measurement. The wrapped run is
still owed.

## Two findings about the FIXTURES, for their owner to adjudicate

Reported separately because scoring must not be allowed to rewrite its own answer key.

1. **`none-deref`'s `truth.md` is inconsistent with the fixture set's own v2 revision.** It
   declares `dependencies=[Depends(get_current_user)]` on an id-addressed route to be *"correct"*
   and any IDOR claim a false positive. But the **v2 revision of `intent-gap` fixed precisely this
   shape** — the README records adding *"owner-scoping on the watchlist update"* to remove a "P0
   ownership/BOLA gap". The same pattern cannot be a real P0 in one fixture and a false positive
   in another. Note that **two independent engines** — this finder and `/code-review`
   (`results/2026-07-13-code-review-swap.md`) — flagged it, with different prompts. Either the
   fixture needs the same owner-scoping revision v2 gave `intent-gap`, or `truth.md` needs to say
   why this route is exempt. **Until adjudicated, it is scored as a false positive, as written.**

2. **`intent-gap` carries an unintended real defect.** `create_watchlist` validates
   `payload.name.strip()` but persists `name=payload.name` — the **unstripped** value. The value
   checked is not the value stored, so `"  Tech  "` round-trips with its padding. This is exactly
   the "fixture carries an unintended defect for the off-oracle" class that forced the v1 → v2
   revision. It is real, so it is not scored as a false positive — but it means the correctness
   pass cannot be CLEAN on this fixture by construction.

## Regression status vs baseline

- **Recall: no regression** (3/3 = 3/3).
- **Altitude pass: no false positives** — the round-1 regression it caused is closed by the gate.
- **False positives overall: REGRESSION stands (0 → 3), cause unattributed.** Do not read this
  file as "the altitude edit is safe, ship it". Read it as: the altitude edit is clean, *and*
  this run surfaced an FP problem in the base finder that the baseline did not show and that
  nobody has explained yet.
