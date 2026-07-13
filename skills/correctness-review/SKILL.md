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

## Pipeline — FIND (A [+B]) → SCORE → THRESHOLD → classify → fix-loop

**Step 0 — compound read-back.** Before scanning the diff, read
`docs/solutions/critical-patterns.md` and all `failure`-track entries in `docs/solutions/` when
present. Each past bug becomes a named check — this closes the compound loop at review time, so a
pattern the team already paid to learn cannot slip through again. Degrade gracefully: if
`docs/solutions/` is absent or empty, skip this step and proceed.

**What makes the finder different:**

- **Ignores the plan.** Validates against actual runtime behavior, not stated intent.
- **Adversarial.** Assumes ≥1 bug exists and hunts specific bug classes (None/async/DB/auth/
  concurrency/contract breaks) rather than confirming compliance.
- **Whole-diff.** Runs once over the full change, so it catches integration bugs that span
  multiple commits/tasks — invisible to any single per-task review.
- **Different model.** Dispatch with a different (ideally most capable) model than whoever wrote
  the code, for ensemble diversity.

1. **FIND-A — always** (`./correctness-reviewer-prompt.md`) — high-recall; flags every plausible
   candidate. Deliberately biased toward false positives; it does not self-filter. Includes the
   **Altitude** pass (is the fix deep enough, or a bandaid?).
2. **FIND-B — high-risk lane only, or on request: a second, independent engine**
   (`./find-b-prompt.md` — dispatch template + output adapter; read it before wiring this).
   Also run the built-in `/code-review` (`high`; `xhigh` when the diff is large) over the same
   range, **normalize** its findings into FIND-A's report shape, and **pool** them before scoring.
   It is not a replacement for FIND-A — it is ensemble diversity: a different engine, different
   angles (removed-behavior auditor, cross-file tracer, conventions-from-CLAUDE.md), different
   blind spots. Skip it on `tiny` and default `normal` lanes: it costs roughly **10–15× the
   tokens** of FIND-A for the same measured recall
   (`benchmarks/review-chain/results/2026-07-13-code-review-swap.md`), so it buys coverage, not
   correctness, and only a high-risk diff is worth that.

   > **The controller runs this one itself.** FIND-A and SCORE dispatch `subagent_type: reviewer`,
   > which is read-only by construction (`agents/reviewer.md`: `Glob, Grep, Read, Bash` — no
   > `Write`/`Edit`/`Agent`). It has no tool that can invoke a skill, and `/code-review` is a
   > skill, not an executable — so no subagent can run FIND-B. The session running
   > `/correctness-review` invokes it directly, then delegates the normalization. Never pass
   > `--fix` (it would mutate the code under review and bypass SCORE), `--comment`, or `ultra`.

   > **Where the lane comes from.** In-flow, the caller passes it. Standalone with a slug, read
   > `Lane:` from `specs/<slug>/SUMMARY.md`. Standalone with **no slug there is no lane** — so
   > FIND-B is **skipped by default** and the skip is stated, not silent. `not_observed != absent`:
   > an unknown lane is not a high-risk lane, and silently spending 10–15× on an ad-hoc review is
   > the wrong failure mode. `--find-b` forces it on.

3. **SCORE** (`./correctness-scorer-prompt.md`) — a cheap-model agent scores each **pooled**
   candidate 0–100 in independent context (no access to either finder's reasoning). One scorer
   agent per finding; dispatch in parallel. Rubric: 0 = false positive / pre-existing / not on
   changed line · 25 = maybe real, unverified · 50 = real but minor or rare · 75 = highly
   confident · 100 = certain, confirmed by code. Score 0 automatically when `ruff-on-edit`,
   `commit-quality-gate`, or `risk-corroboration` would already catch it. **Cap at 50 any finding
   that rests on a file the reviewer could not read** — `not_observed != absent`.

   **Never pass FIND-B's verdict into the scorer.** `/code-review` labels its findings
   `CONFIRMED` / `PLAUSIBLE`, and that ladder is *recall*-biased by design — importing it as
   confidence is exactly how the three benchmark false positives would reach the fix-loop. The
   verdict travels as provenance only (`origin:`); the scorer re-derives confidence from the code,
   blind to which engine found it. Same rule for cross-engine agreement: two engines flagging one
   line is signal, **not** a score, and the merged candidate is still scored like any other.

   > **Why SCORE survives even though `/code-review` has its own verifier.** They filter opposite
   > directions and are not substitutes. `/code-review`'s verifier is *recall*-biased by design
   > ("PLAUSIBLE by default — do not refute for being speculative"), so in a tree where a
   > dependency cannot be read, nothing gets refuted and every speculation survives. SCORE is the
   > *precision* gate. Measured: with SCORE removed, `/code-review` asserted three defects that
   > the benchmark fixtures had each named in advance as false positives (same results file).
   > Deleting SCORE imports those straight into the fix-loop.
4. **THRESHOLD** — drop findings with `score < 80`. Record them as `advisory` in
   `specs/<slug>/SUMMARY.md` under `### Advisory Findings` when a slug is in play (not silently
   dropped, not escalated); in pure standalone use with no slug, report them inline as advisory.
   The threshold is adjustable (lower for high-risk lanes, higher when false-positive noise is a
   known problem); default is **80**.
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

- **`/code-review` (built-in):** generic correctness + reuse/simplification/efficiency/altitude
  cleanup, with effort levels and a cloud `ultra` mode. As of 2026-07-13 it is **not a sibling but
  a component**: `/correctness-review` invokes it as FIND-B, the second engine on high-risk lanes,
  and pools its findings into the same SCORE → THRESHOLD → classify path. It remains usable
  standalone for an ad-hoc cleanup-and-correctness sweep with no gates.

  Measured on `benchmarks/review-chain` (2026-07-13): as a *replacement* for FIND-A it matched
  recall (3/3) but produced **3 hard false positives against 0**, and cost 10–15× the tokens —
  so it augments FIND-A, it does not replace it. What it uniquely contributes is the **altitude**
  lens, which caught a real boundary defect in this repo that two rounds of human fixes and the
  harness's own per-line reviewer all missed. That lens has since been ported into FIND-A
  (`./correctness-reviewer-prompt.md` → Altitude), so the cheap path gets it too.
- **`/review-diff`:** visualizes what changed (C4 diagrams + walkthrough). Not a correctness pass.
- **`subagent-driven-development`:** calls this skill as its final adversarial gate. Invoking
  `/correctness-review` standalone runs the exact same pipeline without the rest of the workflow.

## Prompt Templates

- `./correctness-reviewer-prompt.md` — dispatch the adversarial correctness finder FIND-A (once, whole diff).
- `./find-b-prompt.md` — FIND-B (high-risk only): how the controller invokes `/code-review`, and the adapter that normalizes its output into FIND-A's shape before pooling.
- `./correctness-scorer-prompt.md` — dispatch the cheap-model scorer per candidate finding (SCORE stage, 0–100, threshold 80).
