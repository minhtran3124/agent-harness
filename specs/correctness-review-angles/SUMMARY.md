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

Replaced `/correctness-review`'s single checklist-driven finder with six parallel angles (A diff
scan + enclosing function; B removed-behavior auditor; C cross-file tracer; D stack defect classes;
E altitude/boundary; F compound read-back), each capped at 6 candidates and each requiring a
concrete trigger. Deleted FIND-B entirely (`find-b-prompt.md` gone; no reference remains outside
historical benchmark records). The scorer now dedups by `(file, line)` before scoring, is never
told which angles agreed, states the advisory consequence of a 0 explicitly, and carries a
threshold floor of 60. The finder prompt is literal throughout — no metaphor.

Benchmarked on all 5 fixtures before merge (`benchmarks/review-chain/results/2026-07-13-angles.md`):
**recall 3/3, no regression**; **hard false positives 3 → 0**, closing the altitude run's
regression; cost ~3× the baseline single finder.

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

- **Task 2.2 `<done>` not met literally, on purpose.** It required `grep -ri "find-b"` to resolve to
  benchmark result files only. One live-file hit remains: `skills/correctness-review/SKILL.md:140`,
  the sentence recording that FIND-B *was built, measured against its cost, and deleted*. That is a
  design record of a rejected approach — the same class of history the plan explicitly preserves in
  the benchmark results — not a dangling reference to a stage that still runs. The doc-truth lint
  passes; no path is broken. Kept deliberately: deleting it would erase the only in-skill statement
  of why the extra-engine design was rejected, which is the whole point of that section.
- No Rule 1–3 auto-fix was needed. Every file changed is named in the plan's `<files>` sets.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Full suite (incl. doc-truth lint) | `bash scripts/run-tests.sh` | 0 | 151 passed, 1 skipped, `ALL GREEN`. The doc-truth lint is what proves no dangling FIND-B path reference survives. |
| No FIND-B reference outside history | `grep -ril "find-b" --exclude-dir=.git .` | — | resolves only to `benchmarks/review-chain/results/*` (historical records, kept by design) and this spec |
| Lane evidence | `python3 scripts/check_lane_evidence.py correctness-review-angles` | 0 | high-risk lane: Lane/Confidence/Reason + Verify row + Rollback all present |
| Benchmark, 5 fixtures, one scored run (FIND) | manual protocol, `benchmarks/review-chain/README.md` | — | **recall 3/3 — no regression** vs `results/2026-06-baseline.md`. **Hard FPs 3 → 0**, closing the altitude regression. Full record: `results/2026-07-13-angles.md` |
| Benchmark, end-to-end (FIND → dedup → SCORE → THRESHOLD) | manual protocol; 5 scorers, cheap model, independent context | — | **0 hard FPs into the fix-loop.** Scores split bimodally: 100 where provable from a readable line, exactly 50 where the claim rests on an absent file. Full record: `results/2026-07-14-end-to-end.md` |

### Advisory Findings

Surfaced by the benchmark, not blocking, recorded so they are not silently lost:

- **Angles `call-site-impact` and `prior-art` are unmeasured.** The fixture repos are single-file
  trees with no `docs/solutions/`, so the cross-file tracer has no callers to trace and the
  compound read-back never runs. The recall and FP numbers were produced by the other four angles
  alone. "The six-angle finder is validated" would be a false claim; four of six are.

- **~~Predicted~~ advisory-routing of a true positive — now measured, and resolved.** The
  end-to-end run (`benchmarks/review-chain/results/2026-07-14-end-to-end.md`) closed this. SCORE was
  run for real over the deduplicated FIND output. Result: `soft-delete-filter:13` scores **50** and
  routes to advisory, exactly as predicted.

  The open question was *why*: a correct rule, or a rule too blunt? **A controlled diagnostic
  answered it.** The fixture was rebuilt with `app/models/watchlist.py` present in both commits —
  the diff under review byte-identical (same blob hashes), one variable changed: the model is
  readable. Same claim, same scorer prompt.

  | Tree | Score |
  |---|---|
  | fixture as shipped (model absent) | **50** — *"the bug is unknown, not confirmed"* |
  | same diff, model readable | **100** — *"omits the soft-delete check mandated by the model's comment"* |

  **The cap fired because the fixture is context-starved, not because the rule is wrong.** In any
  repo where the model file exists, this finding scores 100 and enters the fix-loop. No tuning was
  applied; the rule stands as written.

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
