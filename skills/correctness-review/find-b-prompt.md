# FIND-B — dispatch the second engine (`/code-review`) and normalize its output

FIND-B runs the built-in `/code-review` as a second, independent finder on **high-risk lanes
only**, and pools its findings with FIND-A's before SCORE. This file is its dispatch template —
the counterpart to `./correctness-reviewer-prompt.md` (FIND-A) and `./correctness-scorer-prompt.md`
(SCORE).

**Read this before wiring FIND-B.** It is two steps, not one, and the first step is the only
stage of this pipeline the **controller must run itself**.

---

## Why FIND-B cannot be a subagent (the constraint that shapes everything below)

FIND-A and SCORE both dispatch `subagent_type: reviewer`. That agent is read-only **by
construction** — `agents/reviewer.md` whitelists `Glob, Grep, Read, Bash` and deliberately
excludes `Write`, `Edit`, and `Agent`.

It also has **no tool that can invoke a skill**. `/code-review` is a skill, not an executable —
`bash /code-review` is not a thing. So a `reviewer` subagent **cannot** run FIND-B, and neither
can any subagent FIND-A might wish to spawn (it has no `Agent` tool either).

**Therefore: the controller — the session running `/correctness-review` — invokes `/code-review`
directly, via its own Skill tool.** This is the one stage that is not delegated. Everything after
it is.

---

## Gate — when FIND-B runs at all

FIND-B costs roughly **10–15× the tokens of FIND-A for the same measured recall**
(`benchmarks/review-chain/results/2026-07-13-code-review-swap.md`). It buys *coverage* — a second
engine with different angles and different blind spots — not correctness. Spend it only where the
risk justifies it.

| Entry point | Lane source | FIND-B |
|---|---|---|
| **In-flow** (`subagent-driven-development`) | the caller passes the lane | run **iff** lane is `high-risk` |
| **Standalone, slug in play** | read `Lane:` from `specs/<slug>/SUMMARY.md` | run **iff** lane is `high-risk` |
| **Standalone, no slug** | none exists — `/feature-intake` never ran | **skip**, unless the user explicitly asks |
| **Any entry, user asks** (`/correctness-review --find-b`) | n/a | run |

**Default off when the lane is unknown.** A missing lane is *unknown*, not *high-risk*
(`rules/behavior.md` §1 — `not_observed != absent`). Silently spending 10–15× on an ad-hoc review
nobody asked for is the wrong failure mode. Say which way you resolved it:

> FIND-B: skipped — no lane in play (standalone, no slug). Pass `--find-b` to force it.

---

## Step B1 — the controller invokes `/code-review` (not delegated)

```
Skill:
  skill: code-review
  args: "high"        # "xhigh" when the diff is large (> ~40 changed files or > ~2k changed lines)
```

**Three hard constraints. Violating any one of them breaks the pipeline:**

1. **Never pass `--fix`.** FIND-B is a *finder*. `--fix` applies findings to the working tree —
   it would mutate the code under review, bypass SCORE entirely, and import the engine's false
   positives straight into the diff as edits. The whole argument for keeping SCORE
   (`SKILL.md` → "Why SCORE survives") is that this engine's findings must be filtered *before*
   anything acts on them.
2. **Never pass `--comment`.** That posts to the PR. A review stage does not publish.
3. **Never pass `ultra`.** It is a billed cloud review that the controller cannot launch on the
   user's behalf. `high` / `xhigh` is the local, agent-invocable ladder.

**Range alignment.** `/code-review` reviews *the current diff* — it does not accept an arbitrary
`BASE..HEAD`. Before B1, make the working tree BE the range under review (the same range FIND-A
was given). In practice that means the branch is checked out and the range is
`merge-base..HEAD` + working tree, which is the common case. If the range under review is **not**
what `/code-review` would see (an old range, a range on another branch), **skip FIND-B and say
so** — a second engine reviewing the wrong code is worse than no second engine.

---

## Step B2 — normalize its output into FIND-A's shape

`/code-review` reports in its own vocabulary. SCORE and the classify stage consume FIND-A's.
The gap is real and must be closed explicitly — pooling is not a no-op.

| `/code-review` emits | FIND-A's report format needs | Mapping |
|---|---|---|
| `file`, `line` | **Location** (`file:line`) | direct |
| `summary` (one-sentence defect) | the finding claim | direct |
| `failure_scenario` (*concrete inputs/state → wrong output/crash*) | **Trigger** + **Wrong outcome** | split on the `→` — the left side is the Trigger, the right side is the Wrong outcome |
| `category` (`correctness` · `simplification` · `efficiency` · `test-coverage`) | — | **filter**, see below |
| `verdict` (`CONFIRMED` \| `PLAUSIBLE`) | — | **discard**, see below |
| — | **Severity** (`P0`–`P3`) | not emitted — the normalizer assigns it |
| — | **Rule class** (`1–3` \| `4`) | not emitted — the normalizer assigns it |
| — | **Fix** | derive a one-line direction from `summary` |

### Filter: drop everything that is not a runtime bug

