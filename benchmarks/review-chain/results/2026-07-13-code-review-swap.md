# Review-Chain Benchmark Run — 2026-07-13 · candidate engine swap (`/code-review`)

- **Question under test:** can Claude Code's built-in `/code-review` replace the hand-written
  finder inside `/correctness-review` without losing catch rate?
- **Measured:** `/code-review` at `high` effort (workflow-backed: 3 correctness angles + 1
  cleanup finder → one independent verifier per (file,line) → synthesize). Run **standalone**,
  NOT wrapped by `/correctness-review` — this measures the candidate *engine*, not the hybrid.
- **Baseline compared against:** `results/2026-06-baseline.md` (skill sha `4d3a401`) — 5/5,
  0 hard false positives.
- **Date:** 2026-07-13 · **Fixture version:** v2 · **Runner:** manual (per `../README.md`)
- **Scope:** the 3 **correctness** fixtures only. The 2 intent fixtures were not run —
  `/intent-review` is unchanged by this proposal, so it is unmeasured here, not "unaffected"
  (`not_observed != absent`).

## Protocol notes (deviations stated up front)

- Each fixture ran in its own throwaway worktree, one `BASE..HEAD` commit pair, blind.
- Reviewers were explicitly instructed **not** to read `benchmarks/` (holds `truth.md`, the
  answer key), `docs/solutions/`, or `specs/`. `truth.md` was read only afterwards, to score.
- The fixtures are **context-starved by construction**: at the target ref the `app/` subtree
  contains only the changed file. `app/models/`, `app/repositories/base.py`, `app/dependencies/`
  do not exist. This matters — see "Why the false positives" below. The baseline run had the
  same starvation, so the comparison is like-for-like.

## Per-fixture results

| Fixture | Defect class | Caught? | Location | Verdict given | Hard FPs |
|---|---|---|---|---|---|
| missing-await | missing `await` (async) | **caught** | `subscription_service.py:17` ✓ | CONFIRMED | **0** |
| none-deref | None deref (Optional) | **caught** | `user_email.py:19` ✓ | CONFIRMED | **1** |
| soft-delete-filter | soft-delete filter missing | **caught** | `watchlist_repository.py:13` ✓ | PLAUSIBLE | **2** |

## Headline numbers

- **Catch rate: 3/3** on the correctness fixtures — **matches baseline.** Every planted defect
  was found at the right location with the right mechanism.
- **Hard false positives: 3** — baseline was **0**. This is a **regression** and it is the
  finding of this run.
- **Approx cost:** ~583k / ~417k / ~691k subagent tokens per fixture (11 / 8 / 13 agents).
  Baseline was ~44–52k per pass. Roughly **10–15× the token cost** for the same catch rate.

## The false positives (scored against each fixture's own `truth.md`)

Each fixture's `truth.md` names, in advance, what a false positive would look like. `/code-review`
walked into three of them:

1. **`none-deref`** — `truth.md`: *"a false-positive would look like: flagging the
   `dependencies=[Depends(get_current_user)]` auth wiring as missing/incorrect (it is correct)."*
   `/code-review`'s **top-ranked, CONFIRMED** finding was exactly that — an IDOR / broken
   object-level authorization claim on that line. The finding's own prose admits *"the
   `get_current_user` dependency is not present anywhere in this tree, so I cannot rule out that
   it performs path-scoped authorization internally"* — and then reports CONFIRMED anyway. The
   caveat is in the text; the verdict overrides it.
2. **`soft-delete-filter`** — `truth.md` names **two** FPs: *"flagging the `order_by` as a
   problem, or claiming an N+1 / unbounded-result issue (the result is per-user and bounded)."*
   `/code-review` reported **both**: a nondeterministic-`ORDER BY` tiebreaker finding, and a
   "no `LIMIT`, unbounded read" finding. It reported 8 findings total on a 9-line diff.

