# Harness v0.3 — Plan Overview: "Event-Sourced Trust"

- **Date:** 2026-07-03
- **Final verdict:** IMPROVE in-place, do not rewrite. Name the cycle **v0.3** (minor bump per the existing CHANGELOG rule — it touches hooks/ + settings.json).
- **Sources (3 research documents):**
  1. `docs/research/harness-review-improvements/2026-07-03-deep-review-harness-trustworthiness.md` — 2 critical, 9 high, 12 medium (ID: DR-*)
  2. `docs/research/harness-review-improvements/2026-07-03-repository-harness-recheck-v2-proposal.md` — adoption audit + 5-phase v2 (ID: RC-*)
  3. `docs/research/harness-review-improvements/research-repository-harness-ideas.md` (2026-06-09) — 16 original IDEAs, the adapt/skip verdicts still hold
- **Format precedent:** `docs/harness-gap-closure-plan.md`

---

## 1. Goals & principles

**In one sentence:** every record the harness mandates must be written by a **machine event** (CI/hook) or **blocked by a machine checker** when absent — no record may depend on "remembering to append"; and at the same time, patch the enforcement holes verified in the deep review.

Execution principles (from all 3 research documents + decision 0007 of repository-harness):

1. **Fix the foundation first, measure later** — do not build a measurement layer on top of a leaking system (Phase 0 before everything else).
2. **Advisory first, blocking later** — new gates ship in WARN mode, flip to strict once they have run clean for ≥1 week.
3. **Deterministic for the evolution layer** — scripts/CI propose improvements; do not let the LLM edit its own policy.
4. **A sequential chain of small PRs, no burst** — the adoption audit proves the 06-14 burst died immediately afterwards; one reviewable PR per wave.
5. **Every change to hooks/ or settings.json = Rule-4 high-blast** → **high-risk** lane, full chain, with a Rollback.

---

## 2. Roadmap — 6 waves / ~9 PRs

| Wave | PR (proposed slug) | Lane | Content | Findings closed | Depends on |
|---|---|---|---|---|---|
| **0a** | `fix/hook-command-matching` | high-risk | Tokenize command matching in `commit-quality-gate.sh`, `risk-corroboration.sh`, `branch-guard.sh`, `check-untracked-py.sh` (catch `git … commit` after `&&`/`;`/`\|`, `-C`/`-c`/`command`); remove the fake `"if"`/`statusMessage` field in settings.json; add bypass-case tests to `tests/` | DR-1 (critical) | — |
| **0b** | `fix/session-knowledge-root` | high-risk | Resolve the repo root with `git rev-parse --show-toplevel` like the sibling hooks; remove `exec 2>/dev/null`; test running from `.claude/hooks/` | DR-2 (critical) | — |
| **0c** | `fix/skill-doc-truth` | normal | Fix the false premises in `finishing-a-development-branch` (specs/ tracked, test command, remote name); add the review chain or drop the parity claim in `executing-plans`; fallback for the phantom quality-reviewer; unify the create-pr base branch; clean up leftover Vietnamese sentences; fix the brainstorming ↔ using-git-worktrees conflict | DR-3, DR-8, DR-11, Low group | — |
| **1** | `feat/post-merge-maintenance` | high-risk (touches CI + the record-keeping process) | GitHub Action `pull_request_target: closed` + `merged==true`: automatically append a row to `trust-metrics.md`, prepend to CHANGELOG, bump VERSION (minor when the diff touches hooks/+settings.json), idempotent commit+tag. Fix the feature-intake Guardrails: drop the manual-append mandate. Fix/remove the `user_turns` metric + Session End Log rotation in `state-breadcrumb.sh` | DR-12, DR-13, RC §4.1, IDEA-01/15 (revived) | 0a (the gate must be airtight before trusting records) |
| **2** | `fix/verify-substance` | normal | `verify_summary.py`: substance denylist (`true`, `:`, `echo`, `exit 0`, a command that does not reference a path in the diff → FAIL); fix the em-dash duplicate + 3 semantics traps; **add `test_verify_summary.py` to `run-tests.sh` (1 line)**; `check_lane_evidence.py`: rollback must differ from the template, lane must match exactly; sandbox/timeout verify on CI | DR-6, DR-7, DR-18, DR-19, RC §4.3 | — (can run in parallel with Wave 1) |
| **3** | `feat/harness-manifest` | high-risk | `harness-manifest.yaml` (tracked): sections `skills` / `hooks` / `agents` / `hard_gates`. `scripts/check-manifest.py` probes by kind + degrade ladder (Inactive/Degraded/Full), runs in CI, gradually replaces `lint-doc-truth.sh`. The 3 hard-gate consumers (`feature-intake` Step 3, `auto-correct-scope.md` Rule 4, `risk-corroboration.sh`) all read the manifest → no more divergence across 4 sources. Also resolves the dependency-bump conflict (Rule 3 vs hook) by encoding the exception into the manifest | DR-4, DR-5 (partly), RC §4.2, IDEA-09/10 (completed) | 0c |
| **4** | `feat/entropy-trend` | normal | Upgrade `harness-audit.sh` → 6 promise-vs-evidence checks (plan active >30d with no activity · SUMMARY missing Verify · verify never re-run · backlog open >14d · manifest Degraded · solutions stale) + **emit `audit-log.jsonl` on every CI run** → a real trend line. Wire into harness-status | DR-13 (measurement part), RC §4.4, IDEA-04 (completed) | 1, 3 |
| **5** | `feat/corrections-propose` | normal | `templates/CORRECTIONS.template.md` + `specs/<slug>/CORRECTIONS.md` (typed: correction/override/rework/approval); `scripts/propose.py` rule-based: group friction+corrections, count≥2 → backlog entry with `predicted_impact`; closing an entry requires `actual_outcome`, and if it is missing the entropy audit counts it as drift (self-policing loop) | RC §4.5, IDEA-05/07/08 (completed) | 4, and the ledger must have ≥2 weeks of real data |
| **6** | `chore/hygiene` | tiny | Delete `settings copy.json`, `.claude copy/`, the 3 `.harness-backup-*` dirs; commit or delete REQ.md / PR_TEMPLATE.md; commit `docs/research/` | DR-21 | any time |

