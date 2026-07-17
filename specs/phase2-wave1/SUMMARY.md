# phase2-wave1 — Summary

Lane: high-risk
Confidence: high
Reason: The diff will touch templates/ (TEST_MATRIX deletion) which is in ci-strict-gate's HARD_GATE_RE — the high-risk lane is mechanically forced, not judgment; direction is unambiguous (user-directed wave 1 of the verified Phase 2 review). deploy-harness.sh (consumer installer) is also trimmed, surgically.
Flags: high-blast (templates/ via strict gate)
Affects: templates/ (TEST_MATRIX contract removal), scripts/deploy-harness.sh (cosmetic), rules/orchestration.md + HARNESS.md + README.md (prose truth), scripts/context-monitor.py + REQ.md (dead)
Input-type: harness improvement

### Intent

"merge #77 first / next make deep research and review for docs/reviews/phase-2-deep-review-2026-07-16.md again. / start for wave1: design + plan"

## What changed

Planning phase (this entry precedes execution). PR #77 merged; all four Wave-1 claims **re-verified fresh** against the current tree (research-brief.md) — all held, plus one new lane-deciding discovery: `ci-strict-gate.sh` HARD_GATE_RE contains `^templates/`, so the TEST_MATRIX deletion forces this spec through the CI strict gate (high-risk SUMMARY + machine-verified proof). design.md fixes the four decisions (plain delete; delete + preserve questions; delete template + all 3 mandates keeping the `### Verify` clause; de-animate `step()` keeping its contract). PLAN.md (5 tasks / 2 waves) is the first production plan authored in the markdown task syntax — parsed to a correct At-a-glance by the render hook on save.

### Rationale

Wave 1 is scoped to exactly the items whose deletion requires no coordinated machine edits, so the riskiest thing in the diff is the installer trim — bounded by four existing test suites. Everything coupled (manifest, check_manifest §B, CLAUDE.md table) is deferred to Wave 2/3 by design.

### Alternatives considered

- Fold REQ.md into README: rejected — wrong audience; the questions only matter to the assessment doc.
- Keep TEST_MATRIX template "in case": rejected — 0/33 uptake + a consciously deferred activation is the strongest no-demand signal.
- Delete spinner's `step()` wholesale: rejected — callers + ERR trap depend on the wrapper; only the animation goes.

### Deviations

- none (pending execution)

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| plan parses (markdown syntax, 5 tasks / 2 waves) | `bash -c 'python3 skills/visual-planner/render_plan.py specs/phase2-wave1/PLAN.md /tmp/p2w1.html > /tmp/p2w1.out 2>&1 && grep -q "tasks=5 waves=2" /tmp/p2w1.out'` | 0 | dogfood of PR #69 syntax |
| doc-truth lint (pre-execution baseline) | `bash scripts/lint-doc-truth.sh` | 0 | clean |

(Execution rows appended by Task 2.1 — only pipe-free re-runnable commands, per the strict-gate contract.)

### Rollback

- Planning artifacts: revert the commit adding specs/phase2-wave1/.
- Execution (when run): `git revert` the wave commit — all four items restore cleanly from git history; no data/schema migration; deploy-harness change is cosmetic-only.

### Harness-Delta

- none (this wave exists BECAUSE of prior deltas; nothing new surfaced during planning)
