# harness-reliability-improvements — Summary

Lane: high-risk
Confidence: medium
Reason: Hard gate — scope touches `.claude/settings.json` (SessionStart hook), `hooks/*` (commit-quality-gate, risk-corroboration), and core skill engines (feature-intake SKILL.md, SUMMARY template); the breadth of the scope (top-5 vs all 9 items) needs a human to decide.
Flags: existing behavior, weak proof (new scripts have no tests yet), multi-domain (hooks + templates + skills + docs + CI)
Affects: settings.json (hook registration), hooks/commit-quality-gate.sh (REQUIRE_VERIFY path), templates/SUMMARY.template.md (5-field schema), docs/harness-experimental/trust-metrics.md (ledger columns), doc-truth lint (hook table ↔ settings.json)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

## What changed

(Not yet implemented — this is the intake for drafting the PLAN.md that improves the harness per
`docs/research-harness-req-assessment.md`: complete the migration of specs/, answer Q3 (Affects field
+ PROJECT.md), machine-verified proof (verify-summary), close the knowledge loop, strict-in-CI,
story-sizing gate, harness-audit.)

### Rationale

The 2026-06-11 research scored the repo as answering 4/6 of the questions in REQ.md; the improvement items
were already prioritized in the doc. This plan turns that priority list into executable waves, following
the full chain of the high-risk lane.

### Alternatives considered

- Implement each item directly without a PLAN.md — rejected: scope >3 steps, >2 files, multi-wave,
  and several items are Rule-4 (settings.json, hooks/*) which mandates gated-execute.

### Deviations

- Rule 1 — Escaped pipes in `docs/harness-experimental/trust-metrics.md` ledger row (`` `\|\| true` ``) so the new `Affects` column keeps a consistent 9-column machine-read shape. Task 1.4.
- Design refinement (human-approved) — Task 4.1's gate semantics changed from the plan's literal "run `--check` for **all** changed slugs (block on any failure)" to "require **≥1** changed high-risk SUMMARY to verify clean; other failures are non-blocking **warnings**." Reason: this PR is the first-ever `specs/` commit, so `git diff main...HEAD` marks all history as changed and the gate re-ran 5 legacy SUMMARYs whose pre-`verify_summary` Verify tables hold illustrative prose (not runnable). The ≥1-passing rule keeps the "PR carries real proof" guarantee, is unaffected in steady state (a PR changes 1 slug), and does not punish an honest change for legacy baggage. Dogfood vs `main`: `OK (2 verified)` + 5 legacy warnings.

### Verify

Commands are pipe-free and idempotent so `scripts/verify_summary.py --check` can re-run them.

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| doc-truth lint (hook table ↔ settings.json) | `bash scripts/lint-doc-truth.sh` | 0 | green after 3.1 wiring |
| verify_summary unit tests | `python3 -m pytest scripts/test_verify_summary.py -q` | 0 | 19 passed |
| session-knowledge hook test | `bash tests/hooks/session-knowledge.test.sh` | 0 | 7 passed |
| commit-quality-gate hook test | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | 16 passed (incl. REQUIRE_VERIFY re-run + python3-degrade) |
| ci-strict-gate test | `bash tests/scripts/ci-strict-gate.test.sh` | 0 | 8 passed (incl. false-positive guard + ≥1-passing semantics) |
| settings.json valid JSON | `jq -e . settings.json` | 0 | SessionStart hook registered |

### Rollback

- Task 3.1 (SessionStart wiring + CLAUDE.md hook row): `git revert <sha-3.1>` — reverts `settings.json` registration and the CLAUDE.md table row together (single commit, doc-truth stays consistent).
- Task 3.2 (`commit-quality-gate.sh` REQUIRE_VERIFY path): `git revert <sha-3.2>`.
- Task 4.1 (CI strict-gate job + script): `git revert <sha-4.1>` (additive — removes the PR-only job, script, and test).
- Earlier waves are reversible via `git revert <wave-sha>`.

### Escalation — deploy sync required (human)

After task 3.1, the root `settings.json` declares the SessionStart hook but the deployed `.claude/` copy does not yet. `tests/scripts/settings-wiring.test.sh` (deploy-derivation check) is therefore **deterministically red locally** until a human runs `scripts/deploy-harness.sh` to sync `.claude/`, then re-runs `bash scripts/run-tests.sh`. I do not run `deploy-harness.sh` (memory rule). **CI is the official gate** and is unaffected — `.claude/` is untracked, so the wiring test's `.claude/` assertions skip there.

### Harness-Delta

- backlog — The doc-truth lint couples "hook file exists" to "CLAUDE.md table row exists", but the plan split the hook file (task 2.2) from its table row (task 3.1) across waves. Result: the aggregate suite is unavoidably red between wave 2 and wave 3. A future plan touching a new hook should land the file + its table row in the same wave (or have the lint treat a registered-but-unrowed hook as a soft warning during transitions).
