# Re-check `hoangnb24/repository-harness` (v0.1.10) — Adoption Audit & v2 Proposal

- **Date:** 2026-07-03
- **Source:** https://github.com/hoangnb24/repository-harness (clone HEAD, tag `harness-cli-v0.1.10`)
- **Context:** this is the SECOND round of research. The first: `docs/research/harness-review-improvements/research-repository-harness-ideas.md` (2026-06-09, at v0.1.9, 16 IDEAs, a 10-step plan). This time there are 2 new inputs:
  1. **Deep review 2026-07-03** (`docs/research/harness-review-improvements/2026-07-03-deep-review-harness-trustworthiness.md`) — identified the systemic failure modes of our repo;
  2. **Adoption audit** — examining each old IDEA to see how far it was adopted and whether it is still alive.
- **Method:** 2 parallel agents (mechanism-level read of their repo · adoption audit of our repo), every claim verified by reading code/git log.

---

## 1. TL;DR

- **Their delta from 06-09 → now is very small:** only the addition of the **kind-aware inbound tool registry with presence scanning** (US-027, PR #19) + an installer fix + release v0.1.10. All of Phase 4/5 (entropy, propose, interventions, trace scoring) was already covered in the earlier research.
- **The most important finding is NOT on their side but on ours:** the adoption audit reveals an **absolutely clean dividing line** — everything **enforced by CI/hook** (lint-doc-truth, verify_summary --check, ci-strict-gate, test suites) is still alive and running; everything relying on **manual append discipline** (ledger, CHANGELOG, VERSION, backlog triage) **flatlined exactly on 2026-06-14** — the day of the last adoption burst. PR #27 shipped a new wired hook (high-risk!) with no ledger row, no CHANGELOG entry, and **nothing blocked it**.
- **Strategic conclusion:** our repo has proven the "proof by machine, not assertion" thesis on itself over 3 weeks. The biggest lesson from their repo this time is not a feature — it is an **architectural principle: bookkeeping must be written by an EVENT, not by discipline**. Their post-merge-maintenance.yml is the perfect example: CHANGELOG/tag/version are written by the merge event itself, and a human never has to remember.
- **Proposal:** a **v2 along the lines of an "Event-Sourced Trust Layer"** — 5 phases, detailed in §6. No Rust, no SQLite (the earlier verdict stands); only *who writes the record* changes.

---

## 2. Their delta from v0.1.9 → v0.1.10

| Change | Content | Worth learning? |
|---|---|---|
| US-027 tool registry (PR #19) | `tool register --kind cli\|binary\|mcp\|skill\|http` records *intent*; `tool check` reconciles it against *reality* by probing per kind (PATH exec-check, file resolution, TCP), records `status + checked_at`, always exits 0. Degrade ladder: **Inactive** (never registered → clean skip) / **Degraded** (registered but missing on disk → flagged "Weak proof") / **Full** | ✅ Very much — see §4.2 |
| Installer fix (PR #20) | Added missing files to the installer file-list | No |
| Release v0.1.10 | Automatic via post-merge-maintenance | The mechanism is worth learning (§4.1) |

---

## 3. Adoption audit — how far the 06-09 research was actually executed

Adoption happened in 2 bursts: **06-11** (PRs #10–#13) and **06-14** (gap-closure #18–#25), routed through `docs/harness-gap-closure-plan.md`. **After 06-14: zero adoption activity.**

| IDEA | Status | Evidence |
|---|---|---|
| 01 ledger | **adopted-then-decayed** | trust-metrics.md tracked, schema locked (`2582d64`), 15 rows — but `query-ledger.sh` was never built; the last row and last commit are both 06-14 (`fe43d1a`). PRs #27–#30 (including the high-risk branch-isolation-guard, which has a SUMMARY `929d4da`) have **no rows at all** even though the feature-intake Guardrails require them |
| 02 verify_summary | **adopted-faithfully** | Script + test, wired into `commit-quality-gate.sh` (REQUIRE_VERIFY) + `ci-strict-gate.sh`, actually running in CI. The `--all` footgun was avoided by *not implementing it* — about as safe a reading of the research as possible |
| 03 record-quality-gate | **adopted-with-gaps (folded)** | The lane→sections mapping was folded into `check_lane_evidence.py`; but **no PreToolUse hook calls it** — enforcement is only a CI unit test |
| 04 harness-audit | **adopted-with-gaps** | The script exists (`4dd42df`), advisory, wired into harness-status. But: no 0–100 entropy, bands hardcoded (0/≤3/>3), **no audit-log.jsonl** → no history, no trend line — precisely the "one number over time" the idea aimed at is missing |
| 05 friction→propose | **adopted-with-gaps, the warning is coming true** | No `--propose`, no grouping with count≥2. The backlog has **exactly 1 entry, status `open`, untouched for 19 days** — "the backlog becomes a graveyard" is happening |
| 07 CORRECTIONS | **not-adopted** (as planned — conditional) | No files |
| 08 predicted/actual | **not-adopted** | The fields exist only in the research doc itself |
| 09/12 drift check | **adopted-faithfully (consolidated)** | `lint-doc-truth.sh` performs a two-way check of the hook table ↔ settings.json, running in CI on ubuntu+macos. HARNESS_MATURITY.md was not created — the Evidence Tiers table carries part of that role |
| 10 lane evidence | **adopted-with-gaps** | Script + 13 tests in CI. But: **feature-intake Step 7 never mentions it** even though auto-correct-scope.md *claims* it does — a live doc-drift of exactly the class this whole effort targeted, and `lint-doc-truth.sh` cannot catch it (the path exists). No runtime hook calls the script |
| 13/14 marked-block/HARNESS.md payload | **not-adopted (deliberate deferral)** | Re-deferred in research-harness-req-assessment: "when a second consumer arrives" |
| 15 VERSION/CHANGELOG | **adopted-then-decayed** | Created `9e74138`, bumped to 0.2.0 `fe43d1a` (both 06-14). Since then: PR #27 shipped a new wired hook (a minor bump under CHANGELOG's own rule) + #28/#30 — `[Unreleased]` is **empty**, VERSION frozen. Sustained for exactly one release cycle |

**Ratio:** 2 faithful · 5 with-gaps · 2 decayed · 4 not-adopted (~70% had real work done; steps 1–7 and 9 of the plan were attempted; steps 8 and 10 were not).

**The alive/dead dividing line (the central lesson):**

```
ALIVE = run by machine:       lint-doc-truth (CI) · verify_summary --check (CI+hook) · ci-strict-gate (CI) · test suites (CI)
DEAD  = waiting for a human:  ledger rows · CHANGELOG entries · VERSION bumps · backlog triage · STATE.md Active Spec
```

---

## 4. Mechanisms worth learning from their repo (mechanism-level, with honest caveats)

### 4.1. Post-merge maintenance via a CI event — ⭐ the most worth learning

`.github/workflows/post-merge-maintenance.yml`: `pull_request_target: closed` on main, gated on `merged == true`. One bash step: `gh pr view` fetches title/author/files/mergeCommit → if the files match the CLI regex it patch-bumps the version, prepends a structured CHANGELOG entry (date, PR#, author, merge SHA, file list), commits, pushes, tags idempotently (guarded by `git ls-remote --exit-code`), and dispatches the release workflow.

- **It cures exactly our disease:** the record is written by the *merge event*, not by anyone's discipline. Their CHANGELOG matches every merge exactly since the workflow landed (PRs #13/#19/#20); merges before the automation are simply absent — an honest cutover.
- **Failure modes they hit:** it only fires on PR merges (direct pushes to main are invisible); the automation itself once shipped a bug (`7e6c199` fixed printf); races on concurrent merges.
- **Portability: excellent** — pure gh/jq/bash, drop-in for our repo.

### 4.2. Tool registry: register-vs-scan + degrade ladder (US-027 — new)

Separates **intent** (registration) from **reality** (probing per kind). Three pivotal states: *not-registered = not drift* (clean skip); *registered-but-missing = failed validity gate* (Weak proof flag); *present = Full*. `tool check` always exits 0 — "a missing extension is a fact to report, not a CLI error".

- **Maps directly onto our disease:** the hook table in CLAUDE.md *is* a registry — but nothing scans it (lint-doc-truth only checks path-existence, not "skill X references agent Y that does not exist" — exactly the phantom `superpowers:code-reviewer` bug the deep review found).
- **Caveat they declare themselves:** `present` = "exists on disk", not "runnable" (TOOL_REGISTRY.md:88-92).

### 4.3. Store-and-rerun verify command + never-run/stale audit

`story verify` runs the stored `verify_command` and records pass/fail + timestamp; `verify-all` batches it; `audit` counts never-run commands as drift. The pre-close gate (US-017) is **advisory, not blocking**.

- **What stops `true`? — Nothing at all.** The exit-0 of a command the agent wrote itself is the entire "proof". Their mitigation is structural (a human sees `true` during PR review), not mechanical. → It solves "evidence is never re-run" (our STATE.md disease), but **not** "evidence is trivially satisfiable" (our ci-strict-gate disease — both repos share this hole).
- **We must add the part they lack ourselves:** a denylist (`true`, `:`, `echo`, `exit 0`) + a requirement that the command reference a path in the diff.

### 4.4. Entropy audit — one number, with a trend

6 fixed SQL checks, each one a "promise-vs-evidence mismatch": orphaned story ×10, verify not run ×5, implemented backlog item missing `actual_outcome` ×2, stale >30d ×3, broken tool ×8 → weighted sum capped at 100.

- The signals are well chosen; the weights are arbitrary and unvalidated; it only sees what is in the DB — anything undeclared is invisible (a blind spot they acknowledge). It shifts the problem from "will anyone append to the ledger" to "will anyone record a story".
- **What we port:** each check ≈ 10 lines of Python over `specs/*/SUMMARY.md` + docs/solutions front-matter; drop the cosmetic cap-100; **most importantly, emit JSONL to get a trend** — the thing today's harness-audit.sh lacks.

### 4.5. Typed interventions + rule-based propose + a self-policing closed loop

An `intervention` table (type: correction/override/escalation/approval; source: human/reviewer/ci/agent). `propose` is **deliberately rule-based, not LLM** (decision 0007 — for auditability): it groups normalized friction/intervention text, count≥2 → a proposal with evidence/predicted_impact/validation_plan; confidence = count≥3→high. Closing a backlog item **requires** `actual_outcome`; a closed item missing its outcome is **counted as drift by the entropy audit** — a loop that polices itself.

- **This is the piece we most lack for the Lane×Confidence thesis:** "is autonomy actually earned" needs exactly this human-correction data. Their grouping is naive (token-normalize, acknowledged in 0007) — acceptable.

### 4.6. Maturity claims capped by checkable evidence

HARNESS_MATURITY.md ladder H0–H5, each level with file-inspectable criteria; their repo scores itself H3/H5 "Partial" and **names the missing evidence**. We already have part of this discipline (the Evidence Tiers table) — worth keeping and extending.

### 4.7. Governance principles (decision 0007, PHASE4/5)

- **Deterministic for the evolution layer** (never let an LLM propose changes to its own policy);
- **Advisory first, blocking later** — gates warn first, "earn strictness";
- **The harness never rewrites its own policy** without human review;
- Every phase claim must have a story + an Evidence section.

### Their weaknesses (so as not to idolize them)

- **Gates check format, not substance** everywhere: trace tiers count field-presence (`["x"]` passes the list-check, `harness_friction: "none"` passes Standard); a placeholder-filled trace still scores Detailed. Their lane is also **self-declared** at `intake --lane` — the same self-reference bug we have.
- **Paths hardcoded in compiled Rust** (context rules, retrieval triggers) — a doc rename is silent scorer rot, and no test binds CONTEXT_RULES.md ↔ code. Context scoring is the weakest mechanism: `files_read` is self-declared by the agent.
- **Their own dogfooding is invisible:** `harness.db` is gitignored, the binary is absent — no durable record is inspectable in-repo; Evidence sections ("26 passed") are unpinned prose — exactly the documented-only tier we penalize.

---

## 5. Matching up: our diseases (deep review 07-03) ↔ their cures

| Our disease (verified) | Their mechanism | Degree of fit |
|---|---|---|
| Trust ledger dead for 3 weeks; CHANGELOG/VERSION frozen after 1 cycle | Post-merge maintenance CI (§4.1) | **Direct — the right cure for the disease** |
| Hard-gate list diverges across 4 sources; skill references a phantom agent; reviewer.md claims are wrong | Registry register-vs-scan + degrade ladder (§4.2) | **Direct** (extends the existing lint-doc-truth) |
| STATE.md/harness-audit has no history, no trend; "is the harness rotting?" cannot be answered | Entropy score + JSONL trend (§4.4) | **Direct** |
| ci-strict-gate passes with `true`; an unedited rollback template still passes | Store-and-rerun verify (§4.3) — **but they have the `true` bug too** | **Partial** — we must add the substance denylist ourselves |
| Lane is self-declared, hooks only enforce consistency; no data measures "is autonomy earned yet" | Typed interventions + propose + predicted-vs-actual loop (§4.5) | **Direct for the data part**; the self-declared lane is unsolved on their side too |
| Backlog with 1 orphaned entry for 19 days | Propose gate count≥2 + close-requires-outcome policed by the audit (§4.5) | **Direct** |
| Commit-gate bypass, session-knowledge dead, break-glass unreachable | *(no equivalent — our own bug bash)* | Must fix ourselves, see deep review §Critical |

---

## 6. v2 proposal — "Event-Sourced Trust Layer"

**The single innovating principle:** *every record the harness mandates must be written by a machine event (CI trigger, hook trigger), or be blocked by a machine checker when absent. No record may depend on an agent/human "remembering to append".* Keep the markdown + bash + python substrate (reaffirming the 06-09 verdict: no Rust, no SQLite). Ceremony stays the same; only **who keeps the books** changes.

### Phase 0 — Patch the foundation (prerequisite, from the deep review — not inspired by their repo)
Fix the 2 criticals + the high group: command matching in the 3 commit hooks (tokenize, catch `git … commit` in any segment); session-knowledge root resolution; consolidate the hard-gate list into 1 data source (see Phase 2); the review chain for executing-plans; the false premise in finishing-a-development-branch. *Without Phase 0, every measurement layer above it measures a leaking system.*

### Phase 1 — Event-driven bookkeeping (port §4.1)
- Our own `.github/workflows/post-merge-maintenance.yml`: on a merged PR → `gh pr view` JSON → **(a)** append a row to `trust-metrics.md` (Date|PR|Slug|Lane — lane read from the SUMMARY in the diff, `?` if absent), **(b)** prepend a CHANGELOG entry, **(c)** bump VERSION (minor when the diff touches `hooks/`+`settings.json`, patch otherwise), **(d)** commit + push idempotently.
- From now on **nobody appends to the ledger by hand** — delete the "Append to the ledger" mandate in the feature-intake Guardrails, replacing it with "CI appends; check the row after merge".
- Fix the broken `state-breadcrumb.sh` metric or delete `user_turns`; add rotation for the Session End Log.

### Phase 2 — One registry, one gate source (port §4.2 + fix the 4-source divergence)
- `harness-manifest.yaml` (root, tracked) — the single source of truth, 4 sections: `skills` (name, path, handoffs, external deps such as agent types), `hooks` (path, event, matcher, wired), `agents`, `hard_gates` (the list of 8 gates + regex signals).
- `scripts/check-manifest.py` (replacing/extending lint-doc-truth): probe per kind — skill path exists, hook correctly registered in settings.json both ways, an agent type referenced by a skill must be present in the manifest, a missing external dep → **Degraded** (report, do not fail) following their degrade ladder. Runs in CI.
- `feature-intake` Step 3, `auto-correct-scope.md` Rule 4, and `risk-corroboration.sh` **all read `hard_gates` from the manifest** (the hook parses the yaml with a python one-liner, or a .sh file is generated from the manifest at CI time) — structurally ending the 4-source divergence.

### Phase 3 — Verify with substance + entropy with a trend (port §4.3 + §4.4, patching the hole they also have)
- `verify_summary.py`: add a **substance denylist** (`true`, `:`, `echo …`, `exit 0`, a command that references no path in the PR's `git diff --name-only` → FAIL with a clear message); fix the em-dash duplicate + the 3 semantics traps already found; add `test_verify_summary.py` to run-tests (1 line); sandbox verify commands in CI (timeout + no network if possible).
- `check_lane_evidence.py`: rollback must differ from the template byte-wise; lane must match exactly.
- `harness-audit.sh` → upgraded into an entropy score with 6 checks + **emit `docs/harness-experimental/audit-log.jsonl` on every CI run** → a real trend line. Checks include: plan active >30d with no new status-log · SUMMARY missing Verify · verify never re-run · backlog item open >14d · manifest Degraded rows · solutions confirmed_at >30d.

### Phase 4 — The closed improvement loop (port §4.5, only after Phases 1–3 produce data)
- `specs/<slug>/CORRECTIONS.md` append-only (type: correction|override|rework|approval, source, commit) — written by a hook/skill when a human fixes an autonomous diff.
- `scripts/propose.py` rule-based (per their decision 0007: do NOT let an LLM propose changes to policy): group friction + corrections, count≥2 → a backlog entry with `predicted_impact`; **closing an entry requires `actual_outcome`**, and a closed entry missing its outcome is counted by the entropy audit — a self-policing loop.
- `/compound` keeps its role of semantically clustering near-duplicates (a hybrid, as the earlier research proposed).

### Phase 5 — (conditional) Portability
Keep the current deferral: marked-block + HARNESS.md payload only "when a second consumer arrives". No change.

### Not doing (reaffirmed)
Rust/SQLite substrate · context-read scorer (self-reported files_read — weak on their side too) · schema versioning/importer · agnostic AGENTS.md for Codex/Cursor (zero consumers) · a 6×11 maturity matrix.

### Success measures for v2
1. **Zero records waiting on a human to append** — a repo-wide grep finds no remaining "append X" mandate without an accompanying event/checker.
2. Any PR merge → trust ledger + CHANGELOG have an entry within ≤1 minute, with nobody typing.
3. `harness-audit` yields one number + a trend across ≥3 weeks of JSONL data.
4. `ci-strict-gate` **cannot** be passed with `| x | true | 0 | |` (with a test proving it).
5. The hard-gate list exists in exactly **one** machine-readable place; all 3 consumers point at it (with a test).

---

## 7. Proposed next steps (in order)

1. **Phase 0 critical fixes** (commit-hook matching + session-knowledge) — **high-risk** lane (touches hooks/ + settings.json), full chain.
2. **Phase 1 post-merge workflow** — independent, the highest value/effort ratio in the new group; one workflow file + a Guardrails edit.
3. **Phase 3 substance denylist + test_verify_summary into CI** — patches the hole both repos share; small, immediately measurable.
4. **Phase 2 manifest** — larger, deserves its own PLAN.md.
5. **Phase 4** — only start once the event-driven ledger has ≥2 weeks of real data.
