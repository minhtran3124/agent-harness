# Correctness Scorer Prompt Template

Use this template for the **SCORE** stage. Dispatch it once for each **deduplicated location**
that the FIND stage reports. The FIND stage is `./correctness-reviewer-prompt.md`, with six
parallel angles. Dispatch it before any fix work begins.

**Purpose:** The angles report a finding even when they are uncertain. Thus their list favors
recall. This stage gives each candidate a confidence score from 0 to 100. The fix loop acts only
on findings that meet the threshold (default **75**).

**One score per `(file, line)`, not one per angle.** The FIND stage deduplicates by location
before this stage runs. Thus a location that several angles reported arrives here as one
candidate.

**Keep each scorer's context independent.** Give each scorer the finding claim and the relevant
diff and files directly. Do not give it the finder's reasoning, transcript, or review output.
**Do not give it the list of angles that reported the finding.** A scorer that re-reads the
finder's logic confirms it instead of checking it.

**Agreement between angles is provenance, not evidence.** Do not raise a score because more than
one angle reported a location. Six angles that share a blind spot agree as readily as six angles
that share an insight. A fresh judgment from the code is what catches that. Record the reporting
angles in the finding's provenance. Never pass them to the scorer.

**Score in a fresh context, from the code alone.**
Resolve the `correctness_scorer` model stage through the runtime entry binding. Do not write a
vendor model label in this prompt. `model_stage` is not a Task-tool parameter. This stage's
rendered `agents/` definition already declares a `model:` value. Pass that value as the Task
tool's `model:` value.
The harness repo resolves that value at render time (`scripts/render_runtime_entry.py --runtime claude --model-stage correctness_scorer`).
Thus a consuming repo reads it from the agent file and does not derive it again.

```
Task tool (reviewer):
  description: "Correctness score for finding: <short claim>"
  subagent_type: reviewer
  # reviewer is a read-only agent (no Write/Edit/Agent): the harness enforces review independence, not this prompt.
  model_stage: correctness_scorer
  prompt: |
    You are a correctness scorer. You receive one candidate bug finding and the changed
    code. Your only job is to give the finding a confidence score from 0 to 100.

    ## Inputs

    - **Finding claim**: [one-line description of the alleged bug]
    - **Location**: [file:line]
    - **BASE_SHA**: [commit before the first task]
    - **HEAD_SHA**: [current commit after all tasks]
    - **Files to read**: [list the specific files mentioned in the finding]

    Read the diff (`git diff BASE_SHA..HEAD_SHA -- <file>`). Read the file itself at the
    stated location. Do not read the finder's report or reasoning. Judge from the code alone.

    ## Scoring rubric (use only these anchor scores)

    - **0** — False positive: the alleged bug does not exist, existed before this diff, or is
      on a line the diff did not modify.
    - **25** — Maybe real: the concern is plausible but unverified. To confirm it, you need a
      concrete triggering condition.
    - **50** — Real but minor or rare: the bug exists, but its impact is low or its triggering
      condition is unlikely in practice.
    - **75** — Highly confident: the bug is real and normal usage will hit it. You can trace a
      concrete triggering input.
    - **100** — Certain: reading the code confirms it. The incorrect behavior is unambiguous
      and directly in the diff.

    ## Score 0 when any of these apply

    - A wired linter would catch the bug before merge. CI runs only `shellcheck -S error`, over
      bash blocks in skill docs (harness repo only). No Python linter or type checker is wired.
      Thus do not score 0 on this basis for a Python lint-level or type-level defect.
    - An existing CI check or hook already catches it. An example is the risk corroboration in
      `hooks/commit-gate.sh` (declared lane against the staged diff). That hook runs targeted
      pytest only under the `strict` profile or `REQUIRE_APP_GATES=1`. Thus do not assume that
      it caught a bug that a test would detect.
    - **The diff did not modify the flagged line.** This includes every finding marked
      `unmodified-line`: code inside a function the diff changed, on a line the diff did not
      change. Score it 0 even when the bug is clearly real.

    ## What a score of 0 means (read this before you score an `unmodified-line` finding)

    A score of 0 does **not** mean that the finding is false. It does **not** discard the
    finding. It means only one thing: **the finding does not enter the fix loop.**

    Every finding that scores below the threshold is recorded as **advisory** in
    `specs/<slug>/SUMMARY.md`. In standalone use, it is reported inline instead. Each such
    finding is shown to the human. Nothing is dropped.

    Thus a 0 for an `unmodified-line` finding does not judge it untrue. It routes the finding
    to the human instead of to an automatic fix. The reason is that rewriting code that the
    author did not touch, on their feature branch, is not this pipeline's decision.

    Score it 0 and continue. Do not argue in your justification that it deserves a higher
    score. Describe the bug so that the human who reads the advisory list can act on it.

    **Case (2026-07-13, PR #51):** three real, reproducible aborts were found in the
    harness repo's `scripts/harness-status.sh`. They were on lines the diff never touched. All three
    scored 0 and stayed out of the fix loop. They went to the author, who fixed them
    separately. The rule worked as intended. This was not a false negative.

    ## Cap the score at 50 when the claim rests on code you cannot read

    This rule applies `not_observed != absent` (`rules/behavior.md` §1) to scoring. A
    finding's trigger can depend on a file, symbol, or convention that you **cannot read** in
    this tree. Examples are the model, the base class, the auth dependency, and the caller.
    For such a finding, the bug is **unknown, not confirmed**. Such a finding scores **50 at
    most**, however plausible the mechanism sounds.

    Score a finding `<= 50` when its own text admits uncertainty with a phrase such as these:

    - "cannot verify"
    - "not present in this tree"
    - "UNKNOWN"
    - "assuming X"
    - "cannot rule out"
    - "a reviewer with <file> should confirm"

    A finding that argues from the *shape* of the code, and not from a line you can quote, is
    a hypothesis. A hypothesis does not enter the fix loop.

    **Case (2026-07-13, `evals/skills/review-chain`):** an unfiltered high-recall engine
    asserted three defects: an IDOR on correct auth wiring, an unstable `ORDER BY`, and an
    unbounded read. Each rested on a file absent from the tree. Each was a false positive that
    the fixture had named in advance. The mechanism was real every time, but the *trigger*
    could not be verified. That is a 50, not a 75.

    ## Score confidence, not severity

    Score only how confident you are that the bug is real and that this diff introduced it.
    The finding already carries a severity (P0–P3). Do not reclassify it.

    ## Output format

    Return one JSON object per finding, with no prose outside the JSON:

    ```json
    {
      "location": "file:line",
      "score": <0|25|50|75|100>,
      "justification": "<one sentence — what you saw in the code that drove this score>"
    }
    ```

    Return nothing else: one JSON object. Do not put markdown fences around the object
    itself. The outer code block belongs to the template only.
```

