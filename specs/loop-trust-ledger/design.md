---
slug: loop-trust-ledger
status: proposed
owner: Minh Tran
created: 2026-07-18
type: design
---

# Loop-Trust Ledger — make the trust-metrics ledger a *governing* signal

> **Status: proposal for review.** This document specifies a design; it ships **no** code.
> The intent is to decide whether the direction is right before any implementation spec is
> written. Open questions for the reviewer are collected in §9.

## 1. Motivation

The harness governs autonomy along two axes today, and **both are forward-looking and
per-task**:

- **Lane** (`tiny | normal | high-risk`) — set at intake by `/feature-intake` from a risk
  checklist. Drives *ceremony* (how much proof).
- **Confidence** (`high | medium | low`) — drives *interruption* (whether a human is asked).

Neither axis measures **how much the self-verification loop has actually earned trust over
time**. We classify each task's risk before doing it; we never feed back *how well the loop
performed on the tasks we already shipped*. The `docs/harness-experimental/trust-metrics.md`
ledger is the closest thing we have — but it is **descriptive, not governing**: a human reads
the trend line, and nothing computes a score or changes harness behaviour from it.

This is the exact gap named in Boris Cherny's *Steps of AI Adoption* (2026-07-16). His model
frames agent-adoption maturity as five steps whose constraint is always a **trust/verification
bottleneck**, and names the **Step-3 trap** precisely:

> *"scaling agent count before the loop has earned widespread trust."*

Our wave-parallelism machinery (`rules/wave-parallelism.md`) lets the orchestrator fan out
≥2 subagents per wave. **Nothing today ties how wide we fan out to demonstrated loop
reliability.** We could spawn a 5-task wave on a loop that has been catching nothing — which
is the trap, mechanized.

The fix is a third axis: a **backward-looking, measured loop-trust signal** derived from the
ledger, that modulates *parallelism / autonomy aggressiveness* — orthogonal to the per-task
risk lane, which stays exactly as it is.

## 2. The insight being imported

