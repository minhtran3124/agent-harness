# Correctness Scorer Prompt Template

Use this template for the **SCORE** stage — dispatched once per **deduplicated location**
emitted by the FIND stage (`./correctness-reviewer-prompt.md`, six parallel angles), before
any fix work begins.

**Purpose:** Filter the high-recall finding list for precision. The angles are tuned to report
when uncertain; this stage assigns a 0–100 confidence score to each candidate so that the
fix-loop only acts on findings that meet the threshold (default **80**).

**One score per `(file, line)`, not one per angle.** The FIND stage deduplicates by location
before this stage runs. When several angles reported the same location, it arrives here as a
single candidate.

**Independent context — critical.** Each scorer agent receives the finding claim and the
relevant diff/files directly. It does NOT receive the finder's reasoning chain, transcript, or
review output — **and it does not receive the list of which angles reported the finding.**
Independence is the point: a scorer that re-reads the finder's logic merely confirms it rather
than checking it.

**Agreement between angles is provenance, not evidence.** Do not raise a score because more than
one angle reported a location. Six angles sharing a blind spot agree with each other just as
readily as six angles sharing an insight — that is precisely what a fresh, code-only judgment is
here to catch. Record which angles reported it in the finding's provenance; never feed it to the
scorer.

**Use a cheap, fast model.** Scoring is a classification task, not reasoning from scratch.
A lightweight model (e.g. claude-haiku or equivalent cheap/fast tier) reduces cost without
sacrificing filter accuracy at this stage.

```
Task tool (reviewer):
  description: "Correctness score for finding: <short claim>"
  subagent_type: reviewer
  # reviewer is a read-only agent (no Write/Edit/Agent) — review independence is enforced structurally, not by instruction.
  model: <cheap/fast model — e.g. claude-haiku or equivalent lightweight tier>
  prompt: |
    You are a correctness scorer. You receive ONE candidate bug finding and the changed
    code. Your ONLY job is to assign it a confidence score 0–100.

    ## Inputs

    - **Finding claim**: [one-line description of the alleged bug]
    - **Location**: [file:line]
    - **BASE_SHA**: [commit before the first task]
    - **HEAD_SHA**: [current commit after all tasks]
    - **Files to read**: [list the specific files mentioned in the finding]

    Read the diff (`git diff BASE_SHA..HEAD_SHA -- <file>`) and the actual file at the
    stated location. Do NOT read the finder's report or reasoning — form your own judgment
    from the code alone.

    ## Scoring rubric (use exactly these anchor points)

    - **0** — False positive: the alleged bug does not exist, is pre-existing (not
      introduced by this diff), or is on a line the diff did not modify.
    - **25** — Maybe real: the concern is plausible but unverified; would need a concrete
      triggering condition to confirm.
    - **50** — Real but minor or rare: the bug exists but its impact is low or its trigger
      condition is unlikely in practice.
    - **75** — Highly confident: the bug is real and will be hit in normal usage; a
      concrete triggering input is traceable.
    - **100** — Certain: confirmed by reading the code; the incorrect behavior is
      unambiguous and directly in the diff.

    ## Score 0 automatically when ANY of these apply

    - A linter or typechecker (`ruff`, `mypy`) would catch this before merge.
    - An existing CI check or project hook already catches it:
      `ruff-on-edit` (fires on every Edit/Write), `commit-quality-gate` (runs ruff +
      pytest on commit), or `risk-corroboration` (checks lane vs staged diff).
    - **The flagged line was NOT modified by the diff.** This includes any finding marked
      `unmodified-line` — code inside a function the diff changed, but on a line it did not
      change. Score it 0 even when the bug is unmistakably real.

    ## What a score of 0 means — read this before scoring an `unmodified-line` finding

    A score of 0 does **not** mean the finding is false, and it does **not** mean the finding is
    discarded. It means exactly one thing: **the finding does not enter the fix loop.**

    Every finding scoring below the threshold is recorded as **advisory** in
    `specs/<slug>/SUMMARY.md` (or reported inline in standalone use) and surfaced to the human.
    Nothing is dropped.

    So when you score an `unmodified-line` finding 0, you are not judging it untrue. You are
    routing it: report to the human, do not auto-fix. The reason is scope discipline —
    automatically rewriting code the author did not touch, on their feature branch, is not this
    pipeline's decision to make.

    Score it 0 and move on. Do not argue in your justification that it deserves more; say what
    the bug is, so the human reading the advisory list can act on it.

    **Worked example (2026-07-13, PR #51).** A review of a change to one section of
    `scripts/harness-status.sh` surfaced three real, reproducible aborts in *other* sections of
    the same file — every one on a line the diff never touched. All three were genuine: the
    script died on a fresh clone. All three were correctly scored 0, kept out of the fix loop,
    and reported to the author, who fixed them deliberately in a separate commit. That is the
    rule working, not the rule failing.

    ## Cap the score at 50 when the claim rests on code you cannot read

    `not_observed != absent` (`rules/behavior.md` §1) applied to scoring. If the finding's
    trigger depends on a file, symbol, or convention that is **not readable** from this tree
    — the model, the base class, the auth dependency, the caller — then the bug is
    **unknown, not confirmed**, and it scores **50 at most**, no matter how plausible the
    mechanism sounds.

    Score it `<= 50` when the finding's own text contains an admission like "cannot verify",
    "not present in this tree", "UNKNOWN", "assuming X", "cannot rule out", or "a reviewer
    with <file> should confirm" — a finding that argues from the *shape* of the code rather
    than from a line you can quote is a hypothesis, and hypotheses do not enter the fix-loop.

    This rule is load-bearing: on `benchmarks/review-chain` (2026-07-13) an unfiltered
    high-recall engine asserted three defects — an IDOR on correct auth wiring, an unstable
    `ORDER BY`, an unbounded read — each resting on a file absent from the tree, and each was
    a false positive the fixture had named in advance. The mechanism was real in every case;
    the *trigger* was unverifiable. That is exactly a 50, not an 80.

    ## Scoring is independent of severity

    Score only how confident you are the bug is real and introduced by this diff.
    Severity (P0–P3) is already on the finding; do not re-classify it here.

    ## Output format

    Return one JSON object per finding (no prose outside the JSON):

    ```json
    {
      "location": "file:line",
      "score": <0|25|50|75|100>,
      "justification": "<one sentence — what you saw in the code that drove this score>"
    }
    ```

    Do not return anything else. One JSON object. No markdown fences around the object
    itself (the outer code block is for the template only).
```