`/correctness-review` hunts **runtime bugs only** (`SKILL.md` → "Not for style, naming, or
maintainability"). `/code-review` also emits cleanup findings. Keep `category: correctness`; drop
`simplification`, `efficiency`, `test-coverage`, and any other non-correctness category.

Dropping is not discarding: **report the dropped count and titles inline** as a cleanup
by-product, so the user can act on them via `/simplify` or `/code-review` standalone. Do not pool
them, and do not silently bin them.

### Discard the verdict — this is the load-bearing rule

**`CONFIRMED` must NOT be carried into SCORE as confidence.** `/code-review`'s verify stage is
*recall*-biased by design (*"PLAUSIBLE by default — do not refute a candidate for being
speculative"*), so in a tree where a dependency cannot be read, nothing gets refuted and every
speculation survives as CONFIRMED. Measured: it asserted three defects — an IDOR on correct auth
wiring, an unstable `ORDER BY`, an unbounded read — that each fixture's `truth.md` had named **in
advance** as what a false positive looks like, one of them CONFIRMED and top-ranked, its own prose
admitting it *"cannot rule out"* the opposite.

Importing that verdict as a score is precisely how those three reach the fix-loop. **SCORE
re-derives confidence from the code, blind to both finders' reasoning.** Carry the verdict as
provenance only (`origin: FIND-B (code-review, CONFIRMED)`), never as a score, and **do not pass
it into the scorer prompt** — the scorer's independent context is what makes it a precision gate.

### Dispatch

One normalizer agent for the whole FIND-B batch — it is a translation pass, not a judgment pass,
so it does not need per-finding isolation the way SCORE does.

```
Task tool (reviewer):
  description: "Normalize FIND-B (/code-review) findings for <slug>"
  subagent_type: reviewer
  # read-only by construction — it translates findings, it does not re-adjudicate them
  model: <cheap — this is a mechanical mapping, not analysis>
  prompt: |
    You are a finding normalizer. A second review engine (`/code-review`) produced the
    findings below. Rewrite them into this project's correctness-finding format so they can
    be pooled with the primary finder's output and scored.

    You are NOT re-judging these findings. Do not add findings, do not remove findings for
    being weak, do not soften or strengthen a claim. Translate faithfully. SCORE decides what
    is real — that is not your job, and pre-filtering here would defeat it.

    ## Inputs

    - **Raw findings**: [paste /code-review's findings — file, line, summary, failure_scenario,
      category, verdict]
    - **BASE_SHA**: [commit before the first task]
    - **HEAD_SHA**: [current commit after all tasks]

    ## What to do

    1. **Drop non-correctness findings.** Keep only `category: correctness`. List the dropped
       ones separately at the end (title + category) — they are a cleanup by-product, not
       pipeline input.

    2. **For each kept finding, emit exactly this shape** (see
       `.claude/rules/auto-correct-scope.md` for Rule definitions):

       - **Severity**: `P0` (data loss / auth bypass / crash on common path) |
         `P1` (wrong result / crash on edge path) | `P2` (degraded behavior) |
         `P3` (minor correctness issue). Assign it from the failure_scenario's actual
         consequence — `/code-review` does not emit severity.
       - **Rule class**: `Rule 1–3` (a mechanical fix an implementer can apply) |
         `Rule 4` (STOP — schema/API contract/auth/removing behavior/new dependency, i.e.
         needs architectural judgment). Assign from the nature of the fix, not its size.
       - **Location**: `file:line`, taken verbatim.
       - **Trigger**: the concrete input or state — the LEFT side of failure_scenario's arrow.
       - **Wrong outcome**: what actually happens — the RIGHT side of the arrow.
       - **Fix**: one-line direction, derived from the summary.
       - **Origin**: `FIND-B (code-review, <verdict>)` — provenance only.

    3. **If a finding has no concrete trigger** — the failure_scenario is vague, hypothetical,
       or rests on a file not in this tree — **keep it, and say so explicitly** in the Trigger
       field: `UNVERIFIABLE — rests on <file>, not readable in this tree`. Do NOT invent a
       trigger to fill the field. SCORE caps such findings at 50 by rule
       (`./correctness-scorer-prompt.md`), which is exactly what should happen to them — but
       only if you flag them honestly instead of dressing them up.

    ## Output

    ```
    ## FIND-B findings (normalized) — [N]
    [one block per finding, in the shape above]

    ## Dropped — not correctness — [M]
    - [title] (category)
    ```
```

---

## Pooling

Hand FIND-A's findings and B2's normalized findings to SCORE as **one flat list**. From SCORE's
point of view they are indistinguishable candidates — which is the point. The scorer sees the
claim, the location, and the code; it does not see which engine produced the finding, or what
that engine thought of it.

De-duplicate first: when both engines flag the same `file:line` with the same mechanism, keep one
candidate and note `origin: FIND-A + FIND-B`. **Agreement between two independent engines is
signal, but it is not a score** — the merged candidate still goes through SCORE like any other.
Do not promote it on agreement alone; that would smuggle the recall-biased verdict back in
through the side door.