> Waves 0a/0b/0c, Wave 2 and Wave 6 are independent of one another — they can run in parallel. Wave 1 waits on 0a. Wave 3 waits on 0c. Wave 4 waits on 1+3. Wave 5 waits on 4 + data.

---

## 3. Scope per wave (scope / non-goals / main risk)

### Wave 0 — Patch the foundation (DR critical + high)
- **Scope:** exactly the listed fixes, each with a regression test for every proven bypass form.
- **Non-goals:** do not refactor hook style, do not add new hooks, do not touch the break-glass design (moved to the backlog — it needs its own design for a file-based flag with a TTL).
- **Risk:** matching that is too strict → false-blocking of valid git commands. Mitigation: a bypass + happy-path test suite, ship via `bash scripts/run-tests.sh` + CI on 2 platforms.
- **Rollback:** `git revert` per PR; the hooks are pure scripts, no state.

### Wave 1 — Event-driven bookkeeping
- **Scope:** one workflow file + a Guardrails prose fix + the state-breadcrumb fix.
- **Non-goals:** do not release/publish anything outside the repo; do not touch install/deploy.
- **Risk:** `pull_request_target` has push permission — restrict the step to only reading PR metadata (`gh pr view`), never checking out PR code (learning from the known failure mode of this pattern).
- **Decision (2026-07-03, final):** the bot **opens a bookkeeping PR** (`chore/bookkeeping-pr-<N>`) instead of pushing straight to main — no PAT or branch-protection bypass needed; uses the default `GITHUB_TOKEN` + auto-merge if enabled. Accepted trade-off: the record lags by one merge beat instead of being immediate.

### Wave 2 — Verify with substance
- **Scope:** tighten the checker + put the tests in CI. No change to the SUMMARY format.
- **Risk:** the denylist wrongly blocking short but valid commands → allow a per-repo allowlist in the manifest (Wave 3) later.

