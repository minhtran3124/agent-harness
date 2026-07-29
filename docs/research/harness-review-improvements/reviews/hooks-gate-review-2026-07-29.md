# Hooks Gate Review — Redundancy & Over-Blocking Audit

- **Date:** 2026-07-29
- **Method:** Single-pass read of all 13 `hooks/*.sh` + `settings.json` + `harness-manifest.json`, producing an initial hypothesis list. Then 4 parallel research agents were spawned to test those hypotheses against **real evidence** — git history, `docs/solutions/`, `docs/harness-experimental/{break-glass-log,trust-metrics,audit-log.jsonl}`, `specs/STATE.md`, and real commit subjects — rather than re-reading the same source comments. One hypothesis was **directly refuted** by the evidence; it's corrected below rather than dropped.
- **Framing:** the question on the table was: is the hook/gate system redundant, over-coded for gating, and blocking enough to annoy the user? The verdict has to rest on observed trip rates and observed blocks, not on how the code reads.

---

## 1. Executive summary

**The gate system is not over-blocking in aggregate, and it is demonstrably self-correcting.** The one clear historical loosening event (2026-07-23) was preceded by measured trip rates (85% and a 1/40 false positive) and was scoped narrowly — 2 of 9 risk categories, enforcement-only, leaving classification untouched. No gate has ever been re-tightened, and only one real false positive (auth/authorization keywords tripping on English words inside test comments) was ever found and fixed. Zero commits were found in this repo's history that were actually rejected by the two Lane-related commit-time checks.

That said, the audit surfaced two **real, previously-undocumented issues** — not about blocking too much, but about a latent correctness gap and a documentation drift:

1. **Lane-resolution divergence** (Finding F1, medium): `commit-quality-gate.sh` and `risk-corroboration.sh` each independently resolve the `Lane:` field, using *different* fallback strategies. One can attribute an unrelated spec's Lane to a commit that never touched `specs/`.
2. **`break-glass-log.md` header is stale** (Finding F3, low): it attributes the log exclusively to a hook that was deleted five weeks ago, while a different, currently-wired hook writes to the same file under a different entry format.

One initial hypothesis was wrong: **`branch-guard.sh` is not dead weight** — it is the only remaining coverage for `specs/`-only commits landing on `main`, which is a real, common, by-design pattern in this repo (153 specs-only commits found in history).

---

## 2. System inventory

| Hook | Trigger | Decision | LOC |
|---|---|---|---|
| `check-untracked-py.sh` | PreToolUse, `git commit\|push` | block | 30 |
| `commit-quality-gate.sh` | PreToolUse, `git commit` | block (5 sub-checks) | 271 |
| `risk-corroboration.sh` | PreToolUse, `git commit` | block (manifest-driven per-category) | 205 |
| `branch-guard.sh` | PreToolUse, `git commit` | warn only | 30 |
| `branch-isolation-guard.sh` | PreToolUse, Edit\|Write | block | 60 |
| `ruff-on-edit.sh` | PostToolUse, Edit\|Write | auto-fix, no gate | 12 |
| `blast-radius-check.sh` | PostToolUse, Edit\|Write | warn (block opt-in via env) | 79 |
| `render-plan-on-write.sh` | PostToolUse, Edit\|Write on `PLAN.md` | non-blocking | 36 |
| `scope-gate.sh` | UserPromptSubmit | non-blocking (context injection) | 22 |
| `session-knowledge.sh` | SessionStart | non-blocking | 125 |
| `state-breadcrumb.sh` | SessionEnd | non-blocking | 107 |
| `auto-test-on-change.sh` | — | **dormant**, not wired | 120 |
| `lib/git-command.sh` | shared matcher | n/a | 96 |

A single `git commit` invocation runs **3 PreToolUse hooks in sequence** (`check-untracked-py.sh` → `commit-quality-gate.sh` → `risk-corroboration.sh` → `branch-guard.sh`, 4 total), issuing roughly **19 git subprocesses** across them in the worst case (specs + app + other files touched). No evidence this latency has ever been a complained-about problem — it is a real cost, but not one anyone has flagged.

---

## 3. Findings

### 3.1 Gates are actively tuned down in response to measured friction — confirmed

Full git history of `harness-manifest.json` shows exactly **one** loosening event, `3e440da` (2026-07-23):

