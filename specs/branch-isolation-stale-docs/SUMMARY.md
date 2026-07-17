# branch-isolation-stale-docs — Summary

Lane: high-risk
Confidence: high
Reason: Diff edits settings.json — a high-blast/hard-gate path (ci-strict-gate HARD_GATE_RE + risk-corroboration high-blast category force high-risk mechanically). Content change is doc-truth only; direction unambiguous (fixes claims that contradict the shipped hook).
Flags: high-blast (settings.json)
Affects: settings.json (statusMessage text only), CLAUDE.md hook table, 3 skill docs — all describing branch-isolation-guard's condition
Input-type: harness improvement

### Intent

"do the doc-stale follow-up" — the deep review (docs/reviews/phase-2-deep-review-2026-07-16.md) flagged CLAUDE.md:54 + settings.json statusMessage as still describing branch-isolation-guard's removed active-plan condition.

## What changed

branch-isolation-guard.sh blocks code edits on a shared branch **regardless of plan state** (the active-PLAN condition was removed to close the tiny-lane-writes-to-main hole; specs/ stays exempt). Five docs still claimed it only fires "while a plan is `status: active`": CLAUDE.md:54, settings.json:35 statusMessage (the 2 the review named), plus 3 more found by grepping — executing-plans/SKILL.md:53, writing-plans/SKILL.md:155, subagent-driven-development/SKILL.md:54. All corrected to "regardless of plan state". writing-plans additionally carried a now-false "(Tiny-lane in-place edits with no plan are exempt by design.)" — rewritten to the true exemption (only specs/ bookkeeping).

### Rationale

A guard whose docs describe a weaker trigger than the code teaches agents to expect a hole that no longer exists — and the writing-plans tiny-lane claim actively told agents they could edit main without a branch, which the hook now denies. Grepping beyond the 2 review-named sites caught 3 the review missed (verify-before-claiming-complete).

### Alternatives considered

- Fix only the 2 sites the review named: rejected — the 3 skill-doc copies carry the identical false claim; leaving them keeps the contradiction the doc-truth culture exists to prevent.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| no stale active-plan claim survives | `bash -c '! grep -rq "w/ active plan" settings.json && ! grep -rq "once a plan is .status: active." skills/ && ! grep -rq "while a plan is .status: active." CLAUDE.md'` | 0 | all 5 sites |
| settings.json valid JSON | `python3 -c "import json; json.load(open('settings.json'))"` | 0 | statusMessage edit didn't break parse |
| doc-truth lint (hook table vs settings) | `bash scripts/lint-doc-truth.sh` | 0 | clean |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- `git revert <commit>` — text-only; no behavior change to any hook/script.

### Harness-Delta

- The deep review named 2 stale sites; 3 more identical copies existed in skill docs. Duplicated claims about one hook across 5 files is the same "one canonical home per fact" pattern issue #67 Phase 3 targets — a future consolidation could point all skill docs at the CLAUDE.md hook table instead of restating it.
