# harness-comparison-adoptions — Summary

Lane: normal
Confidence: high
Reason: Plan-only session (no code changed yet); the plan spans 9 independent tracks with per-track lanes — track 5 (protected-paths hook + settings.json) is high-risk and gated on human approval inside the plan.
Flags: high-blast file (settings.json, hooks/*) — track 5 only; none for tracks 1–4, 6–9
Affects: skills/correctness-review, skills/intent-review, rules/, hooks/, settings.json, benchmarks/ (new)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> make the deep research for repo https://github.com/Chachamaru127/claude-code-harness/tree/main
> and create the document report wiht
> - what thing they do in the best
> - what thing we are doing well
> - what thing we can learn from this repo
> - what thing we can get idea and apply for our project

> make vietnamese version too

> create plan for all first. and I will make decision for next step

## What changed

Research report written (`docs/research-claude-code-harness-comparison.md` + `.vi.md`).
This spec holds the decision-ready PLAN.md covering all 9 adoption ideas from that report,
structured as independent tracks (1–9) so the user can greenlight a subset.

### Rationale

The user wants to choose which ideas to execute before any implementation starts, so the
plan is organized per-idea with lane, effort, conflicts, and a decision matrix — not as a
single monolithic execution sequence.

### Alternatives considered

- One plan per idea (9 specs) — rejected: the user asked for "all first" in one place to compare and decide.
- Plan only the quick wins — rejected: explicit request was a plan for all ideas.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Plan format | `python3 scripts/check_plan_format.py specs/harness-comparison-adoptions/PLAN.md` | — | run after PLAN.md is written |

### Rollback

- `git revert <sha>` (docs + spec files only at this stage)

### Harness-Delta

- none
