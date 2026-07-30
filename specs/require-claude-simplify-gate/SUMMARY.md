# require-claude-simplify-gate — Summary

Lane: high-risk
Confidence: high
Reason: This proposal changes workflow-engine sequencing, mutation authority, review receipts, and the final push gate.
Flags: workflow-engine
Affects: subagent-driven-development, final review chain, review receipt, finishing gate
Input-type: harness improvement

### Intent

> "hãy lên plan cho việc require skill "simplify" vào workflow hiện tại. hãy research và cho tôi
> biết suy nghĩ của bạn về request này, có đúng ko? có hợp lý ko? có đáng làm ko?"
>
> "ok, hãy viết plan vào doc trước cho tôi"

## What changed

Created a research brief, approved design, and executable proposed plan for adding Claude Code's
bundled `/simplify` as a signal-gated cleanup stage before final review. No runtime workflow
behavior was changed.

### Rationale

The current pipeline lacks a branch-wide owner for reuse, simplification, efficiency, and
abstraction-altitude cleanup. Because `/simplify` mutates code and has version-sensitive vendor
semantics, the plan requires a shadow eval, a minimum client version, post-mutation verification,
and final reviews over the resulting HEAD.

### Alternatives considered

- Require `/simplify` after every task — rejected as duplicate fixed ceremony.
- Require it for every branch — rejected for tiny and non-code changes.
- Keep the existing warning only — rejected because it is not a durable workflow guarantee.
- Create a repository skill named `simplify` — rejected because it may shadow the bundled skill.

### Deviations

- Rule 3 — Relative `--fixtures`/`--output`/`--claude` paths weren't resolved absolute before a
  subprocess `cwd` change (`git bundle create`), breaking `run_simplify_stage_eval.py` from any
  caller cwd other than repo root. Commit `0eb1287`.
- Rule 3 — Sandboxed candidate collection failed 100% on `~/.claude/session-env` EPERM (Bash tool
  needs it regardless of `$TMPDIR`); fixed via `CLAUDE_CONFIG_DIR`, verified empirically not to
  touch the real `~/.claude`. Commit `8c51780`.
- Rule 3 — After the above, `git` itself failed inside the sandbox (`/dev/null` write-deny,
  unallowed git-common-dir) — pre-existing Wave-1 gaps never exercised until a real multi-step
  agentic run; scoped only to the eval's own disposable synthetic repo and universally-safe
  devices, not the security boundary from the Rule-4 case below. Commit `50e3470`.
- Rule 3 — An independent adversarial review of `6ac6d65` found `simplify-stage.md`'s "not
  required" skip path had no valid `simplify_record.py finish --begin-state` to pass; re-keyed the
  bookkeeping decision on `reviewable_paths` instead of `required`. Commit `0611dbb`.
- Rule 1 — Assorted unused-variable removals and lint fixups caught by `ruff`/mutation-review
  passes across waves 1-5 (no behavior change, folded into each wave's own commit).

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Planning contract | `python3 scripts/check_plan_contract.py specs/require-claude-simplify-gate/PLAN.md` | 0 | Contract passed on 2026-07-30 | |
| Plan render | `python3 skills/visual-planner/render_plan.py specs/require-claude-simplify-gate/PLAN.md` | 0 | Parsed 8 tasks across 6 waves | |
| Pre-change full suite | `GOCACHE=/tmp/harness-skills-go-cache bash scripts/run-tests.sh` | 0 | 278 Python tests; all shell contracts green (pre-implementation baseline) | |
| Capability/policy tests | `python3 -m pytest scripts/test_check_claude_simplify.py -q` | 0 | 103 passed | SC-1 |
| Policy self-test | `python3 scripts/check_claude_simplify.py --self-test-policy` | 0 | `simplify-policy: self-test passed` | SC-2 |
| Evidence recorder tests | `python3 -m pytest skills/subagent-driven-development/scripts/test_simplify_record.py -q` | 0 | 27 passed; dirty-worktree, symbolic/short SHA, ancestry all rejected | SC-3 |
| SDD ordering contract | `bash tests/scripts/sdd-simplify-stage-contract.test.sh` | 0 | 25 passed, incl. 12 mutation checks | SC-4 |
| Receipt validation tests | `python3 -m pytest scripts/test_check_review_receipt.py -q` | 0 | 39 passed | SC-5 |
| Receipt self-test | `python3 scripts/check_review_receipt.py --self-test-simplify` | 0 | `check-review-receipt: simplify self-test passed` | SC-6 |
| Finishing contract | `bash tests/scripts/finishing-branch-contract.test.sh` | 0 | 4 passed, incl. simplify-clause mutation check | SC-7 |
| Shadow-eval quality gate | `python3 scripts/score_simplify_stage_eval.py --compare evals/skills/simplify-stage/results/baseline.json evals/skills/simplify-stage/results/candidate.json --fixtures evals/skills/simplify-stage/fixtures --quality-gate` | 0 | Round 3 (HEAD `5a34cae`): `quality_pass: true`, 8/8 fixtures matched `truth.json`. Rounds 1-2 rejected first (`comparison.md`) | SC-8 |
| Shadow-eval value gate | `python3 scripts/score_simplify_stage_eval.py --compare evals/skills/simplify-stage/results/baseline.json evals/skills/simplify-stage/results/candidate.json --fixtures evals/skills/simplify-stage/fixtures --value-gate` | 0 | `value_pass: true`, `value_score: 4` ≥ `minimum_value_score: 3` | SC-9 |
| Adoption/deployed parity | `python3 scripts/check_simplify_adoption.py` | 0 | `consistent` — policy, ordering, receipt, hook, docs, deployed harness all agree (post `deploy-harness.sh`) | SC-10 |
| Post-change full suite | `GOCACHE=/tmp/harness-skills-go-cache bash scripts/run-tests.sh` | 0 | 473 passed (was 278 at intake — CI-registration gap for the 4 new Python test files closed in wave 5) | |

### Plan Review

- Independent review — PASS. Same-wave files are disjoint; shadow evaluation precedes hard-gate
  wiring; `/simplify` runs before the branch package and final oracles; changed outcomes require
  verification plus spec/quality delta review; receipt freshness covers the post-simplify HEAD.

### Rollback

- Whole feature: `git revert --no-commit 29a5419..<final-HEAD> && git commit` (revert range against the
  branch's actual base, `feat/superpowers-6-review-pipeline` at `29a5419` — never `main`, which has
  229 unrelated commits ahead of this branch's true fork point).
- Sandbox-only rollback (keep the harness policy/receipt/SDD wiring, drop only the eval-harness
  sandbox widening): `git revert <f5ecf89> <50e3470>` — reverts the `/tmp/claude-<uid>` and
  git-common-dir/safe-devices sandbox exceptions (`specs/require-claude-simplify-gate/ESCALATIONS.md`
  E001) without touching the required-gate machinery itself.
- Hard-gate-only rollback (keep the shadow-eval evidence, drop enforcement): revert `cba0b71`,
  `f1a9e8f`, `6ac6d65`, `0611dbb`, `c8b7840` — removes `simplify_record.py`, the
  `--require-simplify-if` receipt/finishing gates, the SDD wiring, and the doc/manifest/hook sync,
  leaving the accepted shadow-eval result as a standalone research artifact.
- After a push: prefer `git revert` over history rewriting; never force-push over `origin/main` or
  this branch once shared.

### Harness-Delta

- proposed — add a capability-pinned, signal-gated cleanup stage without weakening existing final oracles.
