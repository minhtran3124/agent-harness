# Research: `hoangnb24/repository-harness` — which ideas we should adopt

> **Source:** https://github.com/hoangnb24/repository-harness (clone HEAD, tag `harness-cli-v0.1.9`)
> **Date:** 2026-06-09
> **Method:** clone the repo, 25 agents reading each subsystem in parallel (Rust CLI, SQLite durable layer,
> trace/scoring, evolution infra, intake lifecycle, distribution), map against this repo, each idea
> passed through a skeptic for rebuttal before synthesis. 16 ideas extracted → scored with an adopt/adapt/skip verdict + fit_score.
> **On-the-spot verification (commands actually run):** `specs/` is gitignored; `docs/solutions/` and `docs/harness-experimental/`
> do not exist on disk despite being referenced in many places; the 4 standalone skills in `skills/README.md` are phantoms;
> `validate-buzz-commands.sh` is a phantom; `render-plan-on-write.sh` is on disk + firing but missing from the CLAUDE.md hook table.

---

## 1. TL;DR

- **Their repo is essentially a distributed PRODUCT, agent-agnostic**: a **compiled Rust CLI** (clap + embedded SQLite via rusqlite) wrapped in a 4-layer clean architecture, installed via `curl | bash` into any repo, with CI cross-compiling for 5 platforms, SHA256 checksums, and auto-changelog/tag on every PR. This is a **tool**, not a prompt set.
- **The biggest strategic difference — in one sentence**: they are **durable + measured + portable** (state in a queryable DB, quality *scored* and *gated by exit code*, installable into any repo/agent); we are **prompt + file + bespoke** (markdown skills, gitignored markdown state, Claude-Code-specific, single-user dogfood).
- **Their strongest idea — the "entropy score"**: a single harness-health number 0–100 (lower = better) aggregated from 6 weighted drift signals (orphaned story×10, broken tool×8, unverified×5, stale×3...). We have **no single number** that answers "is our process rotting?".
- **Second most valuable idea — executable verify**: `verify_command` stored *on the record*, **re-run** by the CLI (`story verify` / `verify-all`), recording pass/fail + timestamp, exiting 1 on failure. Our `### Verify` table is just an exit code **typed by hand**, never re-run.
- **An honest warning throughout**: most of that machinery (≈2,700 lines of `infrastructure.rs`, a hand-written JSON serializer, a hardcoded registry, score-context with doc paths hard-embedded in Rust) is **over-engineering for a one-person dogfood**. Many scoring rubrics hard-embed their repo layout into compiled Rust → they rot on their own when docs move, which is exactly the entropy the tool is meant to detect.
- **On-the-spot verification exposes drift bugs in OUR OWN repo**: `docs/solutions/` and `docs/harness-experimental/` (the trust-metrics ledger) **do not exist on disk** despite being referenced by CLAUDE.md/skills/`harness-status.sh`; the 4 standalone skills in `skills/README.md` are not real; `render-plan-on-write.sh` is on disk but **missing** from CLAUDE.md's hook table; `validate-buzz-commands.sh` is listed but does not exist. This is exactly the "broken registry / over-claiming" a maturity audit would catch.

## 2. How this repo differs from us

