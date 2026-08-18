# Harness gap-closure plan — synthesized from 6 research documents

> **Sources:** synthesis of `research-openai-harness-engineering`, `research-claude-code-harness-comparison`,
> `research-repository-harness-ideas`, `research-compound-loop-closure`, `research-harness-req-assessment`,
> `research-agentic-engineering-roadmap`.
> **Date:** 2026-06-14.
> **Ranking principle:** number of research docs pointing at the same gap (consensus = confidence) × leverage / effort.
> **Scope note:** each item, when *executed*, must go through `/feature-intake` to be assigned a lane. An item touching
> high-blast paths (`settings.json`, `hooks/*`, `commit-quality-gate.sh`, `CLAUDE.md`) is **Rule-4** —
> it requires prior human confirmation (`rules/auto-correct-scope.md`).

---

## 0. Already done — not part of the plan (avoid duplicated work)

> **Correction 2026-06-14 (after a ground-truth check):** many "gaps" in the research were closed between
> the time the research was written (06-08→06-13) and now. Verify each item on disk before implementing.

Raised by research, now resolved at the mechanism level:

- ✅ **`not_observed != absent`** — already present in `rules/behavior.md §1` (comparison #3 treated it as still needed; it actually already exists).
- ✅ **`trust-metrics.md` ledger** — built, committed, has ~9 rows + an `Affects` column (IDEA-01 + part of Q3 is no longer vaporware).
- ✅ **`specs/` removed from gitignore** — mechanically removed (all that remains is the first commit + fixing the doc that says the opposite — see P2-G).
- ✅ **Doc-truth lint in CI** (`scripts/lint-doc-truth.sh`) — already catches hook-table ↔ settings.json drift + phantom path refs.
- ✅ **P1-A `verify_summary.py` — FULLY DONE.** The script re-runs `### Verify`, overwrites Exit with the real value, adds a `Verified:` timestamp, exits 1 on mismatch, has a `--check` mode; **already wired** into `commit-quality-gate.sh` (REQUIRE_VERIFY=1); has `test_verify_summary.py`. The only remaining slack: the fail-open default `REQUIRE_VERIFY=0` → belongs to P3-M.
- ✅ **P2-F SessionStart hook — DONE.** `hooks/session-knowledge.sh` is wired (SessionStart), loads `INDEX.md`+`critical-patterns.md`, silent when the store is empty. The knowledge loop is closed at the "medium" tier → the 06-08 research (compound-loop-closure) is **obsolete**.
- 🟡 **P1-B partially** — `skills/compound/templates/failure-track.md` already has a `## Guardrail` section. Still missing the tightening part (see P1-B below).

---

## 1. Consensus table (gap × number of research docs raising it)

| Gap | Research raising it | Consensus | Leverage/Effort | Rule-4? |
|---|---|---|---|---|
| **Proof is assertion, `### Verify` does not re-run** | repo-harness IDEA-02, req #3, comparison #4 | 3 | High / Medium | wiring yes |
| **Ratchet not closed — `/compound` failure yields prose, not a guardrail** | openai #3, repo-harness IDEA-05 | 2 | High / Medium | no (skill edit) |
| **"Verify the docs" — no automated drift audit yet** | openai #4, repo-harness IDEA-04/12, req #8 | 3 | High / Low | no (advisory) |
| **Review agent not structurally read-only** | comparison #2 | 1 | High / Low | no |
| **Q3: no registry contract; PROJECT.md is a placeholder** | req #1 (the only design hole) | 1 | High / Medium | no |
| **Semi-closed knowledge loop — no SessionStart auto-load** | compound-loop (whole doc), req #4 | 2 | Medium / Low | **yes** (settings.json) |
| **MCP output treated as trusted** | openai #5 | 1 | Medium / Low | light (CLAUDE.md) |
| **specs/ transition incomplete (doc says the opposite)** | req #2/#6 | 1 | Medium / Low | no |
| **No numeric evidence yet: is the harness effective?** | comparison #1/#7 | 1 | Very high / High | no (new directory) |
| **Lane→evidence mapping duplicated in 3 places** | repo-harness IDEA-10 | 1 | Medium / Medium | wiring yes |
| **Story-sizing is a guideline, not a gate** | req #5/#7 | 1 | Medium / Low | no |
| **Break-glass protected paths (Rule-4 only prompts)** | comparison #5 | 1 | Medium / Medium | **yes** (new hook) |
| **Fail-open by default (REQUIRE_VERIFY=0, STRICT=0)** | req #4/#5 | 1 | Medium / Low | **yes** |
| **VERSION/CHANGELOG for the installer** | repo-harness IDEA-15, req #6 | 2 | Low / Low | no |
| **Consolidate bash gates into 1 dispatcher + state ledger** | comparison #8/#9 | 1 | High / Very high | **yes** (overhaul) |

---

## 2. Phased plan

> **Execution status 2026-06-14:** after ground-truth, P1-A/P1-D/P2-F were already done beforehand.
> P1-B and P1-C were **executed in this session** (✅ below). Test suite + lint-doc-truth green.

### Phase 1 — Quick wins, high consensus, little/no Rule-4 (do these first)

**P1-A · ✅ ALREADY DONE PREVIOUSLY (see section 0) — `scripts/verify_summary.py` — turn proof from assertion into fact** *(IDEA-02, req #3, comparison #4)*
- **Gap:** the `Exit` column in the `### Verify` table of `SUMMARY.md` is **typed by hand** by the agent; `commit-quality-gate.sh` only does `grep -q '^### Verify'` (a presence check).
- **Action:** a script (modeled on `check_plan_format.py`) parses the `### Verify` table, re-runs each `Command` (60s timeout, from repo root), **overwrites the Exit column with the real exit code** + a `Verified: <timestamp>` line. `--all` globs `specs/*/SUMMARY.md` and prints a tally.
- **Footgun:** by default only runs the **active** slug, requires read-only/idempotent commands (avoid `alembic upgrade` side effects). Wiring into `commit-quality-gate.sh` (`REQUIRE_VERIFY=1`) is **Rule-4** → split into a separate step, ship the standalone script first.
- **Verify:** `python scripts/verify-summary.py specs/<slug>/SUMMARY.md` exits 0 on a slug whose Verify passes; test modeled on `test_check_plan_format.py`.

**P1-B · ✅ DONE (2026-06-14) — Close the ratchet: `/compound` failure proposes a guardrail, not just prose** *(openai #3 — the strongest recommendation, IDEA-05)*
- **What was done:** `solution-extractor-prompt.md` now requires the `Guardrail` field to be a buildable artifact tagged `existing:`/`proposed:` (prose/`[none]` not allowed); `compound/SKILL.md` adds a step routing `proposed:` guardrails into `docs/harness-experimental/improvement-backlog.md` (seed created); the `failure-track.md` template + inline template updated to match.
- **Gap:** the `failure` track of `/compound` writes the "Guardrail" field as prose — prompt-level, not deterministic. OpenAI: *every* agent error becomes a permanent mechanical guardrail.
- **Action:** edit `skills/compound/SKILL.md` — when writing a `failure`, require emitting a *concrete guardrail proposal*: the hook name / structural test / lint line that would block the error from recurring, together with the target file. Output becomes an entry in `docs/harness-experimental/improvement-backlog.md` (committed) for triage.
- **Verify:** run `/compound` on a session with a failure → the backlog has an entry with a non-null proposed guardrail.

**P1-C · ✅ DONE (2026-06-14) — `scripts/harness-audit.sh` — extended "verify the docs"** *(openai #4, IDEA-04/12, req #8)*
- **What was done:** an advisory script catching 3 drifts nobody covered: SUMMARY missing `### Verify`, PLAN `status:active` stale (>14d), `confirmed_at` >30d. Banded health + raw count; default exit 0 (non-blocking), `--strict` exits 1. Wired advisory-style into `harness-status.sh`. Phantom refs/hook-table are still left to `lint-doc-truth.sh` (no duplication). Manually tested, 3/3 checks fire correctly.
- **Gap:** the doc-truth lint only covers hook-table ↔ settings.json. Not yet caught: phantom references in general, SUMMARY missing `### Verify`, PLAN `status:active` with a cold Status Log, `docs/solutions` `confirmed_at` >30 days.
- **Action:** a bash+python script: (1) grep for paths that are cited but absent on disk; (2)→(4) the checks above; **weights held in data** (assoc array/json sidecar), report both the raw total and a banded value, emit JSONL into `docs/harness-experimental/audit-log.jsonl`. **Advisory, non-blocking**, wired as a line in `harness-status.sh`.
- **Verify:** `bash scripts/harness-audit.sh` exits 0 and prints a report; deliberately add 1 phantom ref → the script catches it.

**P1-D · ✅ ALREADY DONE PREVIOUSLY — review subagent read-only by structure** *(comparison #2)*
- **Ground truth:** `agents/reviewer.md` already exists, read-only (`tools: Glob, Grep, Read, Bash` — excludes Write/Edit/Agent). All 3 prompt templates (`correctness-reviewer`, `correctness-scorer`, `intent-reviewer`) already declare `subagent_type: reviewer` + an explanatory comment. Research comparison #2 ("1 config line") has been implemented more thoroughly — via a dedicated agent definition. Nothing left to do.

> **Execution status 2026-06-14 (after ground-truth):** Phase 2 was nearly all closed beforehand.
> P2-E/F/G were all already in place (the 06-11 research is obsolete); only **P2-H** was genuinely missing → done in this session.

### Phase 2 — Close the design hole + finish the half-done transitions (needs a few decisions / light Rule-4)

**P2-E · ✅ ALREADY DONE PREVIOUSLY — Close Q3 (product contract)** *(req #1 — the only design hole)*
- **Ground truth 06-14:** `skills/xia2/PROJECT.md` is genuinely filled in for this repo (Name: harness-skills, real High-Blast Files + Shared Contracts — no placeholder left); `templates/SUMMARY.template.md` already has an `Affects:` line; `/feature-intake` already asks about the contract (Step ~53, 126); the ledger already has an `Affects` column. The 06-11 research is obsolete.

**P2-F · ✅ ALREADY DONE PREVIOUSLY — SessionStart hook closes the knowledge loop** *(compound-loop, req #4)*
- **Ground truth:** `hooks/session-knowledge.sh` is wired (SessionStart), loads `INDEX.md`+`critical-patterns.md`, silent when empty. The 06-08 research (compound-loop-closure) is obsolete.

**P2-G · ✅ ALREADY DONE PREVIOUSLY — Finish the `specs/` transition** *(req #2/#6)*
- **Ground truth:** CLAUDE.md already states "specs/ is tracked in git"; `.gitignore` already ignores `specs/**/PLAN.html` + `specs/**/.plan-review.json`; the line `skills/README.md:104` "PLAN.html untracked/local-only" is **factually correct** (PLAN.html really is gitignored), not a contradiction. Nothing left to do.

**P2-H · ✅ DONE (2026-06-14) — MCP-output-untrusted note** *(openai #5)*
- **What was done:** added a "Boundary of trust (MCP output is untrusted input)" subsection to the MCP section of CLAUDE.md — treat `code-review-graph`/`context7` output as untrusted input, corroborate before acting, do not execute commands contained in the output; dovetails with `not_observed != absent`. lint-doc-truth + suite green.

### Phase 3 — Larger bets / conditional (each deserves its own spec)

**P3-I · 🟡 Infra already exists; RE-RUN complete (2026-06-14) — Review-chain micro-benchmark** *(comparison #1/#7)*
- **Ground truth:** `benchmarks/review-chain/` already exists (5 intent/diff/truth fixtures + manual protocol v1 + 06-12 baseline = 5/5, 0 FP). Not a new build.
- **What was done (re-ran the full 10-dispatch matrix with the real `reviewer` agent):** results in `results/2026-06-14-reviewer-agent.md` — **5/5 caught matching the oracle, 0 hard false positives**, ~354k tokens. **Closes caveat #2 of the baseline:** the first measurement using a structurally read-only `subagent_type: reviewer` (the old baseline only measured the prompt). No regression after P1-B/P2-H.
- **✅ Caveat #1 closed (2026-06-14):** fixed 2 intent fixtures (excess-scope, intent-gap) to be **runtime-clean v2** — added a None-guard + ownership-scoping while **preserving the planted intent defect**. Verified with 2 off-oracle correctness passes (`reviewer` agent) → both reported **CLEAN**. Fixture versioning is documented in `benchmarks/review-chain/README.md`; the expected-oracle 5/5 baseline still holds.

**P3-J · ✅ DONE (2026-06-14) — lane→evidence single source of truth** *(IDEA-10)*
- **What was done:** the validator reads `specs/<slug>/SUMMARY.md` and encodes the mapping tiny→header / normal→+real Verify / high-risk→+Rollback; tolerant of bold `**Lane:**`; accurate placeholder detection (does not confuse prose containing `|` inside backticks). Initially the validator lived in `check_lane_evidence.py`; it has now been merged into `scripts/verify_summary.py --lane`, with shared tests in `test_verify_summary.py`. The "single source of truth" pointer lives in `rules/auto-correct-scope.md`; the commit gate calls this mode directly.

**P3-K · ✅ DONE (2026-06-14) — Story-size gate** *(req #5/#7)*
- **What was done:** added `story_size_warnings()` to `check_plan_format.py` — warns (advisory, does NOT change the exit code) when a single task touches >`MAX_FILES_PER_TASK` (default 4, overridable via `PLAN_MAX_FILES_PER_TASK`). 4 tests. Steps cannot be counted mechanically (the action is prose) → only the file count is gated (structural).

**P3-L · ✅ DONE, dormant (2026-06-14) · Break-glass protected-path hook** *(comparison #5)*
- **What was done:** `hooks/protected-path-guard.sh` (PreToolUse Edit/Write) hard-blocks writes to the high-blast list (settings.json, `hooks/*`, `render_plan.py`, `run-tests.sh`, the SUMMARY template); break-glass via `PROTECTED_PATH_REASON` → writes to `break-glass-log.md`. `^hooks/` excludes `tests/hooks/`. 8 tests. **DORMANT** — not yet registered in `settings.json` (wiring is Rule-4, needs confirmation); a ⬜ row was added to the hook table in CLAUDE.md.

**P3-M · ✅ ALREADY DONE PREVIOUSLY · Raise fail-open → fail-closed in stages** *(req #4/#5)*
- **Ground truth:** `scripts/ci-strict-gate.sh` already exists + is **already wired** into `harness-ci.yml` — the strict semantics live in the script (runs on PRs when the diff touches a hard-gate path), while the local hook stays warn-by-default. Exactly the "strict-in-CI-first" shape. Nothing left to do.

**P3-N · ✅ DONE (2026-06-14) · VERSION + CHANGELOG** *(IDEA-15, req #6)*
- **What was done:** `VERSION` (0.1.0) + `CHANGELOG.md` (Keep-a-Changelog) at root; added to the installer PAYLOAD + echo `(vX.Y.Z)` at install time; an "update CHANGELOG/VERSION" step in `finishing-a-development-branch` (bump per patch/minor/major). (The old plan said "only when there is a second consumer" — the user asked to do it now to close the backlog.)

**P3-O · Consolidate bash gates into 1 dispatcher + state ledger** *(comparison #8/#9)* — an overhaul, **Rule-4**, lowest priority; only when the hook count/brittleness genuinely hurts.

---

## 3. Recommended execution order

1. **Phase 1 first** (P1-A → P1-D): highest consensus, little/no Rule-4, reuses existing precedent. P1-C (audit) should be done early because it automatically catches drift for everything that follows.
2. **Phase 2** after P1 settles: P2-E closes the Q3 design hole; P2-F/G/H need small decisions (light Rule-4).
3. **Phase 3** — one spec per item; P3-I (benchmark) is the most valuable long-term investment but the heaviest.

**Not doing:** importer/migration (IDEA-11), making the Codex/Cursor mirrors agnostic, approval-gated loop, memory daemon — the research all concluded these are a non-fit for a one-person dogfood.
