---
name: correctness-review
description: Run one adversarial correctness review over a diff — assumes ≥1 runtime bug exists and hunts for it (None/async/DB/auth/concurrency/contract breaks), independent of any plan or spec. Find→score→threshold(80)→classify→fix-loop. Invokable standalone on any diff, and called by subagent-driven-development as its final pre-ship gate. Not a style/cleanup pass; for that use /code-review.
---

# Adversarial Correctness Review

Run **one** adversarial correctness review over a diff and route every surviving finding to a
fix or a durable record. The pipeline is FIND → SCORE → THRESHOLD → classify → fix-loop, backed
by `./correctness-reviewer-prompt.md` (high-recall finder) and `./correctness-scorer-prompt.md`
(cheap-model scorer).

**Two entry points, one pipeline:**

- **Standalone** — `/correctness-review` on any diff, ad-hoc, outside the workflow gates. Use it
  on a branch before a PR, on uncommitted work, or on any range you name.
- **In-flow** — `subagent-driven-development` calls this as its always-on final pass after all
  tasks pass their spec + quality reviews, before `finishing-a-development-branch`.

**Why this stage exists.** Per-task spec and quality reviewers are anchored to the plan as the
oracle — spec review asks *"does it match the spec?"*, quality review asks *"is it clean?"*.
Neither asks *"even if the spec is right, does this code fail at runtime?"*. A bug that faithfully
implements a flawed spec passes both. This is the gap that lets real bugs survive to production
and get caught by external reviewers post-push.

## When to Use

- Before opening a PR or merging a branch — a final bug hunt over the whole change.
- After any implementation, when you want correctness coverage decoupled from the full workflow.
- Automatically, as the final gate inside `subagent-driven-development` (no manual call needed).

Not for style, naming, or maintainability — that is `/code-review`'s cleanup pass or the per-task
quality reviewer. This skill hunts **runtime bugs only**.

## Determine the diff range

The finder needs a `BASE_SHA..HEAD_SHA` range (and the list of touched files):

- **Standalone, branch vs main:** `BASE = git merge-base main HEAD`, `HEAD = HEAD`.
- **Standalone, uncommitted work:** review the working tree (`git diff` / `git diff --staged`);
  stage or stash as needed so the reviewer sees the intended change.
- **Standalone, explicit range:** the user names `BASE`/`HEAD` or a PR.
- **In-flow:** `BASE` = commit before task 1, `HEAD` = current commit after all tasks.

## Pipeline — FIND (6 angles) → dedup → SCORE → THRESHOLD(80) → classify → fix-loop

**What makes this pass different from the other reviewers:**

- **Ignores the plan.** Checks what the code does at runtime, not what someone intended.
- **Assumes a bug exists.** Looks for defects rather than confirming compliance.
- **Whole-diff.** Runs once over the entire change, so it catches integration bugs spanning
  several commits or tasks — invisible to any single per-task review.
- **Different model.** Dispatched with a different (ideally most capable) model than the one that
  wrote the code. A different model finds different bugs.

1. **FIND — six angles, in parallel** (`./correctness-reviewer-prompt.md`). Not one reviewer with
   a checklist: six subagents, each in its own context, each looking by a different **method**.
   Each returns at most 6 candidates, and every candidate must name a concrete trigger (the input
   or state that reaches the bug) and the wrong outcome it produces.

   | Angle | Method |
   |---|---|
   | **A** | Read each changed hunk, then the **whole enclosing function**. Bugs on unmodified lines inside a changed function are in scope, marked `unmodified-line`. |
   | **B** | **Removed-behavior auditor.** For every deleted or replaced line, state what it enforced, then find where the new code re-establishes it. If it does not, that is a finding. |
   | **C** | **Cross-file tracer.** Grep the callers and callees of every changed signature; check for a broken precondition, changed return shape, new exception, or new ordering requirement. |
   | **D** | **Stack defect classes.** The None/async/DB/auth/concurrency/contract checklist — adapted to whatever language the diff is actually in. |
   | **E** | **Altitude.** Where the code guards against failure, does the guard cover *every* way it can fail, or only the ones the author had in mind? |
   | **F** | **Compound read-back.** Read `docs/solutions/` and check the diff against the failures this repo has already paid for, by name. |

   Angles A and B are the two the old single-finder checklist could not reach, because they are not
   defect classes — they are procedures. That gap was not theoretical: the PR #51 review's most
   valuable finding sat entirely on lines the diff never modified.

2. **Dedup by `(file, line)`.** Several angles will land on the same location. Merge them into one
   candidate and record which angles reported it. **Agreement between angles is provenance, not
   evidence** — it does not raise the score, and the angle list is *not* passed to the scorer.
   Angles sharing a blind spot agree just as readily as angles sharing an insight.