| Axis | Them (`repository-harness`) | Us (`harness-skills`) |
|---|---|---|
| Nature | Compiled Rust CLI + SQLite | Skill = markdown prompt (`/skill-name`) |
| State | `harness.db` — 7 typed tables, FKs, CHECK enums, WAL, queryable (`query sql`) | Gitignored markdown under `specs/<slug>/` — no schema, no query, does not survive a clone |
| Cross-task aggregation | JOIN/GROUP BY over the whole history | Each slug is an island; grep is all you get |
| Verification | `verify_command` stored on the record, **re-run**, recording pass/fail+timestamp, exit 1 | Hand-typed `### Verify` table; the hook only `grep`s for presence, never re-runs |
| Record quality | `score_trace` 0–3 tiers by lane, **exit 1** if below requirement | Subagent contract = prose, nobody parses completeness |
| Harness health | `audit` → entropy 0–100 + 6 drift queries + violation IDs | No number; only the "30 days = stale" convention, which nobody computes |
| Self-improvement | `propose` counts repeated friction (≥2), confidence by count, writes a backlog | `/compound` = an LLM reading one session's transcript, no cross-session counting |
| Lane mapping | Pure Rust function, unit-tested (tiny→Minimal...) | Prose in `feature-intake/SKILL.md`; only `risk-corroboration.sh` regex-gates it |
| Tool registry | Queryable manifest, arg schema, `since`, broken-tool check | Prose table in README/CLAUDE.md — already drifted from disk |
| Distribution | `curl|bash` + PowerShell, CI release for 5 platforms, checksums, auto-changelog/tag | We have `install-harness.sh`/`deploy-harness.sh`; **no** CI, no version, no changelog, no tags |
| Entry doc | Vendor-neutral `AGENTS.md` + a `--claude` bridge importing into CLAUDE.md | Hardwired to Claude-Code; entry is CLAUDE.md; no `AGENTS.md` (only `HARNESS.md`) |
| Users | A product for many agents/contributors (Claude/Codex/Cursor) | One-person dogfood, Claude-Code only |

## 3. Ideas we should ADOPT

> No idea earns a pure "adopt-as-is" verdict — they are fundamentally a compiled tool, we are markdown. Every valuable idea is an **ADAPT** (section 4). This section is honestly empty: **we should not lift any of their mechanisms verbatim**, because every mechanism assumes a DB/binary that we deliberately do not have.

## 4. Ideas we should ADAPT (ordered by descending fit_score)

### IDEA-02 — `verify_command` stored + re-runnable (fit 72)
**The real gap:** `commit-quality-gate.sh` only does `grep -q '^### Verify'` (checking for *presence*); the exit code in the table is **typed by hand by the agent**, and nothing re-runs the command or records the result/timestamp.
**Reshaped for us (bash/python, NO DB):**
- Add `scripts/verify-summary.py` (modeled on `check_plan_format.py`): parse the `### Verify` table in `specs/<slug>/SUMMARY.md`, run each `Command` (60s timeout, from repo root), **overwrite the Exit column with the REAL exit code** + a `Verified: <timestamp>` line. Exit 1 on failure or when claimed ≠ actual.
- `--all`: glob `specs/*/SUMMARY.md`, print a tally in their style (`N checked, P passed, F failed, S skipped`).
- Upgrade `commit-quality-gate.sh`: when `REQUIRE_VERIFY=1`, replace the `grep` with a call to `verify-summary.py`.
- Fix the comment in `templates/SUMMARY.template.md`: the Exit column is machine-overwritten, agents stop asserting it themselves.
**Warning:** `--all` runs commands from EVERY slug (including abandoned branches) → a footgun if a command has side effects (`alembic upgrade`); by default run only the active slug, and require read-only/idempotent commands. Editing `commit-quality-gate.sh`/`settings.json` is **Rule-4 high-blast** → must go through the full chain. Storing timestamps has little value since `specs/` is gitignored; the value is in the *re-running*, not in a durable record.

### IDEA-12 — Maturity ladder gated by checkable evidence (fit 72)
**Premise verified right here:** CLAUDE.md/README/HARNESS.md/`skills/README.md` reference multiple subsystems that **do not exist on disk**.
**Reshape (take the PRINCIPLE, drop the ladder/matrix):**
1. `scripts/check-harness-claims.sh` (or fold it into `harness-status.sh`): assert every subsystem referenced in docs exists; exit non-zero + print "claimed in X, absent on disk" pairs.
2. A **flat** `HARNESS_MATURITY.md`: a `Subsystem | Claimed-in | Present-on-disk | Status` table — NOT a 6×11 matrix. A row is Covered only when the checker passes.
3. Wire it as **advisory (non-blocking)**.
**Drop:** the H0–H5 ladder and the 11-responsibility matrix — that part exists for a distributed product with many adopters; for a one-person dogfood it becomes a self-rotting matrix.

