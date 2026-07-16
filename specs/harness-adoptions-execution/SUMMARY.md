# harness-adoptions-execution — Summary

Lane: normal
Confidence: high
Reason: Selected subset (tracks 1, 2, 6, 7) contains no hard-gate work — no settings.json, hooks/, or auth changes; Track 1 touches review skill prompts (normal), Tracks 2/6 are doc/rule edits (tiny), Track 7 adds new benchmark content only.
Flags: none
Affects: agents/, skills/correctness-review, skills/intent-review, rules/behavior.md, skills/README.md, benchmarks/ (new)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> create plan for all first. and I will make decision for next step

> now make the sub plan for 1, 2, 6, 7 now

(Selection refers to the decision matrix of `specs/harness-comparison-adoptions/PLAN.md`:
Track 1 = read-only review agents, Track 2 = `not_observed != absent` rule, Track 6 =
integration evidence-tier table, Track 7 = review-chain micro-benchmark. Upstream original
intent is recorded verbatim in `specs/harness-comparison-adoptions/SUMMARY.md`.)

## What changed

Execution sub-plan derived from the master plan for the four user-selected tracks.
Tracks 3, 4, 5, 8, 9 remain deferred in the master plan (status: proposed).

### Rationale

The user selected a subset; a dedicated spec keeps the executable plan clean (3 waves, no
deferred-task noise) while the master plan stays the umbrella record of all 9 ideas.

### Alternatives considered

- Mark unselected tracks "deferred" inside the master PLAN.md — rejected: executors key on
  specs/<slug>/PLAN.md running all tasks; a separate spec avoids accidental scope.

### Deviations

- none (Rule 1–3) — all 8 tasks implemented as specified; no auto-fixes required.

### Verify

Executed 2026-06-12 via /executing-plans on branch feat/enhance-skills. Every task `<verify>` exited 0.

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| 1.1 reviewer agent | `grep '^name: reviewer$' && '^tools: Glob, Grep, Read, Bash$' && ! '^tools:.*(Write\|Edit)' agents/reviewer.md` | 0 | tools whitelist excludes Write/Edit/Agent |
| 2.1 epistemic rule | `grep 'not_observed != absent' rules/behavior.md && diff -q rules/behavior.md .claude/rules/behavior.md` | 0 | both copies byte-identical |
| 6.1 evidence tiers | `grep 'Integration Evidence Tiers' skills/README.md && grep 'documented-only' && lint-doc-truth.sh` | 0 | doc-truth lint green |
| 7.1 benchmark scaffold | `test -f README.md && test -f results/template.md && grep 'caught / missed / false-positive'` | 0 | protocol + template present |
| 1.2 wire reviewer | `grep 'subagent_type: reviewer'` × 3 prompt files | 0 | all three dispatches named |
| 7.2 five fixtures | `ls -d fixtures/*/ == 5 && ls fixtures/*/truth.md == 5` | 0 | each has intent.md+diff.patch+truth.md |
| 2.2 enforce rule | `grep 'not_observed != absent'` × 2 reviewer prompts | 0 | absence-claim requirement present |
| 7.3 baseline | `test -f results/2026-06-baseline.md && grep -i 'catch rate'` | 0 | catch rate 5/5, 0 hard FP |
| Full suite | `bash scripts/run-tests.sh` | 0 | 85 passed, 1 skipped — ALL GREEN |

### Rollback

- `git revert <sha>` per task commit (all work is additive docs/prompts/fixtures). Wave shas: `9a0c95e`, `5b5d5b6`, `4d3a401`, `6333b70`.

### Harness-Delta

- **backlog** — `hooks/blast-radius-check.sh` does literal file-path matching against the plan
  `<files>` set, so it fired 10 false-positive warnings during Task 7.2 (the plan lists the
  directory `benchmarks/review-chain/fixtures/<name>/` but the writes target files *inside* it).
  Suggest the hook treat a plan `<files>` directory entry as covering its descendants. (→ `/compound`)
- **observation** — Track 1's `reviewer` agent type is not registered in a session that began
  before `agents/reviewer.md` existed, so the 7.3 baseline measured the upgraded prompts only,
  not the structural read-only wiring. Re-measure with `subagent_type: reviewer` after a session
  restart. Recorded in the baseline caveats.
