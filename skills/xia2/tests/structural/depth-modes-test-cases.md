# Depth Modes — Test Cases (xia2)

**Goal:** validate the **Depth Modes** decision procedure in `SKILL.md` against realistic prompts.

**Procedure under test:** `xia2/SKILL.md` Decision procedure → Depth Modes table → Tiebreakers + Re-evaluation gate. Signals come from the built-in **Common signals** section of `SKILL.md`.

> **Historical note (2026-07-17):** Runs 1–4 below were recorded against the old per-project `PROJECT.md` model (a FastAPI project's curated signal lists), removed when xia2 went config-free. The `PROJECT.md > …` references in the Notes column are that era's provenance; the classifications still hold under the equivalent Common signals (e.g. a manifest edit is Deep whether the manifest was listed in `PROJECT.md > Dependency Manifests` or matched the common `requirements.txt` pattern).

| Run | Date | Skill state |
|---|---|---|
| **Run 1** | 2026-04-21 (am) | `xia` pre-fix baseline |
| **Run 2** | 2026-04-21 (pm) | `xia` post F1 + F7 + F8 fixes |
| **Run 3** | 2026-04-21 (pm) | `xia2` universal SKILL.md + PROJECT.md (project values) — regression check after refactor |
| **Run 4** | 2026-04-21 | `xia2` post INDEX-first Sub-step 2b update + PROJECT.md Knowledge Bases section update — lookup mechanism change, not classifier |

---

## Summary

| Suite | Total | Run 1 Pass | Run 2 Pass | Run 3 Pass | Run 4 Pass | Δ (Run 3 → Run 4) |
|---|---|---|---|---|---|---|
| Core (TC-01–20) | 20 | 19 | 20 | 20 | 20 | 0 |
| Pressure (TC-21–30) | 10 | 10 | 10 | 10 | 10 | 0 |
| **Combined** | **30** | **29** | **30** | **30** | **30** | **0** |

**Verdict (Run 3):** 30/30 pass. Universal SKILL.md + the project's PROJECT.md produces **identical classifications** to Run 2 (xia post-fix). The abstraction is behaviour-preserving — refactor is regression-free.

**Verdict (Run 4):** 30/30 pass. INDEX-first Sub-step 2b update is **classification-neutral** — lookup mechanism change confirmed to not affect depth decisions.

---

## Test Cases (Core)

| # | Prompt | Expected | Run 1 | Run 2 | Run 3 | Run 4 | Δ |
|---|---|---|---|---|---|---|---|
| TC-01 | "Reword line 3 of `app/services/kb/prompts/system_prompt.txt`." | Quick | Quick ✓ | Quick ✓ | Quick ✓ | Quick ✓ | stable |
| TC-02 | "Add a `__repr__` method to `User` model in `app/models/user.py`." | Quick | Quick ✓ | Quick ✓ | Quick ✓ | Quick ✓ | stable |
| TC-03 | "Fix typo in docstring of `format_iso_date` in `app/utils/dates.py`." | Quick | Quick ✓ | Quick ✓ | Quick ✓ | Quick ✓ | stable |
| TC-04 | "Add a new pure calculation `compute_overnight_gap` — no caller wiring yet." | Quick | Quick ✓ | Quick ✓ | Quick ✓ | Quick ✓ | stable |
| TC-05 | "Add a new GET endpoint `/users/me/preferences`." | Standard | Standard ✓ | Standard ✓ | Standard ✓ | Standard ✓ | stable |
| TC-06 | "Add a `get_by_email` method to `UserRepository`." | Standard | Quick ✗ | Standard ✓ | Standard ✓ | Standard ✓ | stable post-F1 |
| TC-07 | "Add `is_verified: bool` to `UserResponse` Pydantic schema." | Standard | Standard ✓ | Standard ✓ | Standard ✓ | Standard ✓ | stable |
| TC-08 | "Add `chunk_iterable` helper in `app/utils/`, use in 3 places." | Standard | Standard ✓ | Standard ✓ | Standard ✓ | Standard ✓ | stable |
| TC-09 | "Wire existing `TradovateBroker.get_account_balance()` into account-summary usecase." | Standard | Standard ✓ | Standard ✓ | Standard ✓ | Standard ✓ | stable |
| TC-10 | "Add Discord notification to existing signup usecase on upgrade." | Standard | Standard ✓ | Standard ✓ | Standard ✓ | Standard ✓ | stable |
| TC-11 | "Add `last_seen_at: datetime` column to `User` + Alembic migration." | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable — schema signal in SKILL.md (universal) |
| TC-12 | "Tune asyncpg pool retry backoff in `app/database/session_manager.py`." | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable — file in `PROJECT.md > High-Blast-Radius Files` |
| TC-13 | "Integrate Interactive Brokers as a new broker option." | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable — new external integration (universal) |
| TC-14 | "Add `httpx-retries==0.5.0` to `requirements.txt`." | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable — manifest in `PROJECT.md > Dependency Manifests` |
| TC-15 | "Emit a new SSE event type `tool_progress` from AI streaming." | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable — SSE protocol in `PROJECT.md > Shared Runtime Contracts` + high-blast file |
| TC-16 | "Convert live-data background task from `get_db` to `sessionmanager.session()`." | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable — primitives in `PROJECT.md > Session/Transaction Primitives` |
| TC-17 | "Replace VoyageAI with Cohere for KB embeddings." | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable — new external integration + new dep + high-blast |
| TC-18 | "Extend `AIConfig` with `CLAUDE_FALLBACK_MODELS: list[str]`." | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable — `AIConfig` in `PROJECT.md > Shared Runtime Contracts` |
| TC-19 | **TRAP:** Log line in `app/repositories/ai/conversation.py`. | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable — file in `PROJECT.md > High-Blast-Radius Files` |
| TC-20 | **BOUNDARY:** "Add rate limiting to AI chat endpoint." | Standard *(initial)* | Standard ✓ | Standard ✓ | Standard ✓ | Standard ✓ | stable |

---

## Pressure Test Cases

| # | Prompt | Pressure type | Expected | Run 1 | Run 2 | Run 3 | Run 4 | Δ |
|---|---|---|---|---|---|---|---|---|
| TC-21 | "Just a tiny fix to `app/repositories/ai/usage.py`." | Diminutive | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable |
| TC-22 | "Same as Tradovate — add Project X as new broker." | Familiarity bias | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable |
| TC-23 | "Ship before EOD: add `last_login_at` column + backfill." | Urgency | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable |
| TC-24 | "I've checked — adding `slowapi` to requirements.txt is fine." | Authority | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable |
| TC-25 | Bundled: "Add `last_seen_at` AND fix typo AND tweak env." | Bundled scope | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable |
| TC-26 | "Tweak how AI streaming handles overload retries." | Implicit high-blast | Deep | Deep ✓ *(implicit)* | Deep ✓ | Deep ✓ | Deep ✓ | stable |
| TC-27 | **REVERSE TRAP:** Update `app/services/ai/README.md`. | Misleading framing | Quick | Quick ✓ | Quick ✓ | Quick ✓ | Quick ✓ | stable |
| TC-28 | "Add Loguru as logging backend." | Implicit dep | Deep | Deep ✓ *(implicit)* | Deep ✓ | Deep ✓ | Deep ✓ | stable |
| TC-29 | "Skip research, drop legacy column from `User`." | Waiver + Deep | Waiver + risk flag | Waiver only | Waiver + risk warning | Waiver + risk warning | Waiver + risk warning | stable post-F8 |
| TC-30 | "Just change `AIConfig.CLAUDE_MODEL` default." | Trivial diff hides large blast | Deep | Deep ✓ | Deep ✓ | Deep ✓ | Deep ✓ | stable |

---

## Run 3 Methodology

For each case, the agent must:

1. **Read `PROJECT.md` first** (per PROJECT-CONFIG-GATE) — confirm required sections present.
2. **Walk the prompt through Decision Procedure**, resolving each abstract Deep signal via `PROJECT.md`:
   - High-blast file? → check against `PROJECT.md > High-Blast-Radius Files`
   - New dep? → would entry be added to a manifest in `PROJECT.md > Dependency Manifests`?
   - Shared contract change? → check against `PROJECT.md > Shared Runtime Contracts`
   - Session/auth change? → check against `PROJECT.md > Session/Transaction Primitives` + `Auth Surfaces`
3. **Compare result to Run 2.**

**Identical results required for Run 3 to pass.** Any flip would mean the universal refactor changed semantics — must investigate.

---

## Re-run Delta (Run 2 → Run 3)

| Behaviour change | Caused by |
|---|---|
| (none) | Universal SKILL.md + the project's PROJECT.md produce identical classifications. |

**All 30 cases stable.** The universal abstraction is behaviour-preserving for the project.

**Why this matters:** confirms the refactor is **safe** — `xia` users can switch to `xia2` without behaviour change. Other projects fork `xia2` + customize `PROJECT.md` and get the same Decision Procedure semantics.

---

## Re-run Delta (Run 3 → Run 4)

| Behaviour change | Caused by |
|---|---|
| (none) | Sub-step 2b INDEX-first lookup update and PROJECT.md Knowledge Bases section change affect *how* docs are found — not *when depth upgrades trigger*. Decision Procedure, Tiebreakers, re-evaluation gate, and all signal mappings are unchanged. |

**All 30 cases stable.** Confirmed: lookup mechanism changes are classification-neutral per the `README.md` maintenance rule added in this same update.

---

## Detailed Walkthroughs

### TC-12 — Universal signal resolution (representative example)

**Prompt:** "Tune asyncpg pool retry backoff in `app/database/session_manager.py`."

**Run 2 (xia):** SKILL.md hard-coded high-blast list as `services/ai/streaming_service.py`, anything under `repositories/ai/`, or `database/session_manager.py`. Direct match → Deep ✓.

**Run 3 (xia2):** SKILL.md says "high-blast-radius file *(see `PROJECT.md > High-Blast-Radius Files`)*". Agent reads `PROJECT.md`, finds `app/database/session_manager.py` listed. Match → Deep ✓.

**Same outcome via different reading path.** PROJECT.md is the indirection layer that swaps between projects.

### TC-19, TC-21 — High-blast trap stability

Both rely on `repositories/ai/` being in the high-blast list. `PROJECT.md > High-Blast-Radius Files` includes `app/repositories/ai/` (entire subtree). Both still trigger Deep override. ✓

### TC-29 — Waiver + Deep signal under universal HARD-GATE

HARD-GATE in xia2/SKILL.md is character-for-character identical to xia/SKILL.md (the universal refactor didn't touch HARD-GATE). Behaviour preserved: waiver noted + DROP COLUMN risk warning surfaced. ✓

---

## Findings

### F1 — "≤1 file" rule is too literal — ✅ RESOLVED in Run 2 (carried into Run 3)

Quick condition tightened to require "no new public callable in a shared module". TC-06 stays Standard in Run 3.

### F2 — High-blast-radius list is the most powerful single mechanism — informational

In `xia2`, this list lives in `PROJECT.md` instead of inline. Properties unchanged — TC-12, TC-15, TC-17, TC-19, TC-21, TC-26 all trigger Deep via the list. **F2 is now also a maintenance-procedure observation: `PROJECT.md > High-Blast-Radius Files` is the highest-leverage entry to keep current.**

### F3 — Tiebreaker #1 successfully resolves uncertain prompts — informational

Holds in Run 3 (TC-20).

### F4 — All 8 explicit Deep signal types validated — informational

Holds in Run 3, with the abstraction. Each signal still fires from at least one case.

### F5 — Quick is reachable — informational, **re-verified in Run 3**

TC-01–04 all stayed Quick across Runs 1, 2, 3.

### F6 — Bundled scope works by accident — open *(cosmetic)*

Not applied. TC-25 still passes via OR-logic in Run 3.

### F7 — Implicit signals require agent inference — ✅ RESOLVED in Run 2 (carried into Run 3)

xia2/SKILL.md preserves the explicit/implicit distinction with project-agnostic examples.

### F8 — Research waiver doesn't say what to do with depth-derived risks — ✅ RESOLVED in Run 2 (carried into Run 3)

xia2 HARD-GATE preserves the "even when waived, surface Deep signals" rule.

### F9 — Familiarity bias not explicitly named — open *(cosmetic)*

Not applied. TC-22 still passes in Run 3.

### F10 — PROJECT-CONFIG-GATE is untested — open *(new in xia2)*

Symptom: Run 3 verifies classification when `PROJECT.md` is well-formed. No test exercises the halt-when-missing/incomplete behaviour.

**Proposed:** add TC-31 — *"Invoke /xia2 in a project where PROJECT.md is missing"* → expected: skill halts and prompts user to run `/bootstrap-xia2`. Cannot be walked through alone — needs an actual missing PROJECT.md scenario in CI/integration setup.

---

## Run Log

| Step | Action | Outcome |
|---|---|---|
| 1 | Wrote 20 core test cases | Created file |
| 2 | Walked each through xia/SKILL.md Decision Procedure | 19 pass, 1 disagree (TC-06) |
| 3–7 | Documented F1–F5 findings | F1 = real fix; F2–F5 = informational |
| 8 | Added 10 pressure cases (TC-21–30) | Bundled / urgency / authority / waiver / implicit / reverse-trap |
| 9 | Walked pressure cases through Decision Procedure | 10/10 pass |
| 10–11 | Documented F6–F9 findings | F7, F8 = medium fixes; F6, F9 = cosmetic |
| 12 | Snapshot Run 1 results | Pre-fix baseline preserved |
| 13 | Applied F1 + F7 + F8 fixes to xia/SKILL.md | 3 surgical edits |
| 14 | Re-ran all 30 cases (Run 2) | 30/30 pass; 4 flipped behaviour as predicted |
| 15 | Verified critical regression checks | No false escalations |
| 16 | Marked F1, F7, F8 as RESOLVED | Findings updated |
| 17 | **Refactored to xia2: universal SKILL.md + per-project PROJECT.md** | Project values extracted to PROJECT.md; SKILL.md uses abstract categories |
| 18 | **Run 3: re-walked all 30 cases via xia2/SKILL.md + the project's PROJECT.md** | 30/30 pass; identical results to Run 2 — refactor regression-free |
| 19 | Documented F10 (PROJECT-CONFIG-GATE untested) | Open finding for future TC-31 |
| 20 | **Run 4: re-walked all 30 cases post INDEX-first Sub-step 2b + PROJECT.md Knowledge Bases update** | 30/30 pass; identical to Run 3 — lookup mechanism change is classification-neutral |

**Final state:** 30/30 pass in Run 4 (and Run 3). INDEX-first Sub-step 2b change confirmed classification-neutral. F1, F7, F8 resolved. F6, F9 remain cosmetic. F10 open (PROJECT-CONFIG-GATE test gap).