### IDEA-03 — Score record completeness, gate by exit code per lane (fit 68)
**Gap:** the subagent contract (Commits/Files/Lane/Deviations/Verify/Harness-Delta) is prose nobody parses.
**Reshape:** add `hooks/record-quality-gate.sh` (PreToolUse `git commit`, alongside `risk-corroboration.sh`) — **reuse exactly the Lane resolution of `risk-corroboration.sh`**: grep `^Lane:`, normalize tiny|normal|high-risk. Map lane→required sections: tiny→header (Lane/Confidence/Reason); normal→ + one non-placeholder `### Verify` row; high-risk→ + `### Rollback`. On a miss → print the missing list + exit 2. WARN by default, enable blocking via `RECORD_QUALITY_STRICT=1` (following the `RISK_CORROBORATION_STRICT` convention). **NO** Python module, NO duration/token fields, NO lifting their "anti-laziness sentinel".
**Warning:** a tiny-lane direct edit may commit without a SUMMARY → must fall back to WARN when there is no SUMMARY. Ship WARN first, only then flip.

### IDEA-10 — Lane→evidence mapping as testable code (fit 68)
**Gap:** the lane→ceremony mapping is only prose in `feature-intake/SKILL.md` Step 7, and it is **duplicated in 3 places** (Step 3, `rules/auto-correct-scope.md` Rule 4, `risk-corroboration.sh`) with nothing keeping them in sync.
**Existing precedent:** `scripts/check_plan_format.py` (174 lines) + `scripts/test_check_plan_format.py` (218 lines) — we HAVE already encoded a markdown convention as tested code.
**Reshape:** `scripts/check_lane_evidence.py` + tests. A single source-of-truth mapping; the script reads a real `specs/<slug>/SUMMARY.md` and exits non-zero when an artifact is missing. **The consumer is the crux** — gate against the real specs dir. Wire a warn-first hook and point Step 7 and `auto-correct-scope.md` at this script as the single source.

### IDEA-04 — Drift audit + a single 0–100 health number (fit 68)
**Gap (verified, worse than described):** `docs/solutions/` and `docs/harness-experimental/trust-metrics.md` **do not exist** despite being referenced in many places; `harness-status.sh` tries to read the ledger and falls into `[not found]`.
**Reshape (bash+python, computed — do NOT let the model assert it, NO DB):** `scripts/harness-audit.sh`:
1. **phantom references** — grep for paths that are cited but absent on disk;
2. SUMMARYs that exist but lack a `### Verify` line;
3. PLANs with status:active but a stale Status Log;
4. `docs/solutions` entries with `confirmed_at:` >30 days (degrade to 0 when the dir is empty);
5. orphan untracked `.py` files (reuse `check-untracked-py.sh`).
Keep the **weights in data** (assoc array / json sidecar) because their caveat is right: the weights are uncalibrated magic numbers. **Report both the raw total and the banded value** — do not silently `min(100)`. Emit JSONL to `docs/harness-experimental/audit-log.jsonl`, wire it as an opt-in line in `harness-status.sh`, **not** as a blocking hook.