The baseline reviewer saw the same auth wiring on `none-deref` and declined to assert it —
it labeled the possible IDOR **unknown** ("the project's authz convention is not visible here"),
per `rules/behavior.md` §1.

## Why the false positives (mechanism, not excuse)

`/code-review`'s verify stage is **recall-biased by design**. Its verdict ladder instructs:
*"PLAUSIBLE by default — do not refute a candidate for being 'speculative' or 'depends on runtime
state' when the state is realistic… REFUTED only when constructible from the code."* In a tree
where the model and base class **cannot be read**, nothing is constructible, so nothing gets
refuted — every speculation survives as PLAUSIBLE. That is the correct behavior for a
high-recall finder and the wrong behavior for a gate.

The harness reviewer avoids this not by being smarter but by being **bound by a different rule**:
`not_observed != absent` forces an unreadable dependency to be reported as *unknown*, never as a
defect. That rule is what bought the baseline its 0 FPs.

**Honest caveat on generalization:** these fixtures are context-starved, which is the worst case
for a speculative finder. On a *real* diff in this repo (the `harness-status.sh` bake-off,
same day, complete readable file) `/code-review` produced 5 findings, all CONFIRMED, all
reproduced, **0 false positives** — and it found a real live boundary defect that the harness
reviewer missed. So this run is evidence about **precision under missing context**, not a
blanket precision claim. Both facts are real; neither cancels the other.

## What this run decided

**The engine swap is rejected. `/code-review` augments the harness finder; it does not replace
it.** Three conclusions, each traceable to a number above:

1. **Equal recall, worse precision, 10–15× cost** → replacing FIND-A buys nothing and costs a
   lot. The hypothesis that drove the swap proposal — that the finder's FastAPI-framed bug-class
   list would blind it on non-FastAPI code — was **not supported**: it caught 3/3 here, and it
   caught the bash/python bugs in the same-day `harness-status.sh` bake-off too. The list was a
   checklist, not a blindfold.
2. **SCORE/THRESHOLD(80) stays.** The plan to delete it as redundant with `/code-review`'s
   verifier was wrong. The verifier is a *recall* filter ("PLAUSIBLE by default"); the scorer is
   a *precision* filter. Removing it is precisely how these 3 false positives would reach the
   fix-loop. The scorer now also caps at 50 any finding resting on an unreadable file.
3. **What `/code-review` uniquely brings is the `altitude` lens** — "is this fix deep enough, or
   a bandaid?" — which is not a bug class and which no per-line hunt asks. It is the one thing it
   found that the harness reviewer could not (`harness-status.sh`: a boundary defect that
   survived two rounds of human fixes). That lens has been **ported into FIND-A's prompt**, so
   the cheap default path now gets it without paying for the second engine.

**Shipped design:** FIND-A (harness finder, + new Altitude pass) always; FIND-B (`/code-review
high`) additionally on **high-risk lanes only**, pooled into the same SCORE → THRESHOLD →
classify → fix-loop. Ensemble diversity where the risk justifies the spend; cheap everywhere else.

## Regression status vs baseline

**Catch rate: no regression (3/3 = 3/3). False positives: REGRESSION (0 → 3) for the raw engine
run standalone** — which is why it is not shipped standalone.

**This run measured the raw candidate engine, NOT the shipped pipeline.** The shipped design
(FIND-A + Altitude, optional FIND-B, SCORE, threshold 80) is therefore **unmeasured** —
`not_observed != absent`. Two runs are still owed and are not claimed here:

- **the altitude-augmented FIND-A** against all 5 fixtures, to confirm the prompt addition did
  not cost recall or precision on the baseline set;
- **the wrapped hybrid** on high-risk (FIND-A + FIND-B + SCORE), to confirm the scorer actually
  filters the 3 false positives this run exposed.

Until those exist, the 5/5 baseline is the only measured claim about the shipped chain, and it
was measured on the **pre-altitude** prompt.
