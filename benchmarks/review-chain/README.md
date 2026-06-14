# Review-Chain Micro-Benchmark (manual v1)

The repo's first empirical measurement of what the review chain actually catches. v1 is a
**manual protocol** — there is no automated runner, and adding one is explicitly out of scope
for this version (automate later only if the manual loop proves valuable).

## Claim discipline (read first)

Borrowed from the breezing-bench design: **this benchmark measures only whether the two review
skills (`/correctness-review`, `/intent-review`) catch the planted defect classes in these
fixtures.** It is *not* evidence about the full workflow chain, about real-world catch rate, or
about defect classes not represented here. A number from this benchmark is a claim about *these
fixtures and these two skills*, nothing more. State that scope wherever the number is cited
(`not_observed != absent` — a defect class we did not seed is unmeasured, not "handled").

## Fixture layout

Each fixture lives under `fixtures/<name>/` and contains exactly three files:

- **`intent.md`** — a verbatim-style user request (what the user asked for).
- **`diff.patch`** — a small, self-contained diff that implements `intent.md` with **exactly
  one planted defect**.
- **`truth.md`** — the ground truth: the defect class, its exact location, which oracle should
  catch it (`/correctness-review` or `/intent-review`), and what a false-positive would look
  like for this fixture.

## Running a fixture

A **run** is:

1. Apply the fixture's `diff.patch` in a scratch worktree (one throwaway worktree per fixture
   so fixtures never contaminate each other).
2. Execute `/correctness-review` standalone, then `/intent-review` standalone, over that diff.
3. Score each pass against `truth.md` as one of **caught / missed / false-positive**:
   - **caught** — the pass reported the planted defect (right defect, right location).
   - **caught-wrong-reason** — flagged the defect but for an incorrect rationale; record it and
     say so (it is *not* a clean catch).
   - **missed** — the pass did not report the planted defect.
   - **false-positive** — the pass reported a defect that is not the planted one and is not real.
4. Record the approximate **token cost per pass** (from session usage).

## Results

Results land in `results/<date>-<label>.md`, built from `results/template.md`. Columns:
`fixture | defect class | expected oracle | caught-by | verdict | tokens`. The headline numbers
are the **catch rate (n/5)**, the **false-positive count**, and approximate token cost per pass.

## Fixture revisions

Fixtures are versioned by the honesty rule that each carries **exactly one planted defect** for
the *expected* oracle. When a fixture is found to carry an unintended defect for the *other*
oracle, it is revised — the planted defect is preserved, the unintended one removed — and the
revision is recorded here. Past result files state which fixture version they measured.

- **v2 (2026-06-14)** — `excess-scope` and `intent-gap` made **correctness-clean**. v1 of both
  carried real latent correctness bugs (a `model_validate(None)` None-deref in each, plus a P0
  ownership/BOLA gap in `intent-gap`) that the off-oracle `/correctness-review` pass correctly
  caught — so the off-oracle pass was not a clean false-positive probe. v2 adds `None` guards
  (and owner-scoping on the watchlist update) while **keeping the planted intent defect intact**
  (the excess `get_profile` refactor; the missing empty-name validation on `update_watchlist`).
  The expected-oracle defects are unchanged, so the **5/5 expected-oracle catch-rate baseline
  still holds**; only the off-oracle correctness pass changes (now expected **CLEAN** on these
  two). v1 results: `results/2026-06-baseline.md`, `results/2026-06-14-reviewer-agent.md`.
  **Verified (2026-06-14):** the off-oracle `/correctness-review` pass (via `subagent_type:
  reviewer`) reports **CLEAN** on both v2 fixtures — no asserted runtime bug, unknowns labeled —
  confirming they are now true false-positive probes.

## Honesty rules

- Report misses plainly. A miss is a finding about the skill, not a failure of the benchmark.
- **Do not re-run a fixture until it passes** — the first scored run is the record.
- If a skill catches a defect for the wrong reason, score it `caught-wrong-reason` and say so.
- The baseline file (`results/2026-06-baseline.md`) is the regression baseline for any future
  edit to `/correctness-review` or `/intent-review` — note the measured skill commit sha in it.