### IDEA-05 — Self-improvement generator from accumulated friction (fit 68)
**Gap:** the `Harness-Delta` signal (fix-direct/backlog/none) in SUMMARY is gitignored → a **dead end**; `/compound` reads only 1 session, never counts across sessions. Our own `docs/research/harness-review-improvements/research-compound-loop-closure.md` already diagnosed this loop as "open/semi-closed".
**Reshape (markdown/grep, hybrid):**
1. Add a `Harness-Delta` column to the `docs/harness-experimental/trust-metrics.md` ledger (committed, dated rows);
2. Extend `harness-status.sh --propose`: group friction by a normalized key, gate on count≥2, confidence (high≥3 else medium), emit a proposal;
3. Backlog = `docs/harness-experimental/improvement-backlog.md`;
4. **The hybrid is the strongest version:** the count≥2 gate is a deterministic filter; the semantic near-duplicate clustering step is handed to `/compound`'s LLM. Wire one line into `skills/compound/SKILL.md` so an over-threshold entry becomes a trigger.
**Warning:** worth it only if the dev *actually triages*; otherwise the backlog becomes a graveyard (the "unread artifacts" anti-pattern). Lower priority than closing the read-back loop.

### IDEA-14 — Idempotent marked-block updates for CLAUDE.md (fit 66)
**Gap:** `/compound` is **forbidden from writing CLAUDE.md itself** because there is no safe in-place update mechanism; the installer currently does `cp -R`.
**Precedent:** `hooks/state-breadcrumb.sh` already manages a delimited markdown section (`## Session End Log`); CLAUDE.md already has a `<!-- code-review-graph MCP tools -->` marker.
**Reshape:** `scripts/lib/marked-block.sh` with `upsert_marked_block <file> <begin> <end> <content>`: back up first, `cmp -s` no-op when identical, `awk`-replace the block between `<!-- HARNESS:BEGIN/END -->`, append if absent. Call it from `install-harness.sh` to refresh the harness region in the target project's CLAUDE.md. **Leave** `/compound` Step 6 as-is — this is a precondition for the AGENTS.md bridge (IDEA-13), not a way to unlock compound auto-write.

### IDEA-08 — Predicted-vs-actual outcome loop (fit 62)
**Gap:** decision/solution docs have rationale + confidence but **do not** pair the prediction-at-creation with a measured outcome.
**Reshape (2 YAML fields + grep):** add `predicted_impact:` and `actual_outcome: null` to `skills/compound/templates/decision-track.md`; extend `/xia2`'s planning-time read to surface docs with a prediction set but a null outcome & `confirmed_at` >30 days ("open prediction loops"). **Warning:** the main risk is `actual_outcome` staying null forever → a write-only field; worth it only because it is extremely cheap.

### IDEA-07 — Record typed interventions (human correction is data) (fit 62)
**Gap:** `ESCALATIONS.md` only captures the "ask-before-acting" slice; when a human **fixes** an autonomous diff *afterward* → zero trace. Yet our core thesis (Lane×Confidence = "reduce/justify human intervention") needs exactly this data to know whether autonomy was *actually earned*.
**Reshape (markdown + compound, NO DB):** `templates/CORRECTIONS.template.md` (append-only `specs/<slug>/CORRECTIONS.md`): `type: correction|override|rework|approval`, `source`, `lane`, `what`, `commit`. Hard separation: escalation (ask-before) in `ESCALATIONS.md`; correction (observe-after) in `CORRECTIONS.md`. Extend `/compound`'s FAILURE_TRACK miner to read it. **Warning:** counting "≥2 occurrences" across gitignored specs is unreliable → the data is only directional. Ship the consumer TOGETHER with the template or skip.

### IDEA-15 — Auto-changelog + version on merge (fit 62)
**Gap (verified):** there is no CHANGELOG/VERSION/tag/CI at all; the **installer pins `BRANCH=main`** → every user silently gets HEAD-of-main, with **no version surface**.
**Reshape (do NOT lift their Rust CI/pull_request_target):** add `CHANGELOG.md` + `VERSION` at the root; have `skills/finishing-a-development-branch/SKILL.md` prepend an entry at merge time + bump VERSION (patch by default, minor/major when a skill/hook contract changes); wire VERSION into `install-harness.sh` to echo the version just installed. Add a single `release.yml` (release-please) only *after* the manual version proves it can be maintained.

