# correctness-review-angles — Summary

Lane: high-risk
Confidence: high
Reason: No diff-detectable hard gate fires, but this rewrites the always-on correctness gate that guards every other change in the repo — a silent recall regression here degrades every future review and would not surface on its own. Ceremony is set by that blast radius, not by a gate match.
Flags: high-blast (core skill engine — judgment, not manifest-detectable), existing-behavior (rewrites a shipped reviewer), weak-proof (the only evidence is an n=1 manual benchmark)
Affects: skills/correctness-review (the finder + scorer prompts), skills/subagent-driven-development (calls it), skills/README.md (inventory)
Input-type: harness improvement

### Intent

The user's request, verbatim, across the scope-deciding turns:

> "Now i have idea, we can review skill "code-review" from CC. After that, review our skill "/correctness-review" and improve it. Make the deep research to improve the our skill for correctness-review, learn the best thing from CC skill.
> Make it short, clear and clean. Adopt the best thing CC skill have.
>
> Give me the design + brainstorming before do anything"

Then, deciding the three open questions from the design brief plus one constraint:

> "1. giu 0
> 2. xoa FIND-B
> 3. benchmakr nam trong change nay
> 4. dam bao viec update correctness-reviewer-prompt.md ro rang, sach se, ngữ nghĩa đầy đủ và trong sáng, ko chứa ý ẩn dụ"

(1. keep SCORE=0 for unmodified lines. 2. delete FIND-B. 3. the benchmark is part of this change.
4. the rewritten finder prompt must be clear, clean, semantically complete and transparent, with
no metaphorical or implicit meaning.)

## What changed

Not yet implemented — plan only. Proposed: replace `/correctness-review`'s single checklist-driven
finder with six parallel angles (diff scan + enclosing function; removed-behavior auditor;
cross-file tracer; stack-pitfall list; altitude/boundary; compound read-back), each capped at 6
candidates and each requiring a concrete trigger. Delete FIND-B entirely. Dedup candidates by
(file, line) before SCORE. Measure the result on all 5 benchmark fixtures before merge.

### Rationale

Two measured facts drove this. **(a)** Claude Code's `/code-review`, read from its own source,
finds bugs by running several independent finders with different *methods*, not one finder with a
longer list. Two of its methods are absent from our checklist because they are procedures, not bug
classes: read the enclosing function of a changed hunk, and audit what every deleted line used to
enforce. The blind spot is real and self-demonstrated — the PR #51 review's most valuable finding
(three live aborts in `harness-status.sh`) sat entirely on unmodified lines, which our finder has
no instruction to reach. **(b)** FIND-B was justified as "ensemble diversity: different angles,
different blind spots"; parallel angles buy exactly that inside our own finder at roughly a tenth
the cost, with no output adapter and no recall-biased verdict to quarantine. Its only remaining
justification is model-level diversity, which is unmeasured — and we do not ship unmeasured stages.

We deliberately did **not** adopt `/code-review`'s verdict ladder (recall-biased by its own label —
it is the mechanism behind the 3 false positives the benchmark caught) or its cleanup angles (out
of this skill's lane).

### Alternatives considered

- **Keep FIND-B alongside the angles.** Rejected: once angles supply angle-diversity, FIND-B's
  marginal value is model-diversity alone, which no run has measured. Keeping a 10–15× stage on an
  unmeasured hypothesis is what this branch's own benchmark argued against.
- **Widen SCORE to accept unmodified lines (score >0), so pre-existing bugs enter the fix-loop.**
  Rejected by the user (decision 1). Auto-fixing untouched code on a feature branch violates
  surgical-change discipline (`rules/behavior.md` §3). The findings are surfaced as *advisory*
  instead — reported, never auto-fixed. PR #51's review is the worked example of that being the
  right call.
- **Replace SCORE with `/code-review`'s CONFIRMED/PLAUSIBLE/REFUTED verifier.** Rejected on
  evidence: it is recall-biased by design, so in a tree where a dependency cannot be read nothing
  gets refuted. Measured at 3 hard false positives against a baseline of 0.
- **Ship the rewrite and benchmark it afterwards.** Rejected by the user (decision 3), and
  correctly — an unmeasured rewrite of the review gate is the exact thing this branch spent a
  benchmark rejecting.

### Deviations

- none (not yet executed)

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| _pending_ | `bash scripts/run-tests.sh` | — | doc-truth lint catches dangling FIND-B path refs |
| _pending_ | benchmark, 5 fixtures, manual protocol | — | recall must not regress vs `results/2026-06-baseline.md`; a regression is a hard stop, not a re-run |

### Rollback

- Revert the whole change: `git revert <sha>` (each wave commits separately; revert in reverse order)
- The finder and scorer prompts are plain markdown with no runtime state — reverting the commits
  fully restores the prior reviewer. No migration, no persisted artifact to unwind.
- The benchmark results file is an append-only historical record; leave it in place even on revert
  (a rejected experiment that stays recorded is the point of the benchmark).

### Harness-Delta

- backlog → `/compound`: the benchmark protocol's "one scored run, do not re-run until it passes"
  rule collided with wanting to iterate on the prompt. That tension is real and worth writing down —
  it is what makes an n=1 benchmark honest and also what makes it expensive to act on.