## Threshold and routing

The default threshold is **75**. A finding with `score >= 75` goes to the fix loop (severity ×
Rule-class classification, then auto-fix or escalate). A finding with `score < 75` is recorded as
`advisory` in `specs/<slug>/SUMMARY.md`. It does not block shipping.

The threshold is adjustable. Raise it (for example to 90) when false positives are a known
problem. With the discrete anchors, any value above 75 admits only a 100. Lowering it below 75
changes nothing until it crosses 50. The floor of 60 below forbids a threshold that low.

**The threshold must never be 50 or below.** The unreadable-code rule above caps those findings
at exactly 50. Thus a threshold of 50 or lower lets every capped finding into the fix loop, and
that removes the rule. **The floor is 60.** To make a high-risk lane act on an unverifiable
finding, raise its score by *reading the missing file*. Do not lower the threshold for this.

## Dispatcher protocol

1. The controller collects the candidate findings from all six FIND angles. It
   **deduplicates them by `(file, line)`**: one candidate per location, with the reporting
   angles recorded as provenance.
2. For each location, dispatch one scorer (the `correctness_scorer` model stage, in an
   independent context). Pass the claim, the location, and the files to read. **Do not pass the
   provenance**: the scorer must not know how many angles agreed.
3. Dispatch scorers in parallel in one assistant message, at most 20 at a time. Send any
   remainder in a following batch.
4. Collect the scores and split the findings into `≥ threshold` (proceed) and `< threshold`
   (advisory).
5. Send only the findings at or above the threshold into the severity × Rule-class
   classification and the fix loop (`SKILL.md` → Pipeline, steps 5–6).
6. Record every below-threshold finding in `specs/<slug>/SUMMARY.md` under
   `### Advisory Findings`. This includes every `unmodified-line` finding. Such a finding scores
   0 by rule, so it is always advisory. Nothing is silently dropped.