### IDEA-09 — Queryable tool/skill registry + existence check (fit 62)
**Gap (3 live bugs, verified):** README lists 4 standalone skills that do not exist; CLAUDE.md lists `validate-buzz-commands.sh` (phantom) and **omits** `render-plan-on-write.sh`.
**Reshape (1 bash check, NOT a product registry):** `hooks/inventory-drift-check.sh` (in the style of `check-untracked-py.sh`): scan `skills/*/SKILL.md` (the `name:` field is ground truth), `hooks/*.sh`, and hook entries in `settings.json`; assert every name in `skills/README.md`/the CLAUDE.md table exists on disk and vice versa; exit non-zero on drift. **Drop:** the ToolEntry struct, taxonomy, semver, arg schema, SQLite.

### IDEA-01 — A durable, queryable state layer (fit 58)
**An important truth:** we have **already designed** a cross-slug ledger (`feature-intake/SKILL.md` points to `docs/harness-experimental/trust-metrics.md`; `harness-status.sh` already parses it) **but never built it**.
**Reshape (the lightest tier, NO SQLite):**
1. Create + **track** `docs/harness-experimental/trust-metrics.md`; lock the column schema in the header and in `SUMMARY.template.md`;
2. `scripts/query-ledger.sh`: `--high-risk-no-verify`, `--friction`, `--stats`;
3. Escalate to JSONL + a ~40-line Python script ONLY if grep/awk over markdown gets too brittle; **do not** jump to SQLite unless we pass thousands of rows.
**Why not higher:** their 7-table schema + migrations + WAL is the architecture of a *distributed product*; for one person, durable state is only worth it if *someone acts on the queries*.

### IDEA-06 — Context-read scoring (fit 42)
**ADOPT only the data half, DROP the scorer half.** `xia2/SKILL.md` is already a per-phase read-list with an implicit over-read guardrail.
**Reshape:** create `rules/context-rules.md` — a phase × lane Must/Should/Skip matrix + token budget suggestions as **soft hints, not a gate**. **DROP the scorer:** do not build `score-context`, no PostToolUse(Read) hook, no files_read ledger — they themselves call their phase inference "brittle/over-fit".

### IDEA-13 — Agnostic AGENTS.md + a Claude @-import bridge (fit 38)
**A very narrow reshape, rejecting most of it.** The "agnostic, Codex/Cursor" framing is a non-fit. "Separating portable doctrine" is largely **already done**: `HARNESS.md` *is* the doctrine doc; CLAUDE.md already uses `@`-import. **The only real gap:** the installer payload **does not include** `HARNESS.md`/`CLAUDE.md` → the target project gets skills but no entry doc.
**Reshape:** add `HARNESS.md` to `install-harness.sh`'s PAYLOAD; use the marked-block mechanism (IDEA-14) to inject a single `@.claude/HARNESS.md` line into the consumer's CLAUDE.md. **DO NOT** rename to AGENTS.md, and NO Codex/Cursor issue templates.

## 5. Ideas we should SKIP (and why)

- **IDEA-11 — Schema versioning + brownfield importer (fit 18, verdict SKIP).** Entirely **dependent on IDEA-01 (a DB), which we already declined**. Our "schema" is a few markdown templates that **git already versions** (diffable, revertable, zero machinery). There is no brownfield corpus to ingest (one person, 2 active slugs). Building an importer now is **speculative** (violates `behavior.md` §2). **Action: do nothing yet**; record the conditional dependency in decision-track so a future agent does not independently re-propose it.

> **The principle running through the SKIP/ADAPT sections:** every mechanism only "fits" *because they are a compiled tool with a DB* — the hand-written JSON serializer, hand-drawn ASCII tables, the hardcoded `compiled_tool_registry()`, score-context with paths hard-embedded in Rust, `pull_request_target` auto-push-main — all are the **wrong altitude** for a prompt framework. Porting the **concepts** (runnable verify, trace tiers, context matrix, entropy) into files/hooks is right; porting the **binary substrate** is wrong.