### Wave 3 — One-source manifest
- **Scope:** manifest + checker + point the 3 consumers at it.
- **Non-goals:** NO product-style registry with ToolEntry/semver/arg-schema (the old SKIP verdict stands); do not port context-scoring.
- **Risk:** bash hooks parsing YAML — solved by generating `hard-gates.generated.sh` from the manifest at CI/pre-commit time, with the hooks sourcing the generated file (deterministic, diffable).

### Wave 4 — Entropy with a trend
- **Scope:** 6 checks + JSONL + trend display. Weights live in the data (not hardcoded), report both raw and banded.
- **Non-goals:** no blocking, no fancy cap-100 scoring.
- **Bug discovered after merge (2026-07-04):** `pull_request_target` always loads the workflow definition from the repo's actual default branch (`main`), regardless of the PR's `base` — and `main` has been frozen since PR #36 (107 commits behind `v2`), so the new `git add` line (Task 2.2) never took effect: `bookkeeping.sh` computes and writes the JSONL line, but the `git add` step in the old YAML on `main` does not stage it → bookkeeping PR #43 had an empty `audit-log.jsonl`. Fix: PR #44 (`ci/sync-post-merge-git-add`, merged straight into `main`, same pattern as PR #36) — sync 1 line, nothing else changed.
- **Secondary finding while merging PR #44 (2026-07-04):** merging PR #44 into `main` triggered `post-merge-maintenance` for PR #44 itself (the workflow trigger has `branches: [v2, main]`) — it FAILED right at the first step: `scripts/bookkeeping.sh: No such file or directory`, because `main` had never received the `scripts/` from Wave 1+ (it only has old pre-v0.3 files like `check_plan_format.py`). This is a pre-existing latent bug, not something PR #44 caused — PR #44 was the FIRST PR merged into `main` since PR #36 registered this workflow on `main`, so this path had never been exercised before. No wrong/corrupted data was written (it crashed on the very first command, before any git operation). **Fix ✅ PR #45** (merged straight into `main`, same pattern as #36/#44) — remove `main` from `branches:` (`[v2, main]` → `[v2]`); the workflow file still lives on `main` (keeping the registration, per PR #36's original reasoning — it only needs to *exist*, it does not need to be in `branches:`), so only merges into `v2` still trigger `bookkeeping.sh`.

### Wave 5 — A closed improvement loop
- **Entry gate for the wave:** only start when (a) the event-driven ledger has ≥2 weeks of real rows, (b) the current backlog has been triaged (there is currently 1 orphaned entry, 19 days old — if nobody triages it, skip this wave, exactly per the "graveyard" warning from the 06-09 research).
- **Decision (2026-07-03):** the owner commits to triaging the backlog — Wave 5 stays on the roadmap; conditions (a)/(b) must still be satisfied before starting.
- **Gate status (2026-07-04):** (a) NOT yet satisfied — the event-sourced ledger only started running for real on 2026-07-03, so we need to wait until ~2026-07-17. (b) ✅ triaged — the `pretooluse-hook-denies-combined-git-add-commit` entry was closed via the docs-only route (add a rule to `CLAUDE.md` Gotchas instead of modifying `hooks/check-untracked-py.sh`, avoiding a full high-risk chain for what is purely a workflow-ordering friction); see `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`. Wave 5 still NOT started — waiting on (a).

---

## 4. v0.3 success criteria (definition of "done")