3. **SCORE** (`./correctness-scorer-prompt.md`) — a cheap-model agent scores each deduplicated
   location 0–100 in independent context (no access to the finder's reasoning). One scorer per
   location; dispatch in parallel. Rubric: 0 = false positive, pre-existing, or not on a changed
   line · 25 = maybe real, unverified · 50 = real but minor or rare · 75 = highly confident ·
   100 = certain, confirmed by code. Score 0 automatically when `ruff-on-edit`,
   `commit-quality-gate`, or `risk-corroboration` would already catch it. **Cap at 50 any finding
   that rests on a file the reviewer could not read** — `not_observed != absent`.

   > **Why a precision gate, and why we did not adopt `/code-review`'s verifier.** The built-in
   > `/code-review` verifies its own findings with a `CONFIRMED / PLAUSIBLE / REFUTED` ladder that
   > is *recall*-biased by its own instruction ("PLAUSIBLE by default — do not refute for being
   > speculative"). In a tree where a dependency cannot be read, nothing is constructible, so
   > nothing gets refuted and every speculation survives. That is correct for a high-recall finder
   > and wrong for a gate. Measured on `benchmarks/review-chain` (2026-07-13): run without a
   > precision gate, it asserted three defects that the fixtures had each named **in advance** as
   > false positives. SCORE filters the opposite direction. It stays.

4. **THRESHOLD** — findings scoring below **80** do not enter the fix-loop. They are recorded as
   `advisory` in `specs/<slug>/SUMMARY.md` under `### Advisory Findings` (reported inline in
   standalone use with no slug). **Below-threshold does not mean discarded** — every
   `unmodified-line` finding scores 0 by rule and lands here, real and reported, simply not
   auto-fixed. Adjustable: raise it when false-positive noise is a known problem. **Never set it
   to 50 or below** — that would admit every unreadable-file finding the cap exists to hold back.
   Floor: 60.

5. **Two-axis classification.** Findings that survive the threshold carry two labels:

- **Severity** — `P0` (data loss / security / crash) · `P1` (wrong output / broken path) ·
  `P2` (degraded behavior, non-fatal) · `P3` (minor correctness issue)
- **Rule class** — per `.claude/rules/auto-correct-scope.md`: `Rule 1` (auto-fix obvious bug) ·
  `Rule 2` (auto-add missing standards) · `Rule 3` (auto-fix blocker) · `Rule 4` (STOP — needs
  architectural judgment)

6. **Residual gate + fix-loop.** See below.

## Fix routing by Rule class

- **Rule 1–3** → implementer auto-fixes (fresh dispatch) → re-review → repeat until ✅. Log each
  fix as a deviation in `SUMMARY.md` when a slug is in play.
- **Rule 4** → STOP immediately. Do not attempt a fix. Write the finding to
  `specs/<slug>/ESCALATIONS.md` (or surface it directly to the user in standalone use) before
  proceeding. The plan was wrong or underspecified; a human must narrow scope.

## Residual work gate

Before reporting done (in-flow: before handing off to `finishing-a-development-branch`), every
finding must be in one of two states: fixed (✅, with a commit sha) or durably recorded
(`SUMMARY.md` for Rule 1–3 carry-overs, `ESCALATIONS.md` for Rule 4 blocks; or surfaced inline in
standalone use). A finding with neither is a hard block — do not report success.

## Relationship to other review skills

- **`/code-review` (built-in):** a **sibling**, not a component. It reviews correctness *and*
  cleanup (reuse, simplification, efficiency, conventions) at several effort levels, plus a cloud
  `ultra` mode. Run it standalone for an ad-hoc sweep with no gates. It does not replace this
  skill and this skill does not invoke it.

  **What we measured, and what we took.** On `benchmarks/review-chain` (2026-07-13) we tested
  replacing this skill's finder with `/code-review`. It matched recall (3/3) but produced **3 hard
  false positives against a baseline of 0** — each one a false positive the fixture had named in
  advance — and cost 10–15× the tokens (`results/2026-07-13-code-review-swap.md`). **The swap was
  rejected.** A second stage that ran it as an additional engine (FIND-B) was also built, measured
  against its cost, and **deleted**: parallel angles inside our own finder buy the same diversity
  for roughly a tenth of the tokens.

  What we *did* take is its **structure**: reviewing by several independent angles rather than one
  checklist. Angles A (enclosing function), B (removed-behavior), C (cross-file), and E (altitude)
  all come from reading its source. Its recall-biased verdict ladder we deliberately did not take —
  see the SCORE callout above.
- **`/review-diff`:** visualizes what changed (C4 diagrams + walkthrough). Not a correctness pass.
- **`subagent-driven-development`:** calls this skill as its final adversarial gate. Invoking
  `/correctness-review` standalone runs the exact same pipeline without the rest of the workflow.

## Prompt Templates

- `./correctness-reviewer-prompt.md` — the FIND stage: six angles, dispatched in parallel over the whole diff.
- `./correctness-scorer-prompt.md` — the SCORE stage: one cheap-model scorer per deduplicated location (0–100, threshold 80).
