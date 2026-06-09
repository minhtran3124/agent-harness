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
Neither asks *"cho dù spec đúng, code này có chạy sai ở runtime không?"*. A bug that faithfully
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

## Pipeline — FIND → SCORE → THRESHOLD → D → E

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

1. **FIND** (`./correctness-reviewer-prompt.md`) — high-recall; flags every plausible candidate.
   The finder is deliberately biased toward false positives; it does not self-filter.
2. **SCORE** (`./correctness-scorer-prompt.md`) — a cheap-model agent scores each candidate
   0–100 in independent context (no access to the finder's reasoning). One scorer agent per
   finding; dispatch in parallel. Rubric: 0 = false positive / pre-existing / not on changed
   line · 25 = maybe real, unverified · 50 = real but minor or rare · 75 = highly confident ·
   100 = certain, confirmed by code. Score 0 automatically when `ruff-on-edit`,
   `commit-quality-gate`, or `risk-corroboration` would already catch it.
3. **THRESHOLD** — drop findings with `score < 80`. Record them as `advisory` in
   `specs/<slug>/SUMMARY.md` under `### Advisory Findings` when a slug is in play (not silently
   dropped, not escalated); in pure standalone use with no slug, report them inline as advisory.
   The threshold is adjustable (lower for high-risk lanes, higher when false-positive noise is a
   known problem); default is **80**.
4. **D — two-axis classification.** Findings that survive the threshold carry two labels:

- **Severity** — `P0` (data loss / security / crash) · `P1` (wrong output / broken path) ·
  `P2` (degraded behavior, non-fatal) · `P3` (minor correctness issue)
- **Rule class** — per `.claude/rules/auto-correct-scope.md`: `Rule 1` (auto-fix obvious bug) ·
  `Rule 2` (auto-add missing standards) · `Rule 3` (auto-fix blocker) · `Rule 4` (STOP — needs
  architectural judgment)

5. **E — residual gate + fix-loop.** See below.

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

- **`/code-review` (global):** generic correctness + reuse/simplification/efficiency cleanup with
  effort levels and a cloud `ultra` mode. `/correctness-review` is the repo-tuned bug-only pass
  (reads `docs/solutions/`, classifies by `auto-correct-scope.md` Rule class, threshold-80). They
  compound — run either or both before merge; neither replaces the other.
- **`/review-diff`:** visualizes what changed (C4 diagrams + walkthrough). Not a correctness pass.
- **`subagent-driven-development`:** calls this skill as its final adversarial gate. Invoking
  `/correctness-review` standalone runs the exact same pipeline without the rest of the workflow.

## Prompt Templates

- `./correctness-reviewer-prompt.md` — dispatch the adversarial correctness finder (once, whole diff).
- `./correctness-scorer-prompt.md` — dispatch the cheap-model scorer per candidate finding (SCORE stage, 0–100, threshold 80).