1. **Zero records waiting on a human to append** — no "append X" mandate remains in the docs without an accompanying event/checker (grep-able).
2. Merge any PR → trust-metrics + CHANGELOG get an automatic entry within ≤1 minute.
3. `ci-strict-gate` **cannot** be passed with `| x | true | 0 | |` — with a pinning test to prove it.
4. The hard-gate list exists in exactly **one** machine-readable place; the 3 consumers point at it — with a pinning test.
5. `harness-audit` produces a single number + a trend with ≥3 weeks of JSONL data. **NOT yet done (2026-07-04):** the mechanism has shipped (Wave 4, PR #42) but `audit-log.jsonl` only received its first real line after PR #44 (the main/v2 sync fix) was merged — we need ≥3 weeks of data accumulated from that point before it counts as a "real trend".
6. All the bypass forms in DR-1 are blocked — with a pinning test per form (`cd x && git commit`, `git -C`, …).
7. Every v0.3 PR goes through the very workflow it builds (dogfood: correctly declared lane, SUMMARY with a real Verify, Rollback for high-risk).

## 5. Out of scope for v0.3 (reaffirming the earlier verdicts)

- Rust/SQLite substrate · context-read scorer · schema versioning/importer · AGENTS.md agnosticism (waiting on a second consumer) · 6×11 maturity matrix · break-glass redesign (backlog, needs its own design) · extending branch-isolation to Bash writes (backlog — needs false-positive consideration first).

## 6. Next steps

1. You review this overview (in particular: the wave ordering, the PAT decision point in Wave 1, the entry gate for Wave 5).
2. Run `/feature-intake` for Wave 0a → SUMMARY (high-risk lane) → `/writing-plans` → detailed PLAN.md per `rules/plan-format.md` → worktree → execute.
3. Each wave repeats the cycle; this overview updates its status column after every merge.

| Wave | Status |
|---|---|
| 0a | ✅ merged (PR #31) — matcher lib + 4 hooks rewired + `if` removed; 41 tests; reviews F1/F2 fixed |
| 0b | ✅ merged (PR #32) — session-knowledge resolves the root with git rev-parse (DR-2); deployed-location regression test |
| 0c | ✅ merged (PR #33) — 8 doc-truth files; intent review pass (phantom /code-review self-fixed) |
| 1 | ✅ merged (PR #34) + **registration fix PR #36** (GitHub only registers pull_request_target from the default branch `main`) + backfill #31–#35 (PR #37) + repo setting "Actions may create PRs" enabled. **Full auto loop verified 2026-07-04**: merge #40 → the workflow opens #41 by itself → merge → loop-guard skip ✓. VERSION auto-bumped to 0.7.2 |
| 2 (verify-substance) | ✅ merged (PR #38 + auto-bookkeeping #39) — trivial denylist (DR-6, pinned at the gate), negative proof (19a), honest stamp (19b), row-order rewrite (19c + review MEDIUM fix), placeholder sets cross-pinned (DR-18), lane/rollback exactness, test_verify_summary in CI (DR-7) |
| 3 (manifest) | ✅ merged (PR #35) — harness-manifest.json canonical (8+3 gates + inventory); check_manifest.py enforces hook↔manifest + presence-scan in CI; DR-4 fixed |
| 4 (entropy trend) | ✅ merged (PR #42) — `harness-audit.sh` 3→6 checks (verify-never-rerun, backlog-stale, manifest-degraded) + `--root`/`--json` + a 16-case test suite (the first for this script); `bookkeeping.sh` writes 1 JSONL line per merged PR into `audit-log.jsonl` (reusing the post-merge flow, no new workflow); wired into `harness-status.sh`. Two rounds of correctness-review caught + fixed 2 real bugs (`set -u` unbound array; an uncaught `KeyError` in an except block); 1 advisory (dirname/`--root` edge case) left in place with a note. Intent-review caught 1 drift ("every CI run" → "every merge") — asked and confirmed correct. `/compound` wrote 2 new docs + promoted critical-patterns. **Follow-up ✅ merged (PR #44, straight into `main`)** — syncs the `git add` line that went "missing" because `main` was frozen 107 commits behind (see §3 Wave 4); also uncovered 1 latent bug (not yet fixed, see §3 Wave 4) when merging PR #44 triggered bookkeeping for itself and crashed because `main` lacks `scripts/bookkeeping.sh`. `audit-log.jsonl` still has NO real lines — waiting for the next merge into `v2` |
| 5 | ⬜ (gated: ≥2 weeks of data + backlog triaged) |
| 6 | ✅ merged (PR #40 + auto #41) — 6 plan flips shipped (blast-radius noise gone), research corpus committed, local junk (settings copy.json, .claude copy/, backups) deleted. REQ.md / PR_TEMPLATE.md committed (`1b95fc8`, outside the PR flow — a direct chore on `v2`) |
