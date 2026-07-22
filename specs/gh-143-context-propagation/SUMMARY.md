# gh-143-context-propagation — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate — the work edits hooks/risk-corroboration.sh and core review-chain skills (high-blast surfaces); direction is unambiguous (issue #143 authored and approved by the repo owner).
Flags: existing-behavior, weak-proof, multi-domain
Affects: hooks/risk-corroboration.sh, harness-manifest.json, skills/correctness-review, skills/subagent-driven-development, skills/finishing-a-development-branch, skills/feature-intake
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> now, let make plan for all phases first

Then, after the plan was presented, the user chose **Subagent-Driven (this session)** execution
and said:

> resume working

(Context: "all phases" = Phases 0–5 of minhtran3124/agent-harness issue #143 — "fix(review):
close context-propagation escapes in Claude Code workflow changes" — reviewed and summarized
earlier in the same session. Phase 5's threshold half already shipped as issue #152 / PR #153.
The intent therefore spans BOTH planning all phases AND executing them in this session via
subagent-driven-development.)

## What changed

Planned and then executed all 6 waves (Phases 0–5 of issue #143) on
`feature/gh-143-context-propagation`. The product delta:

- **Phase 0** — two review-chain regression fixtures (`context-rule-unread`,
  `stale-inline-policy`) reproducing the PR #141 P1/P2 escapes, plus
  `tests/scripts/context-propagation-regression.test.sh` (parses the live skill files; mutation
  cases prove the two explicit Reads + the 8-case STOP list are load-bearing).
- **Phase 1** — a `workflow-engine` hard-gate path signal in `hooks/risk-corroboration.sh`
  (mirrored in `harness-manifest.json` + `category_mode`) so workflow-as-code Markdown can't stay
  `Lane: normal`; `feature-intake` + `CLAUDE.md` guidance that such Markdown is executable.
- **Phase 2** — the change-triggered `/context-propagation-audit` skill (consumer/context
  delivery matrix; assumed/unconfirmed delivery FAILS), wired into subagent-driven-development;
  `tests/scripts/inline-policy-drift.test.sh` guards the Rule-4 STOP list against silent drift.
- **Phase 3** — `evals/context-boundaries/` probe protocol + a baseline run (Claude Code 2.1.217)
  proving delivery per isolated context, honestly recording the cheap-model + main-session
  `unconfirmed` cases.
- **Phase 4** — `scripts/check_review_receipt.py` (fail-closed, HEAD-pinned) + template + tests,
  wired to write receipts after review and gate the finishing-branch push.
- **Phase 5 (remainder)** — the threshold-75 benchmark (catch rate 7/7, 1 soft FP, honest
  harness caveats) and `docs/review-escapes.md` ledger seeded with the three known escapes.

Planning artifacts (`design.md`, `research-brief.md`, `PLAN.md`) were written first.

### Rationale

The issue is itself a detailed, owner-authored design; planning proceeded directly on it plus
repo ground truth (Explore agent report) rather than re-running brainstorming. High-risk lane
because execution touches `hooks/*` and core review skills (manifest high-blast + the very
workflow-engine class this issue defines); the hard-gate human confirmation is satisfied by the
owner directing the work on their own issue.

### Alternatives considered

- One plan per phase (6 plans) — rejected: phases share one inventory definition (Task 1.1)
  and one fixture corpus; a single plan keeps the dependency chain visible.
- Skipping Phase 3 probes as "unverifiable" — rejected: the issue makes unverified boundary
  claims a blocking class; the manual probe protocol is the minimum honest form.

### Deviations

- Rule 1 — Final correctness review found the `workflow-engine` signal over-matched
  `agents/README.md` / `agents/*.template.md` (prose), asymmetric with the `skills/README.md`
  exclusion. Fixed the regex in `hooks/risk-corroboration.sh` + added three agents/ test cases.
- Rule 2 (plan correction) — Task 2.1's declared Files omitted `harness-manifest.json`; a new
  `skills/<name>/SKILL.md` must be registered there or `check_manifest.py` fails. Added to the
  plan before dispatch, so the audit skill was registered.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| workflow-engine gate + agents/ exclusions + nested prompts | `bash tests/hooks/risk-corroboration.test.sh` | 0 | 22 cases incl. agents/README+template silent-pass, nested prompt block |
| Manifest ↔ hook ↔ disk parity | `python3 scripts/check_manifest.py` | 0 | workflow-engine slug + audit skill registered |
| P1/P2 regression guard | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | mutation cases detect removed Reads / STOP case |
| Inline-policy drift guard | `bash tests/scripts/inline-policy-drift.test.sh` | 0 | Rule-4 STOP list drift detected |
| Doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | all referenced paths exist; hook table matches settings.json |
| workflow-engine regex parity (hook ↔ receipt gate) | `bash tests/scripts/workflow-engine-regex-parity.test.sh` | 0 | include+exclude patterns byte-identical; mutation detected |

The receipt engine (`scripts/check_review_receipt.py`) is proven by `scripts/test_check_review_receipt.py`
(11 pytest cases incl. stale-sha, blocking-open, malformed, symbolic-sha reject, specs-only-advance
tolerance) — run by the `harness-ci` test job, not listed above because the strict-gate job has no
pytest and every `### Verify` row must run self-contained in <60s.

### Rollback

- Revert the whole branch: `git revert --no-edit 89422d1..3f362a5` (and the follow-up review-fix
  commit), or drop the branch entirely: `git checkout main && git branch -D feature/gh-143-context-propagation`.
- The `workflow-engine` gate and `check_review_receipt.py` are source-only (not deployed to
  `.claude/`), so reverting the branch fully disarms them; no separate un-deploy step.

### Harness-Delta

- backlog — the `/context-propagation-audit` benchmark (wave 6) showed the two new fixtures are
  *easier* than the cross-context escapes they model (a single-diff correctness pass catches
  them). A harder cross-context fixture variant is needed to truly exercise the audit; recorded
  in `evals/skills/review-chain/results/2026-07-22-threshold-75.md` and `docs/review-escapes.md`.
