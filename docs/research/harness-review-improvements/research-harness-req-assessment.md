# Research: the `harness-skills` repo against REQ.md — what it satisfies, what is missing, what to improve

> **Question:** How much of "The Harness Approach" (REQ.md) does the current repo satisfy?
> What is missing, what should be improved to make it more trustworthy, and which structural
> limitations need to be addressed?
> **Date:** 2026-06-11
> **Method:** 2 agents surveying in parallel (inventory + adversarial gap audit) across all of
> skills/ hooks/ rules/ templates/ tests/ docs/, followed by in-place verification of the contradictory
> points (PROJECT.md, ledger, defaults, test coverage). Builds on 2 prior research documents:
> `research-compound-loop-closure.md` (2026-06-08) and `research-repository-harness-ideas.md` (2026-06-09).
> **Verification note:** one finding from the audit agent ("CI does not test hook behavior") was rejected —
> `tests/hooks/` contains a full set of 10 behavioral test files; the ledger `docs/harness-experimental/trust-metrics.md`
> already exists, is git-tracked, and holds 5 rows of real data (unlike the vaporware state recorded on 2026-06-09).
> **Same-day update (after owner feedback):**
> (1) This is the **source repo** that creates/sets up the harness — an empty `docs/solutions/` is the expected state
> (entries are generated in consumer repos or through dogfooding), not a defect.
> (2) `specs/` **has been removed from `.gitignore`** (`#specs/`) — the "audit trail does not persist" finding
> is mechanically resolved; what remains is the initial commit plus updating the docs that still assert the opposite
> (`CLAUDE.md:61`, `rules/plan-format.md:125`) and the decision on whether to separately ignore `PLAN.html`.

---

## Source questions (from REQ.md, deleted 2026-07-17)

