# Correctness Scorer Prompt Template

Use this template for the **SCORE** stage — dispatched once per candidate finding that
the adversarial correctness reviewer (`./correctness-reviewer-prompt.md`) emits, before
any fix work begins.

**Purpose:** Filter the high-recall finding list for precision. The finder is tuned to
FLAG when uncertain; this stage assigns a 0–100 confidence score to each candidate so
that the fix-loop only acts on findings that meet the threshold (default **80**).

**Independent context — critical.** Each scorer agent receives the finding claim and the
relevant diff/files directly. It does NOT receive the finder's reasoning chain, transcript,
or review output. Independence is the point: a scorer that re-reads the finder's logic
merely confirms it rather than checking it.

**Use a cheap, fast model.** Scoring is a classification task, not reasoning from scratch.
A lightweight model (e.g. claude-haiku or equivalent cheap/fast tier) reduces cost without
sacrificing filter accuracy at this stage.

```
Task tool (general-purpose):
  description: "Correctness score for finding: <short claim>"
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
    - The flagged line was NOT modified by the diff (pre-existing code the finder
      incidentally read).

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

The threshold is adjustable: set it lower (e.g. 60) on high-risk lanes where recall
matters more, or higher (e.g. 90) when false-positive noise is a known problem.

## Dispatcher protocol

1. The controller collects all candidate findings from the correctness reviewer.
2. For each finding, dispatch one scorer agent (cheap model, independent context).
3. Scorer agents for independent findings MAY run in parallel — dispatch in ONE assistant
   message.
4. Collect scores; split findings into `≥80` (proceed) and `<80` (advisory).
5. Proceed with only the `≥80` findings into the severity × Rule-class classification
   and fix-loop (`./correctness-reviewer-prompt.md` → Fix loop).
6. Record `<80` findings in `specs/<slug>/SUMMARY.md` under `### Advisory Findings`
   (not silently dropped).