- `workflow-engine`: block → warn. Recorded reason: *"fired on 34/40 recent commits (85%) — in this meta-repo those paths ARE the product, so blocking carried ~0 bits."*
- `weakening-validation`: block → warn. Recorded reason: *"1 firing in the last 40 commits and it was a refactor (precision 0)."*
- Expected effect, documented at the time: blocking-gate trip rate **85% → ~15%**.
- The other 7 `detectable` categories (`auth`, `authorization`, `data-loss/migration`, `audit/security`, `external-provider`, `public-contract`, `high-blast`) have never been loosened and have **zero recorded false positives**.
- The only other real false positive found anywhere in history: `risk-corroboration.sh` matching the English words "session"/"permission" inside shell-test *comments* — found and fixed 2026-07-16 (comment-stripping added, regression test landed). `docs/solutions/harness/risk-corroboration-scans-test-comments-for-auth-words.md`.
- `docs/harness-experimental/break-glass-log.md` has **0 entries** — not because overrides are hidden, but because the override path has genuinely never been exercised (see 3.5).
- No gate has ever been re-tightened (warn → block).

**Reading:** this is what a working feedback loop looks like — loosen only with a number behind it, scope the loosening to enforcement (not classification), leave a written rationale. It argues against "gates are over-coded on vibes" as a general claim.

### 3.2 `branch-guard.sh` is not redundant — hypothesis refuted

Original hypothesis: since `branch-isolation-guard.sh` (added 2026-06-17, blocks Edit/Write on `main`/`master`) postdates `branch-guard.sh` (added 2026-05-25, warns on `git commit` on `main`/`master`), the latter should have nothing left to warn about.

Refuted: `branch-isolation-guard.sh` explicitly exempts `specs/*` from its block (by design — intake has to write `SUMMARY.md` before a branch exists). Real, by-design workflow patterns — `state-breadcrumb.sh` session-end commits, `docs(specs):` bookkeeping — land directly on `main` through that exemption. 153 specs-only commits were found in history, with concrete examples of commits made `--first-parent` directly on `main` (not just merged in). `branch-guard.sh` is the *only* hook left that nudges on those. **Verdict: keep, unchanged.**

### 3.3 `scope-gate.sh` nags on an estimated 25–35% of implementation-intent turns — mostly by design, one real gap

A manual regex walk over 30 real commit subjects (used as a phrasing proxy) estimated roughly 8/30 (~27%) would trip the nag. This is not literal chat spam — it's `additionalContext` on `UserPromptSubmit`, private model-context, not a visible message — so the cost is token/attention, not a visible interruption. The tiny-lane resolution is baked into the injected text itself ("Tiny lane → proceed with a direct edit, no confirmation needed"), so a firing is self-dismissing rather than a dead-end.

A prior review (`docs/research/harness-review-improvements/reviews/over-engineering-review-2026-07-16.md`) already rated this hook "keep (borderline) — cheap, advisory."

**Real, undocumented gap found this pass:** the hook has no session-state dedup. Within one active tiny-lane task, every follow-up message that matches the regex re-injects the same nudge, even though routing already happened — pure repeated token cost for zero new signal.

### 3.4 Lane-resolution divergence between `commit-quality-gate.sh` and `risk-corroboration.sh` — new finding, F1, medium severity

Both hooks independently read the `Lane:` field on every commit, using **different** strategies:

- `commit-quality-gate.sh` Check 1.6 delegates to `scripts/verify_summary.py --lane`, strictly scoped to slugs the staged diff actually touched (`git diff --cached --name-only` → `specs/<slug>/`). If the commit touches no `specs/*` path, this check does not run at all.
- `risk-corroboration.sh` reads `Lane:` directly in bash, preferring a staged `SUMMARY.md` — but **falls back to the most-recently-*modified* `SUMMARY.md` anywhere on disk** (`ls -t specs/*/SUMMARY.md | head -1`) when the current commit stages none.

Concrete failure scenario: a commit that touches only `app/utils.py` and `hooks/` (no `specs/` path) skips Check 1.6 entirely, but `risk-corroboration.sh` will still borrow whatever spec was most recently touched on disk — possibly from a different, unrelated task — and corroborate (or wrongly block) the current commit against that Lane. No evidence this has fired in anger yet, but it's a live latent bug, not hypothetical.

### 3.5 `break-glass-log.md` header is stale — new finding, F3, low severity (found directly, not by an agent)