## 6. "A different version" — a sketch

If we genuinely wanted a **v2** inspired by them, the minimum viable shape (NO Rust, NO SQLite):

- **The core: one committed ledger, queryable with grep/awk.** This is the *precondition* for everything else (scoring, audit, propose, predicted-vs-actual all need somewhere to query). Concretely: *actually* build `docs/harness-experimental/trust-metrics.md`, which we **designed but never created** — committed, with a fixed column header (Date|Slug|Lane|Confidence|Verify|Harness-Delta|Hook-outcome), plus `scripts/query-ledger.sh` for a handful of preset queries.
- **The measurement layer (built on the core):** `scripts/harness-audit.sh` (the 0–100 entropy number, weights in data), `scripts/verify-summary.py` (re-run the Verify table), `hooks/record-quality-gate.sh` (per-lane completeness gate). Each is one file/hook, exit-code-gating — following the `check_plan_format.py` precedent exactly.
- **The portability layer (built last):** the marked-block updater (IDEA-14) + `HARNESS.md` in the payload + VERSION/CHANGELOG. This is the part that puts the harness into other repos *safely*, but still Claude-first — do NOT chase Codex/Cursor agnosticism (zero consumers).

**Is it worth it — a blunt opinion:** A **comprehensive v2 in their style is NOT worth it** for a one-person dogfood — it imports the full maintenance debt (migrations, markdown↔DB drift, a build toolchain) to serve one person who mostly needs "show all high-risk no-verify" a few times. But **the ledger core + 2–3 measurement files ARE very much worth it**, because (a) we already *designed* the ledger and left it vaporware, (b) on-the-spot verification shows we *are* over-claiming subsystems that do not exist, and (c) they use exactly the bash/python precedent we already accept. The honest line: **build for queries we can name today, not for a hypothetical analytics platform.**

## 7. Proposed next steps (quick wins first)

1. **Fix the verified drift immediately (≈0 effort, highest value).** Remove the 4 phantom standalone skills from `skills/README.md`; remove `validate-buzz-commands.sh` from the CLAUDE.md hook table; add `render-plan-on-write.sh` to the table. _(DONE — 2026-06-09.)_
2. **Build the already-designed ledger (IDEA-01, light tier).** Create + track `docs/harness-experimental/trust-metrics.md`, lock the column schema, add `scripts/query-ledger.sh`. Unlocks IDEA-04/05/08.
3. **`scripts/harness-audit.sh` (IDEA-04).** Check (1) phantom references — it will catch all drift on its own; weights in data; advisory, wired into `harness-status.sh` in place of the dead branch.
4. **`scripts/check-harness-claims.sh` + a flat `HARNESS_MATURITY.md` (IDEA-12).** Overlaps heavily with #3; can be merged. Advisory, non-blocking.
5. **`scripts/check_lane_evidence.py` + tests (IDEA-10).** Modeled on `check_plan_format.py`; warn-first hook.
6. **`hooks/record-quality-gate.sh` (IDEA-03).** Reuse `risk-corroboration.sh`'s Lane resolution; ship WARN first.
7. **`scripts/verify-summary.py` (IDEA-02).** Medium, touches Rule-4 (`commit-quality-gate.sh`/`settings.json`) → run the full chain.
8. **`scripts/lib/marked-block.sh` + wire the installer (IDEA-14 → IDEA-13).** An independent quick win that opens the path to putting `HARNESS.md` in the payload.
9. **VERSION/CHANGELOG via the finishing skill (IDEA-15).** Closes the "installer pins main, no version" gap.
10. **Last, conditionally:** IDEA-05/07/08 (self-improve loops) only *after* the ledger has real data and there is a commitment to triage.
11. **Do not do:** IDEA-11 (importer/migration) until — if ever — IDEA-01 moves to a real DB.