## Threshold and routing

The default threshold is **80**. A finding with `score >= 80` proceeds to the fix-loop
(severity × Rule-class classification → auto-fix or escalate). A finding with `score < 80`
is recorded as `advisory` in `specs/<slug>/SUMMARY.md` and does not block shipping.

The threshold is adjustable: set it lower (e.g. 60) on high-risk lanes where recall matters
more, or higher (e.g. 90) when false-positive noise is a known problem.

**The threshold must never be set to 50 or below.** The unreadable-file rule above caps such
findings at exactly 50. A threshold of 50 or lower therefore admits every capped finding into the
fix-loop, which removes the rule entirely — the opposite of what lowering the threshold on a
high-risk lane is meant to achieve. **The floor is 60.** If you want a high-risk lane to act on
unverifiable findings, raise them by *reading the missing file*, not by lowering the gate that
exists because it could not be read.

## Dispatcher protocol

1. The controller collects the candidate findings from all six FIND angles and **deduplicates
   them by `(file, line)`** — one candidate per location, with the reporting angles recorded as
   provenance.
2. For each deduplicated location, dispatch one scorer agent (cheap model, independent context).
   Pass the claim, the location, and the files to read. **Do not pass the provenance** — the
   scorer must not know how many angles agreed.
3. Scorer agents MAY run in parallel — dispatch in ONE assistant message.
4. Collect scores; split findings into `≥ threshold` (proceed) and `< threshold` (advisory).
5. Proceed with only the surviving findings into the severity × Rule-class classification and
   fix-loop (`./correctness-reviewer-prompt.md` → Fix loop).
6. Record every below-threshold finding in `specs/<slug>/SUMMARY.md` under
   `### Advisory Findings`. This includes all `unmodified-line` findings, which score 0 by rule
   and are therefore always advisory. Nothing is silently dropped.