| Axis | Direction | Granularity | Governs | Exists today? |
|---|---|---|---|---|
| **Risk lane** | forward (predict this task's danger) | per-task | ceremony / proof depth | ✅ `/feature-intake` |
| **Confidence** | forward (how sure of the plan) | per-task | human interruption | ✅ `/feature-intake` |
| **Loop-trust** | **backward (how well the loop performed)** | **cross-task, rolling** | **fan-out width / autonomy dial** | ❌ *this proposal* |

The claim from the adoption model: **you advance autonomy by earning trust in the loop, not by
adding agents.** Risk-per-task tells you how careful to be *on this change*; loop-trust tells
you how much unsupervised parallelism the *system as a whole* has earned. They are independent
— a high-trust loop still runs full high-risk ceremony on an auth change; a low-trust loop
narrows its waves even on routine work.

## 3. What we have today (ground truth)

- **`docs/harness-experimental/trust-metrics.md`** — a markdown table, one row per merged PR.
  Columns: `Date | Slug | Lane | Affects | Confidence | Flags | Escalated | Outcome | Notes`.
- **`scripts/bookkeeping.sh`** — appends the row in the post-merge CI pipeline (event-sourced,
  pipe-escaped title). This is the write path.
- **`scripts/harness-status.sh`** — prints the last 5 rows for a human. This is the read path.

What the ledger captures: **classification** (lane, confidence, flags, escalated) and a coarse
**outcome** (`shipped`). What it does **not** capture — and what a trust score needs:

- Did the review chain (correctness / intent / code-review) **catch a real issue** that was
  fixed pre-ship? (loop working) — or find nothing? (clean *or* blind — indistinguishable today)
- Did the `### Verify` block **run and pass**? (already partly enforced by
  `scripts/check_verify_rows.py` + `verify_summary.py`, but not aggregated across tasks)
- Did a defect **escape** to a post-ship revert or a follow-up `fix(...)` PR pointing back at
  the slug? (the loop let a bug through)
- Did escalations resolve as **"proceed unchanged"** (over-caution) vs **"narrowed / blocked"**
  (a correct catch)? (calibration signal — already the ledger's stated purpose in its header)

The ledger's own header already states its purpose is *"calibrate autonomy over time … if
under-classification recurs, tighten; if escalations keep resolving as 'proceed unchanged',
loosen."* — this proposal is that sentence, mechanized.

## 4. Proposed: the loop-trust score

A single **rolling, coarse** score over a trailing window of the last *N* merged tasks
(proposed `N = 20`, i.e. roughly the ledger's recent history). Coarse on purpose — a letter
grade or a small integer, **never a fake-precise decimal**. Four backward-looking signals feed
it:

1. **Review-catch health** — of tasks where the review chain ran, what fraction produced a
   real finding that was fixed pre-ship. A loop that *never* catches anything is either
   perfect or blind; sustained zero-catch is a *distrust* signal, not a trust signal.
2. **Verify-pass rate** — fraction of tasks whose `### Verify` block ran ≥1 real check at
   exit 0 (leaning on the existing `check_verify_rows.py` / `verify_summary.py` gates).
3. **Escaped-defect rate** — fraction of recent tasks followed within the window by a revert
   or a `fix(...)`/`hotfix` PR naming the same `Affects` surface or slug. This is the **most
   load-bearing** signal: it is the only one measuring what the loop *missed*.
4. **Escalation calibration** — ratio of escalations that resolved "proceed unchanged"
   (over-caution) to those that were narrowed/blocked (correct). Extremes in either direction
   lower trust (over-caution = miscalibrated conservative; never-escalate = miscalibrated
   reckless).

The score is a **weighted combination**, weighted toward escaped-defects (§4.3) because a loop
that ships bugs has not earned width regardless of how green its own checks look. Exact weights
are an open question (§9) — v1 can start with escaped-defect as a hard cap and the others as
advisory inputs.

## 5. How the score governs behaviour (the feedback loop)

The score modulates **one dial: how aggressively the orchestrator fans out and skips the human
notify step** — never the hard gates.

| Loop-trust | Max wave width | Human on normal lane | Verify requirement |
|---|---|---|---|
| **Low** | 1–2 tasks | notify-and-proceed → **ask** | required at normal + high-risk |
| **Medium** (default) | current behaviour (`rules/wave-parallelism.md`) | notify-and-proceed | required at high-risk (today's rule) |
| **High** (sustained) | wider waves permitted | notify-only, no gate | unchanged |

Key invariants:

- **The score never touches Rule-4 hard gates.** Auth/authz, data-loss/migration, public
  contract, high-blast files, etc. (`harness-manifest.json` → `hard_gates`) stay exactly as
  enforced by `risk-corroboration.sh`. A high-trust loop does **not** get to auto-approve an
  auth change. Trust buys *parallelism*, not *permission*.
- **Risk lane wins on ceremony.** A high-risk task runs the full chain even at high loop-trust.
  The score only widens/narrows the *parallelism and human-notify* dial within what the lane
  already allows.
- **One bad merge must not tank the score** — the rolling window (§4) absorbs single events;
  the score moves on trends, matching the ledger header's "if X *recurs*" language.

## 6. Anti-goals / failure modes to design against

- **Goodhart** — if the score becomes a target, agents learn to manufacture review-catches or
  trivial verify rows. Mitigation: escaped-defect (§4.3) is the dominant term and is the one
  signal an agent cannot game by adding ceremony; the others are advisory. Plus the
  measure-before-govern rollout (§7).
- **False precision** — no `0.873` trust scores. Coarse grade only.
- **Automation-readiness** — this introduces a standing computation that could gate real work.
  Per `docs/solutions/harness/automation-readiness.md`, it must fail *open and loud*: if the
  score can't be computed (missing data, parse error), the harness behaves as **medium**
  (today's behaviour) and says so — never silently narrows or widens.
- **Meta-trust** — we must trust the trust signal before it governs anything. Hence §7 ships it
  read-only first.

## 7. Phased rollout (measure → surface → govern)

Deliberately staged so the signal earns *its own* trust before it changes behaviour:

- **Phase 0 — Measure.** Extend the SUMMARY `### Verify` capture + `bookkeeping.sh` to record
  the four signals (§4) as new ledger columns. No score, no behaviour change. Pure data
  collection.
- **Phase 1 — Surface (read-only).** A `scripts/compute_loop_trust.py` reads the ledger and
  prints a coarse grade; `harness-status.sh` shows it. **No behaviour change** — the
  orchestrator ignores it. We watch whether the grade tracks reality for a few weeks.
- **Phase 2 — Govern.** Only after Phase 1 proves the grade is sane, wire it into
  `rules/orchestration.md` / `rules/wave-parallelism.md` as the fan-out-width input in §5.

Each phase is its own spec + PLAN + PR. This document greenlights only the **direction**.

## 8. Prerequisites & touched surfaces (for whoever implements)

- **New data**: 3–4 columns on `trust-metrics.md` (schema change — the ledger is machine-read
  by `harness-status.sh` and appended by `bookkeeping.sh`; both must move together).
- **Write path**: `scripts/bookkeeping.sh` (post-merge CI — a standing automation; touching it
  is `automation-readiness` territory).
- **Read/compute**: new `scripts/compute_loop_trust.py` + pytest.
- **Governance wiring (Phase 2 only)**: `rules/orchestration.md` (fan-out budget table),
  `rules/wave-parallelism.md` (max wave width), `skills/feature-intake` (surface score at
  intake alongside lane/confidence).
- **Escaped-defect detection** is the hard part — it needs a reliable way to link a
  `fix(...)`/revert PR back to the slug/`Affects` it repairs. Candidate: a `Fixes-slug:` trailer
  convention, or matching on the `Affects` surface. **Open question (§9).**

## 9. Open questions for the reviewer

1. **Is the third axis worth it**, or does per-task risk + confidence already cover enough?
   (The counter-argument: our waves are usually 1–2 tasks anyway, so fan-out-width governance
   may be low-value until we routinely run wider waves.)
2. **Escaped-defect linkage** — adopt a `Fixes-slug:` commit trailer, match on `Affects`, or
   defer this signal to a later phase and start with the three we can already measure?
3. **Weights** — start with escaped-defect as a hard cap + others advisory, or a flat weighted
   sum? (§4) — the external prior art in §11 gives a concrete worked formula to start from.
4. **Window size** `N` — 20 merges? Time-based (last 30 days) instead, to match the
   `docs/solutions/` 30-day staleness convention?
5. **Scope of governance** — should Phase 2 also feed the auto-mode aggressiveness / permission
   pre-approval story, or stay strictly on wave-width + human-notify?

## 10. Relationship to existing work

- Extends, does not replace, `docs/harness-experimental/trust-metrics.md` (adds columns + a
  derived score; the per-task rows stay).
- Complements `specs/entropy-trend` (that gives *entropy* a trend line; this gives *trust* a
  trend line — sibling metrics, both event-sourced off post-merge).
- Sits downstream of the review oracles (`correctness-review`, `intent-review`, `code-review`)
  and the verify gates (`check_verify_rows.py`, `verify_summary.py`) — it **aggregates their
  per-task outcomes into a cross-task signal**, which none of them do individually.

## 11. Prior art — confidence as a behavioral gate (external)

The idea that a *trust/confidence number should govern real behaviour* — not just annotate it —
is not hypothetical. Licaomeng's *"Building a Production Agent Harness"* (Medium, 2026)
describes an always-on on-call/dev harness on Claude Code that already runs a mechanized
confidence gate in production. Its mechanics are worth importing as a **starting point for §4
(the score) and §5 (how it governs)** — adapted from *per-investigation-iteration* (theirs) to
*cross-task rolling* (ours):

- **Confidence is a 0–100 number that gates behaviour, not a label.** Thresholds fire real
  transitions: `< 70` cannot exit the loop; `≥ 70` + done + no open questions opens the
  adversarial-review phase; `≥ 95` may auto-execute non-destructive actions; a drop `> 10%`
  across two consecutive rounds exits with reason `degrading`. This is the concrete shape our
  soft `high | medium | low` confidence label is missing.
- **A hard ceiling *formula*, not a vibe.** Their assertion ceiling is
  `1.0 − (open_questions × 0.08) − (unchecked_sources × 0.05)` — confidence is *capped* by how
  much is still unknown. This directly answers §9-Q3 (weights): start with a subtractive
  ceiling driven by unresolved signals, rather than a flat weighted sum, and let escaped-defects
  (§4.3) pull the cap down further.
- **Structural gates emit non-blocking "guard notes", not hard stops.** Their 19 quality-gate
  functions check *structure* (e.g. "every fix action must pair with a `verify_action`";
  "confidence may not rise when open-questions grew") and, on violation, prepend the note to the
  next iteration's prompt instead of blocking. That is a third enforcement mode our harness
  lacks (we have only `warn` and hard-`deny`) — relevant to how a low loop-trust score should
  *nudge* rather than *halt*.
- **Ground truth on the wire.** Success is a real operation validated by exit code
  (`git push` exit 0), never the agent's self-report — the same principle as our
  evidence-over-assertion `### Verify` rows, and the reason escaped-defect (§4.3) must be
  measured from *actual* follow-up reverts/fixes, not from an agent claiming a clean loop.

**What does not transfer:** their gate is per-iteration *inside one investigation*; ours is
per-task *across shipped work*. Their confidence resets each case; our loop-trust must persist
and roll (§4). And their numbers (0.08, 0.05, the 70/95 thresholds) are tuned to their domain —
we adopt the *shape* (subtractive ceiling, threshold-gated transitions, guard-note nudges), not
the constants, which Phase 1 (§7, measure read-only) would calibrate against our own history.