The file's own header text: *"Audit trail of overrides to `hooks/protected-path-guard.sh` (a **dormant** hook...)."* That hook was deleted in PR #133 (2026-07-21). Meanwhile `hooks/branch-isolation-guard.sh` — currently wired, active — **also appends to this exact file** on `BRANCH_ISOLATION_REASON` overrides (confirmed at `hooks/branch-isolation-guard.sh:46-50`), under a different entry format than the one the header documents (`- <iso8601> — branch-isolation \`<path>\` on \`<branch>\` — <reason>` vs. the documented `- <iso8601> — \`<path>\` — <reason>`). The header was never updated when `protected-path-guard.sh` was removed and `branch-isolation-guard.sh` took over the log. Cosmetic, but exactly the kind of doc-truth drift this repo's own CI lint is meant to catch elsewhere.

### 3.6 No real blocked commits found for either Lane-related gate

Across the full history, no commit message, `SUMMARY.md`, or `docs/solutions/` entry records an actual rejection by Check 1.6 (lane evidence) or `risk-corroboration.sh`'s lane-mismatch block. The one adjacent real block found is a *different* mechanism entirely (CI's `strict-gate` on a pytest environment bug, `specs/acceptance-contract-loop-budget/SUMMARY.md`). The tempdir-materialization complexity in Check 1.6 (mktemp, `git show :file` staging, `--plan-dir` override) is not gratuitous, though — it exists specifically to close a documented fail-*open* bug (SC coverage silently skipped) recorded in that same SUMMARY.

---

## 4. Recommendations, ranked

1. **Fix the Lane-resolution divergence (F1).** Extract a shared `hooks/lib/lane.sh`, mirroring the pattern of `hooks/lib/git-command.sh`, with one resolution strategy used by both hooks. Prefer the stricter behavior (scoped to slugs the diff actually touched; no cross-slug "most recent on disk" fallback) — or, if the fallback is kept for a reason, make it visible in the hook's own denial/warn text so a human isn't corroborated against a Lane they can't see.
2. **Add session-scoped dedup to `scope-gate.sh`.** Skip the nudge once a Lane has already been resolved / a `specs/*/SUMMARY.md` has already been touched this session — closes the repeated-nudge gap in 3.3 at near-zero cost.
3. **Fix the `break-glass-log.md` header (F3).** One-paragraph edit: it's `branch-isolation-guard.sh`'s log now, not `protected-path-guard.sh`'s.
4. **Leave `branch-guard.sh` as-is.** The removal hypothesis was refuted by evidence (3.2).
5. **Leave the 7 remaining block-mode risk-corroboration categories as-is.** Zero recorded false positives beyond the one already fixed; no basis to loosen further.
6. **Low priority / optional:** the ~19 git subprocesses per commit are cheap in absolute terms and nobody has recorded a latency complaint — not worth restructuring for performance alone. Only worth touching as a side effect of #1 (a shared Lane-read lib would incidentally cut a few redundant `git show`/`git diff` calls).

## 5. What not to change

- `workflow-engine` / `weakening-validation`: already correctly loosened to warn; don't re-tighten without a new measured trip-rate.
- The 7 hard-block categories (`auth`, `authorization`, `data-loss/migration`, `audit/security`, `external-provider`, `public-contract`, `high-blast`): no evidence of false positives; keep blocking.
- `branch-isolation-guard.sh`: structural, correctly scoped (specs/ exemption is deliberate and load-bearing), no evidence of over-firing.

## 6. Appendix — condensed per-agent findings

**Agent 1 (gate-trip history):** one loosening event (2026-07-23, `workflow-engine` 85%→~15% expected, `weakening-validation` 1/40 precision-0); no re-tightening ever; break-glass log empty because its only historical user (`protected-path-guard.sh`) was deleted; `audit-log.jsonl` staleness-finding count trending from 21–36 down to 0 since 2026-07-17.

**Agent 2 (`branch-guard.sh` redundancy):** refuted — 153 specs-only commits found on `main`, `branch-isolation-guard.sh`'s `specs/*` exemption is the reason `branch-guard.sh` still has real coverage; recommend keep unchanged.

**Agent 3 (`scope-gate.sh` nag rate):** ~25–35% estimated trigger rate on implementation-intent turns; mostly by-design (tiny lane self-dismisses); prior review already rated it "keep, borderline"; found undocumented no-dedup gap.

**Agent 4 (`commit-quality-gate.sh` / `risk-corroboration.sh` overlap):** ~19 git subprocesses/commit worst case across the 3 PreToolUse commit hooks; confirmed the Lane-resolution divergence (F1) as a real, distinct-strategy bug, not just duplicated code; zero real historical blocks found for either gate; tempdir complexity in Check 1.6 is proportionate to a documented fail-open bug it fixed.