> REQ.md was removed as a stale stub (issue #67 Phase 2, wave 1). Its six harness
> questions — the subject this assessment scores against — are preserved verbatim:
>
> - What should I read first?
> - What type of work is this?
> - Which product contract does it affect?
> - How risky is the change?
> - What proof will show the work is done?
> - What decision or lesson should future agents inherit?

---

## 1. TL;DR

- **Score across the 6 REQ.md questions: 4/6 answered well.** Strongest are *"How risky?"* (Q4) and
  *"What type of work?"* (Q2) — there is a classifier plus machine-enforced hook corroboration. Weakest are
  *"Which product contract does it affect?"* (Q3 — **no mechanism answers it**) and
  *"What lesson should future agents inherit?"* (Q6 — the machinery is built but the **store is empty and the loop is half-closed**).
- **The biggest gap between design and reality:** the enforcement infrastructure (hooks, CI, tests, ledger) has
  matured considerably, but **the data layer has not been loaded**. For `docs/solutions/` and
  `agent-memory/` this is *expected* (source repo — data is generated in consumer repos); the real remaining
  consequences are that the `/compound` pipeline **has not been validated end-to-end with real data**, and
  `xia2/PROJECT.md` is still a placeholder template for this very repo.
- **The two most important gates currently fail open by default** (`REQUIRE_VERIFY=0`,
  `RISK_CORROBORATION_STRICT=0`). The strict-default in particular is a **deliberate decision recorded in the ledger**
  ("strict-default decision: keep warn", slug `p3-hook-fixes`) — not a bug, but a tradeoff
  worth revisiting once the harness leaves the dogfood phase.
- **Proof is currently assertion, not fact:** the `Exit` column in the `### Verify` table is typed by hand by the agent,
  with nothing re-running it. Removing `specs/` from gitignore (2026-06-11) resolves the *persistence* half —
  proof artifacts can now be committed — but the *machine-verified* half (re-running the Verify commands) is still open.

---

## 2. What the repo already satisfies (against the 6 REQ.md questions)

| # | REQ.md question | Answering mechanism | Enforcement level | Assessment |
|---|---|---|---|---|
| Q1 | What should I read first? | `CLAUDE.md` auto-load + `@`-import of `rules/behavior.md`, `skills/README.md`; pointer to `docs/solutions/critical-patterns.md`; `agents/PROJECT.md` for execution agents | Document/convention — the pointer surfaces itself, **the content does not auto-load** | ✅ Decent — the entry doc is clear, but it depends on the model following the pointer |
| Q2 | What type of work is this? | `/feature-intake`: 6 input types, 10-flag checklist, 3 lanes (tiny/normal/high-risk) + confidence → written to `specs/<slug>/SUMMARY.md` | **Hook-corroborated** — `risk-corroboration.sh` blocks the commit when the diff trips a hard gate while Lane < high-risk | ✅ The strongest part of the system |
| Q3 | Which product contract does it affect? | Only indirectly: the High-Blast Files / Shared Contracts section in `xia2/PROJECT.md` | **None** — PROJECT.md is a placeholder; the SUMMARY template has no contract/module field; intake never asks | ❌ Not answered |
| Q4 | How risky is the change? | 10 flags + hard gates (intake) · `risk-corroboration.sh` · `blast-radius-check.sh` · `branch-guard.sh` · Rules 1–4 of `auto-correct-scope.md` | Hooks can block — **but fail open when Lane is missing** (unless `RISK_CORROBORATION_STRICT=1`) | ✅ Strong, with a default-state hole |
| Q5 | What proof will show the work is done? | The `### Verify` table (SUMMARY) · per-task `<verify>` (PLAN.md, <60s, exit-0) · `TEST_MATRIX.md` · `commit-quality-gate.sh` (secrets + debug + targeted pytest) | Partial — the targeted pytest really runs; but the `### Verify` check is **opt-in** (`REQUIRE_VERIFY=1`) and only greps for presence, **it does not re-run the commands** | ⚠️ Medium — proof is self-reported |
| Q6 | What lesson should future agents inherit? | `/compound` (4 tracks: bug/knowledge/decision/failure) · `docs/solutions/` schema + INDEX · `critical-patterns.md` · the `trust-metrics.md` ledger (committed, 5 rows) · `agent-memory/` confidence decay | Pull-only — `/xia2` and `/brainstorming` do read back, **there is no SessionStart auto-load** | ⚠️ Good design; the empty store is expected (source repo) but the pipeline is unvalidated in practice, and the loop is half-closed |

### Against the 5 failure modes REQ.md wants to prevent

| Failure mode (REQ.md) | Prevented? | How |
|---|---|---|
| Agent edits code before understanding intent | ✅ mostly | `/feature-intake` is required to run first; `scope-gate.sh` warns on a prompt with implementation intent and no plan (but it only warns, it does not block) |
| Constraints live only in chat | ✅ mostly | `rules/` + `CLAUDE.md` are committed; the SUMMARY/ESCALATIONS templates turn decisions into artifacts; `specs/` is no longer ignored (06-11) so per-task constraints can now persist — the initial commit is still needed |
| Vague validation expectations / late detection | ⚠️ half | per-task `<verify>` + `### Verify` + TEST_MATRIX provide the shape; but REQUIRE_VERIFY is off by default and nothing is re-run |
| Architectural tradeoffs repeated instead of inherited | ❌ not yet | The `/compound` → `docs/solutions/` mechanism exists, but there are 0 entries, 0 critical patterns, and the loop is pull-only |
| Large requests not broken into story-sized pieces | ⚠️ half | `plan-format.md` has thresholds (>3 steps / >2 files / >30min) + wave-parallelism + `check_plan_format.py` validating **format**; but the size thresholds are prose only, nothing checks them |

### Infrastructure already in place (a significant plus)

- **9 hooks wired** + 1 dormant, and the hook table in CLAUDE.md **matches** `settings.json` (verified).
- **Real tests:** 10 hook behavior test files (`tests/hooks/*.test.sh`), 2 script tests, pytest for
  `check_plan_format` / `render_plan` / feature-intake canaries; CI `harness-ci` runs on ubuntu+macos
  including the **doc-truth lint** (fails when a doc references a nonexistent path — precisely the cure for the 06-09 drift episode).
- **The `trust-metrics.md` ledger is built, committed, and holds data** — the biggest gap from the 06-09 research
  (IDEA-01) has been closed at a lightweight tier.
- 14 skills covering the full lifecycle: intake → brainstorm → research → plan → execute → review → compound → ship.

---

## 3. What the repo is missing

Ordered by severity:

1. **(High) Q3 has no solution — there is no contract/domain registry.**
   The SUMMARY template has Lane/Confidence/Reason/Flags but no "affected contract/module" field;
   intake does not ask; `xia2/PROJECT.md` (the place designed to declare High-Blast Files + Shared Contracts)
   **is still the `<your project name>` placeholder for this very repo** → `/xia2` loses its main signal source,
   and PROJECT-CONFIG-GATE should be halting.
2. **(High → half resolved on 06-11) Proof is not re-run; persistence is unlocked but incomplete.**
   `specs/` has been removed from `.gitignore` → SUMMARY/PLAN/ESCALATIONS/STATE/TEST_MATRIX can be committed
   (10 slugs + STATE.md are currently untracked, awaiting the initial commit). What remains: (a) the Exit column in
   `### Verify` is still self-declared by the agent, with no mechanism re-running it (IDEA-02 not done); (b) 2 tracked docs
   still assert the opposite — `CLAUDE.md:61` ("specs/ is fully gitignored") and `rules/plan-format.md:125`;
   (c) a decision is needed on whether to separately ignore derived artifacts (`PLAN.html`).
3. **(Downgraded: expected for a source repo) The knowledge store is empty.** `docs/solutions/INDEX.md` has 0 entries,
   `critical-patterns.md` says "none yet", `agent-memory/` has only a README — **this is the correct state for a
   source repo**: the data is generated in repos that consume the harness, or through dogfooding. Two real consequences remain:
   (a) the `/compound` pipeline (collision handling, severity triage, INDEX rebuild) **has never run with
   real data** and is therefore unvalidated end-to-end; (b) the read-back loop is still half-closed in every repo
   the harness is deployed to (pull-only via `/xia2`/`/brainstorming`, no SessionStart hook — the 06-08 conclusion
   still holds in full and applies to consumers).
4. **(Medium) The two main gates fail open by default.** `REQUIRE_VERIFY=0` (evidence check off) and
   `RISK_CORROBORATION_STRICT=0` (a diff that trips a hard gate *without a declared Lane* → warn only). Noted:
   keep-warn is a deliberate decision in the ledger — but it means the last safety layer depends on
   the agent's discipline in declaring the Lane.
5. **(Medium) Story sizing is a guideline, not a gate.** The >3 steps / >2 files thresholds are not checked by
   any script; a 10-file, 1-wave plan still sails straight through.
6. **(Medium) No version/changelog for the distributed payload.** `install-harness.sh` pins `main`, so
   consumers silently receive HEAD (IDEA-15, not done).
7. **(Low) `auto-test-on-change.sh` is dormant** — test feedback is pushed back to commit time.
8. **(Low) `scope-gate.sh` is advisory only** — nothing *forces* `/feature-intake` to run first; the whole
   workflow routing depends on the model complying with the prompt.

---

## 4. What to improve to make it more trustworthy (descending priority)

1. **Run `/bootstrap-xia2` to fill in `xia2/PROJECT.md` for this very repo** — the cheapest move, and it unlocks Q3+Q4:
   declare the real High-Blast Files (`settings.json`, `hooks/*`, `skills/visual-planner/render_plan.py`…) and
   Shared Contracts (the SUMMARY schema, ledger columns, hook exit-code contract).
2. **Add an `Affects:` field (contract/module) to `templates/SUMMARY.template.md` plus an asking step
   in `/feature-intake`** — a direct answer to Q3; add a matching ledger column so it becomes queryable.
3. **`scripts/verify-summary.py` (IDEA-02): re-run the `### Verify` table and overwrite the Exit column with the real exit
   code** — turning proof from assertion into fact. There is already a precedent for the shape (`check_plan_format.py` + tests).
   Footgun note: only run the active slug, and require idempotent commands; modifying `commit-quality-gate.sh` is Rule-4.
4. **Close the knowledge loop:** a SessionStart hook printing `INDEX.md` + `critical-patterns.md` (the "medium" tier
   from the 06-08 research). Rule-4 (touching `settings.json`) → needs human confirmation. In parallel:
   start *actually running* `/compound` after sessions that produced a lesson — the read infrastructure exists, it is starved of data.
5. **Gradually raise fail-open → deliberate fail-closed:** turn on `REQUIRE_VERIFY=1` +
   `RISK_CORROBORATION_STRICT=1` **in CI first** (safe, does not block local dev), measure the breakage rate
   through the ledger for a few weeks, and only then consider enabling it locally. Respect the existing keep-warn decision —
   this is a staged upgrade proposal, not a reversal of that decision.
6. **Finish opening up specs/ (ignore removed on 06-11):** (a) make the initial commit of the 10 slugs + STATE.md that are
   untracked; (b) fix the 2 docs that still assert the opposite (`CLAUDE.md:61` Gotchas section,
   `rules/plan-format.md:125`) — and sweep the skills describing "PLAN.html untracked/local-only"
   (`skills/README.md`, `visual-planner`); (c) decide on separately ignoring derived artifacts
   (`specs/**/PLAN.html`) to avoid committing an HTML file that can be rebuilt from PLAN.md.
7. **A story-size gate:** extend `check_plan_format.py` to count `<files>`/steps per task and warn when
   the `plan-format.md` threshold is exceeded — turning a prose threshold into a runnable check.
8. **Self-detecting drift:** `scripts/harness-audit.sh` (IDEA-04/12 merged) periodically checking phantom references —
   the doc-truth lint in CI covers part of this; the rest is SUMMARYs missing Verify, an active PLAN whose
   Status Log has gone cold, and solutions with `confirmed_at` >30 days.
9. **VERSION + CHANGELOG for the installer** (IDEA-15) once a second consumer appears.

---

## 5. Structural limitations & how to address them

| Limitation | Nature | Remedy |
|---|---|---|
| **Enforcement by prompt** — skills are markdown; lane mapping, escalation, and the subagent contract are all prose the model is *supposed* to follow | Inherent to a prompt framework; the model can skip any step that has no blocking hook | Keep pushing load-bearing checks down into hook/script exit codes (good precedents: `check_plan_format.py`, `risk-corroboration.sh`, the doc-truth lint). Priority: lane→evidence mapping (IDEA-10) so the 3 prose copies get one runnable source of truth |
| **`specs/` used to be local-only** — the ignore was removed 2026-06-11, but the transition is incomplete | The root limitation is mechanically resolved; the remaining risk is the half-done state (slugs uncommitted, docs saying the opposite) | Make the initial specs/ commit; fix `CLAUDE.md:61` + `rules/plan-format.md:125`; separately ignore the derived `PLAN.html`; the ledger remains the cross-slug aggregation layer |
| **Hook detection by grep/regex** — there have been real false positives (ledger: "corroboration regex false-positive on tests/hooks/" ×2) | Regex over a diff does not understand semantics; both false positives and false negatives will keep occurring | The direction is already right (precision fixes + 10 behavioral tests). Accept this as a coarse net — do not tune it infinitely; the compensating layer is adversarial review (`/correctness-review`) |
| **The knowledge loop depends on someone invoking the skill** — `/compound` does not self-run, solutions do not auto-load | "Pointer auto, content on-demand" | A SessionStart hook (section 4.4); a reminder trigger for `/compound` already exists (the commit hook hint at ≥5 app/ files) but has never had occasion to fire — track it through the ledger |
| **Single-person, Claude-Code-only dogfooding** — untested across multiple agents/machines/consumers | Every trust number so far comes from 1 user; fail-open is acceptable *because* there is only 1 disciplined user | Do not rush to make it agnostic (the 06-09 conclusion still holds). When a 2nd consumer appears: HARNESS.md into the installer payload + marked-block (IDEA-14/13) + VERSION |
| **The knowledge pipeline is untested in practice** — an empty store is expected for a source repo, but the consequence is that `/compound`'s collision handling, severity triage, and INDEX rebuild have never run against real data | The design has not been validated end-to-end before being deployed to consumers | Dogfood `/compound` right here in the source repo for recent harness sessions (all 5 slugs in the ledger have a lesson worth recording — e.g. the keep-warn decision, the regex false positive) — this both smoke-tests the skill and produces a sample corpus for consumers |

---

## 6. Conclusion

This repo **has moved past the "loose collection of prompts" stage**: there is a real intake classifier, machine-enforced
commit gates, tests + CI for the harness itself, a committed ledger, and (since 06-11) `specs/` that can persist — meaning
4 of the 6 REQ.md questions have an answering mechanism, with Q2/Q4 at a level rarely seen in a prompt framework.
Because this is a **source repo**, an empty knowledge store is not a defect; three things will determine trustworthiness in the
next phase: **(1) finish the specs/ transition** (initial commit + fix the docs that say the opposite + ignore the derived
PLAN.html), **(2) move proof from self-reported to machine-verified** (re-run Verify, raise strict
in stages), and **(3) dogfood `/compound` + fill in `xia2/PROJECT.md`** so the knowledge pipeline is
validated before consumers rely on it. Question Q3 (product contract) is the one design hole
with no mechanism at all — it needs an added field plus a filled-in PROJECT.md, not a new system.
