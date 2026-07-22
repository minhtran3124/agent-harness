# phase2-wave1 — Summary

Lane: high-risk
Confidence: high
Reason: The diff will touch templates/ (TEST_MATRIX deletion) which is in ci-strict-gate's HARD_GATE_RE — the high-risk lane is mechanically forced, not judgment; direction is unambiguous (user-directed wave 1 of the verified Phase 2 review). deploy-harness.sh (consumer installer) is also trimmed, surgically.
Flags: high-blast (templates/ via strict gate)
Affects: templates/ (TEST_MATRIX contract removal), scripts/deploy-harness.sh (cosmetic), rules/orchestration.md + HARNESS.md + README.md (prose truth), scripts/context-monitor.py + REQ.md (dead)
Input-type: harness improvement

### Intent

"merge #77 first / next make deep research and review for docs/research/harness-review-improvements/reviews/phase-2-deep-review-2026-07-16.md again. / start for wave1: design + plan"

## What changed

Planning phase (this entry precedes execution). PR #77 merged; all four Wave-1 claims **re-verified fresh** against the current tree (research-brief.md) — all held, plus one new lane-deciding discovery: `ci-strict-gate.sh` HARD_GATE_RE contains `^templates/`, so the TEST_MATRIX deletion forces this spec through the CI strict gate (high-risk SUMMARY + machine-verified proof). design.md fixes the four decisions (plain delete; delete + preserve questions; delete template + all 3 mandates keeping the `### Verify` clause; de-animate `step()` keeping its contract). PLAN.md (5 tasks / 2 waves) is the first production plan authored in the markdown task syntax — parsed to a correct At-a-glance by the render hook on save.

### Rationale

Wave 1 is scoped to exactly the items whose deletion requires no coordinated machine edits, so the riskiest thing in the diff is the installer trim — bounded by four existing test suites. Everything coupled (manifest, check_manifest §B, CLAUDE.md table) is deferred to Wave 2/3 by design.

### Alternatives considered

- Fold REQ.md into README: rejected — wrong audience; the questions only matter to the assessment doc.
- Keep TEST_MATRIX template "in case": rejected — 0/33 uptake + a consciously deferred activation is the strongest no-demand signal.
- Delete spinner's `step()` wholesale: rejected — callers + ERR trap depend on the wrapper; only the animation goes.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| plan parses (markdown syntax, 5 tasks / 2 waves) | `bash -c 'python3 skills/visual-planner/render_plan.py specs/phase2-wave1/PLAN.md /tmp/p2w1.html > /tmp/p2w1.out 2>&1 && grep -q "tasks=5 waves=2" /tmp/p2w1.out'` | 0 | dogfood of PR #69 syntax |
| 1.1 context-monitor gone, zero refs | `bash -c 'test ! -f scripts/context-monitor.py && ! grep -rq "context-monitor" scripts/ hooks/ skills/ rules/ templates/ tests/ settings.json harness-manifest.json'` | 0 | |
| 1.2 REQ.md gone, questions preserved | `bash -c 'test ! -f REQ.md && grep -q "Source questions" docs/research/harness-review-improvements/research-harness-req-assessment.md'` | 0 | |
| 1.3 TEST_MATRIX template + mandates gone | `bash -c 'test ! -f templates/TEST_MATRIX.template.md && ! grep -rq "TEST_MATRIX" README.md HARNESS.md rules/ templates/ skills/ scripts/ tests/'` | 0 | 3 prose edits keep the Verify clause |
| 1.4 spinner gone, step() contract intact | `bash -c '! grep -q "SPIN" scripts/deploy-harness.sh && ! grep -q "sleep 0.045" scripts/deploy-harness.sh && grep -q "step()" scripts/deploy-harness.sh'` | 0 | animation out; wrapper kept |
| installer suites (deploy/install behavior unchanged) | `bash -c 'bash tests/scripts/resync-conflict.test.sh && bash tests/scripts/install-tty-gate.test.sh && bash tests/scripts/settings-merge.test.sh && bash tests/scripts/settings-wiring.test.sh'` | 0 | 5+3+9+4 cases |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | clean after all prose edits |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- Planning artifacts: revert the commit adding specs/phase2-wave1/.
- Execution (when run): `git revert` the wave commit — all four items restore cleanly from git history; no data/schema migration; deploy-harness change is cosmetic-only.

### Harness-Delta

- none (this wave exists BECAUSE of prior deltas; nothing new surfaced during planning)
