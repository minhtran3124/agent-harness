# Deep Research — Anthropic's "AI-native SDLC playbook" vs. our harness

> Date: 2026-10-10 · Source: Claude Academy course *The AI-native SDLC playbook*
> (`https://academy.claude.com/courses/ai-native-sdlc-playbook/introduction`), all 14 lessons
> fetched and read in full on 2026-10-10.
>
> Question: what does the playbook actually prescribe, how is each "play" implemented, how does it
> compare with this harness's current workflow, and what should we adopt — ordered from easy to hard?
>
> Method: primary source only (the course text, server-rendered HTML → text). Harness claims are
> cited to the file that shows them; every "gap" claim names the surface that was searched
> (`rules/behavior.md` §1). Where something was not checked it is marked **unknown**.

---

## TL;DR

- **The playbook is one idea applied six times:** every SDLC stage produces a *versioned Markdown
  artifact in Git* that the next stage consumes (`intent.md → spec.md → plan.md → diff → review →
  eval`), and every policy that must hold is backed by a *deterministic* control (hook / CI check),
  not just an advisory one (skill / CLAUDE.md). Humans move from *doing* each stage to *approving*
  it, and Stage 6 closes the loop: a deterministic monitor writes a new `intent.md` when a metric
  leaves its control band.
- **Our harness already implements most of the Build → Deploy half, often more rigorously** than
  the playbook (evidence tiers, a blind intent oracle, index-safe gate config, deny-on-no-response
  escalation, honest eval discipline, a review-escape ledger).
- **Our clear gaps are at the two ends and in measurement:**
  1. **Evals are manual-run, not continuous** — the playbook's central Test play (evals re-run on
     every change to CLAUDE.md / skills / hooks) is what we lack most. `evals/README.md` says
     "the LLM runs are triggered manually, not in CI".
  2. **No protected feedback loop** — nothing deterministic stops an agent editing the test it is
     supposed to make pass; `weakening-validation` is warn-mode and commit-time only.
  3. **No closed loop on metrics** — `audit-log.jsonl` has reported the same 39 findings
     ("needs attention") on every merge since at least 2026-09-30 with nothing acting on it: the
     exact "alert that nobody acts on" failure Stage 6 is designed to remove.
  4. **No per-play leading/lagging indicators** — the playbook defines two Git-derivable metrics
     for every play; we have a ledger but no computed indicators.
  5. **Always-on context is large** — ~30 KB of always-on instructions (CLAUDE.md + 5 rules) vs.
     the playbook's "keep CLAUDE.md under a page".
- **The ranked suggestion list is in §6** — 6 easy, 6 medium, 4 hard.

---

## 1. The concept

### 1.1 Core thesis

> "Organizations have started using AI to write code at a speed unthinkable one year ago, yet the
> processes around the code haven't changed at the same pace." — Lesson 1

The six classical stages stay (Plan, Design, Build, Test, Deploy, Maintain), but each one shifts:

| Stage | Traditional | AI-native (playbook) |
|---|---|---|
| Plan | Requirements by committee, workshops, sign-offs | Claude synthesizes pain points into `intent.md` — human readable, machine actionable |
| Design | Analysts write spec, designers parse it | Requirements + design compressed into one agent session, constrained by policy encoded as skills, versioned in Git |
| Build | Handwritten code/tests; docs after | AI-generated code/tests; institutional knowledge as versioned CLAUDE.md + skills |
| Test | QA gates at stage boundaries | Continuous evals woven through implementation |
| Deploy | Humans review every line; governance inconsistent | Layers of agentic review; human review reserved for regulated/critical code; governance enforced *as the AI acts* via hooks |
| Maintain | Humans watch production | Agents monitor; a breached control band is diagnosed and written back as a new `intent.md` |

Invariant: **"Humans remain accountable for every decision that requires judgment."**

### 1.2 The play format

Each of the 12 plays has the same five parts — *What changes · Getting started (prerequisites +
infrastructure) · How to execute it · Governance considerations · How to measure it (one leading
and one lagging indicator)*. Plays form a dependency graph; six have no prerequisites and are the
recommended entry points: **intent.md, plan mode, CLAUDE.md, skills, feedback loop, hooks as
approval gates**.

### 1.3 The artifact chain (the backbone)

```
trigger (person | ticket | alert)
  → intent.md   (Problem · Proposed outcome · Affected users/systems · Constraints · Open questions)
      product owner corrects + merges = approval
  → spec.md     (numbered requirements R1..Rn · design · constraint→"met by" table ·
                 open questions carried forward · Areas of concern with named owner)
      product owner signs off; higher risk → tech lead
  → plan.md     (files that change · order of work citing R-ids · risks · proof)
      engineer approves in plan mode; plan updated in same commit when implementation departs
  → diff + Verify output (tests/build/screenshot pasted from the toolchain)
  → PR review (REVIEW.md passes: bugs · security · compliance vs spec.md/plan.md)
      code owner approves via branch protection; agent can never approve its own code
  → deploy via MCP tools, tiered by environment, prod gated by hook + change ticket
  → monitor: control band breach → diagnose → write new intent.md  ─┐
  → incident fixed → becomes a permanent eval                         │
  └────────────────────────────── loop ──────────────────────────────┘
```

Numbered IDs are what make the chain checkable: the plan cites R-ids, the review's compliance
pass reads `plan.md`, and the lesson notes one finding "exists only because the compliance pass
reads the committed plan.md".

### 1.4 The principles that recur across plays

1. **Advisory vs. deterministic controls.** "A skill is a control, though an advisory one… The skill
   makes violations rare and the hook makes them close to impossible." Any policy that must always
   hold gets a hook *and* the same check in CI, because "an Edit|Write hook does not fire when a
   shell command rewrites the file."
2. **Protect the feedback loop.** "An agent fixing code must not be able to weaken the check on that
   code." For bug fixes: write the failing test first, confirm it fails for the expected reason,
   commit it, then fix *without editing the test* (enforced by a test-file hook).
3. **Configuration is code and gets regression-tested.** The eval suite runs "on any change to
   CLAUDE.md, skills, or hooks, since that configuration steers the agent". Every production
   incident becomes an eval.
4. **Gates explain themselves.** A block states the reason *and the route to approval*. Hooks can
   `allow`, `ask`, or `deny`; in non-interactive runs `ask` becomes deny, so pipelines must have an
   explicit allow path; production fails closed. "The gate depends on the agent having no way to
   write to the records it reads."
5. **Humans off the build critical path.** Approval prompts belong at Deploy, not Build, "because an
   approval prompt during the build puts a person back on the critical path of all the sessions
   running in parallel". Build hooks must be fast and file-scoped; heavy checks go to commit/PR.
6. **Separation of duties.** The agent that wrote the code cannot approve it; human attention moves
   "up a level" to intent and risk.
7. **Autonomy tiered by blast radius.** Dev: free. Staging: ask / pipeline-from-main. Prod: agent
   prepares, release manager authorizes. Rollback is "the most rehearsed path in the pipeline".
8. **Deterministic detection, model diagnosis.** Stage 6 keeps detection "entirely deterministic,
   with no model involved" (mean ± σ over a 30-day window + Western Electric drift rules). Tiers:
   1σ log · 2σ diagnose read-only · 3σ propose (PR or pre-approved runbook only).
9. **Measure from Git.** Nearly every indicator is two Git timestamps or a count of commits
   (e.g. "count `spec.md` commits dated after the first `plan.md` commit" = requirements rework).
10. **Keep the always-on context small.** CLAUDE.md "under a page"; "When Claude makes a mistake
    twice, the correction goes into CLAUDE.md."
11. **One source of truth per artifact.** Repo-as-truth, legacy-as-truth (MCP write-back), or
    *linkage as the minimum bar* (artifact cites record ID, record cites commit SHA).

---

## 2. Play-by-play: how to implement it

| # | Play | Key implementation mechanics | Leading / lagging indicator |
|---|---|---|---|
| 1 | **Capture as intent.md** | Originator brainstorms with Claude; org template encoded as a skill; product owner corrects; commit to `intent/` in the product repo (connector commits for non-Git users) | Time first conversation → committed intent / survival rate + edits to intent after first spec commit |
| 2 | **Requirements and design** | Prompt: apply skills, produce `spec.md`, "describe clearly any areas of concern, especially where you cannot satisfy contradicting policies". Run by hand → slash command → non-interactive job fired on intent merge that opens a spec PR | intent→spec latency / spec commits after first plan commit |
| 3 | **Plan mode default** | Plan names files, order, tests; interrogate risk & rejected options; iterate "until an engineer who has never seen the conversation could implement the change from the plan alone"; commit `plan.md`; keep in sync (hook suggested). Auto mode for routine work once guardrails mature | First-pass merge share, plan→merge time / rework cycles, merged diff still matches plan |
| 4 | **CLAUDE.md** | `/init`, cut to day-one knowledge (commands, conventions, "things Claude gets wrong"), < 1 page, code-owner reviewed | Repeated-mistake rate / new-joiner time to first PR |
| 5 | **Skills as institutional knowledge** | One inconsistently-enforced policy → SKILL.md with trigger description; test triggering with varied phrasings; policy owner signs off changes; back with PostToolUse hook + identical PR check | Policy-change→skill-merge time / PR findings citing the policy → 0 |
| 6 | **Parallel sessions & subagents** | One worktree per task, tasks split on file independence; 2–3 sessions, add only "while review is keeping up"; recurring jobs as `.claude/agents/` (verifier: "Do not fix anything; report only") | Concurrent sessions at held review quality / merged changes × rework rate |
| 7 | **Feedback loop** | One-command test/build with healthy-output examples in CLAUDE.md; quantifiable target; failing-test-first for bugs; visual loop for UI; "run tests before reporting complete, paste output"; hook blocks test edits during fix | First-pass CI success / review time per PR, change-failure rate |
| 8 | **Continuous evals in CI** | 20–50 real tasks; eval JSON = `from` commit + prompt + `may_change` + checks; run in scratch worktree with `evals/` removed and the *branch's* config copied in; checker run from a copy made before the run; fail on stray files; triggered on config change + nightly; never use `--bare` (it skips the config under test) | Pass-rate trend, incident→eval latency / regressions caught in CI vs prod |
| 9 | **AI in PR review** | `REVIEW.md`: passes (bugs / security / compliance vs spec+plan), what "Important" vs "Nit" means, nit cap (5), do-not-report list; findings don't approve/block on their own; `@claude` fix loop; second-time findings go into CLAUDE.md; monthly tuning by rating findings | Time to first review, comments resolved hands-off / pre-merge vs escaped defects |
| 10 | **Hooks as approval gates** | List the approvals that must survive; one hook per gate with allow/ask/deny; team hooks in `.claude/settings.json`, non-negotiable ones in managed settings; block message = reason + route. Managed settings add permissions allow/deny, sandbox (network allowlist, credential denial), `allowManagedHooksOnly`, marketplace allowlist, min version | Wait time per gate (OTel) / violations reaching prod |
| 11 | **CI/CD integration** | Start with read-only `claude -p` judgment steps (triage failed build, changelog); then write steps that land as PRs; sandboxed, short-lived scoped tokens; deploy/status/rollback as per-environment MCP servers; `--permission-mode dontAsk` | Failures triaged without paging / DORA |
| 12 | **Closing the loop on metrics** | Pick one stable metric; deterministic σ-band script (version-controlled, unit-tested); `bands.yaml` tier→tools/routes; stateless headless run; output as `intent.md` into triage; dismissals tune bands; fixed incident → eval. Claude Tag for chat-originated incidents | Breach→intent latency / findings→merged fixes, repeat-incident rate |

---

## 3. Mapping to our harness

Status: ✅ strong · 🟡 partial · ❌ gap · ➖ not applicable to this repo.

| Play | Harness equivalent | Status | Evidence / searched surface |
|---|---|---|---|
| intent.md | `SUMMARY.md` `### Intent` — the request **verbatim**, oracle for `/intent-review`; `QUESTIONS.template.md` open-questions register; `gh-NNN` slug prefix as ticket linkage | 🟡 | `templates/SUMMARY.template.md`; `skills/feature-intake/SKILL.md:29`. Verbatim ≠ structured: no Problem / Outcome / Constraints / Out-of-scope fields; no survival-rate metric |
| spec.md | `/brainstorming` → `design.md` (only on a real design fork), `/xia2` → `research-brief.md`, PLAN §3 `SC-n` success criteria enforced by `verify_summary.py`; `ESCALATIONS.md` for concerns | 🟡 | `rules/orchestration.md` (artifact policy). No "constraint → met by" table; concerns aren't owner-tagged in the design artifact; for consumers, skill-policy constraints depend on `techstacks/` which ships empty |
| Plan mode | `/writing-plans` → `PLAN.md` (Files, waves, Verify, SC-n), `/visual-planner`, `check_plan_scope` warns on out-of-plan paths | ✅ | `rules/plan-format.md`; CLAUDE.md hook table. Plan↔diff sync is warn-only (`BLAST_RADIUS_STRICT=1` to block); no "diff still matches plan" metric |
| CLAUDE.md | CLAUDE.md + 5 always-on rules; `/compound` + `critical-patterns.md` + `/session-retro` for "learn from mistakes" | 🟡 | `wc -c` of CLAUDE.md + the 5 always-on rules = 30,814 bytes (~7–8k tokens) vs "under a page". No "mistake twice → always-on" rule; repeat-mistake rate not measured |
| Skills | 13 skills; activation evals (should-trigger + near-miss, ≥8 per polarity + holdout); gate-verifiability principle pairs claims with enforcement tier | ✅ | `evals/skills/prompt-refactor/README.md`; `skills/README.md` |
| Parallel sessions & subagents | `/subagent-driven-development` waves, `/using-git-worktrees`, read-only `reviewer` / `task-reviewer` / `test-runner` agents, `wave-parallelism.md` file-disjointness | ✅ | `agents/`, `rules/wave-parallelism.md`. Ahead of the playbook: tool-level read-only enforcement for reviewers |
| Feedback loop | `### Verify` rows (re-runnable, exit codes), `REQUIRE_VERIFY=1` re-run gate, `test-runner` agent | 🟡 | No test-edit protection: `hooks/` holds only `branch-isolation-guard.sh`, `commit-gate.sh`, `session-knowledge.sh`; `settings.json` registers only PreToolUse + SessionStart; `weakening-validation` is `"mode": "warn"` in `harness-manifest.json`. No failing-test-first protocol: grep of `feature-intake` and `subagent-driven-development` SKILL.md for "failing test / regression test" found nothing |
| Continuous evals in CI | `evals/` (intake-classifier, review-chain, task-review, test-runner, prompt-refactor) with blind runs + deterministic scorers | ❌ (for *continuous*) / ✅ (for eval *quality*) | `evals/README.md`: "the LLM runs are triggered manually, not in CI". `.github/workflows/` = `harness-ci.yml`, `post-merge-maintenance.yml` — neither runs an eval |
| AI in PR review | `/correctness-review` (scored), `/intent-review` (blind to plan), `/context-propagation-audit`, review receipts pinned at PR, `docs/review-escapes.md` (external Codex review → fixture) | 🟡 | Strong pre-PR. No `REVIEW.md` (`ls REVIEW.md` → absent) defining severity / nit cap / do-not-report; no in-PR `@claude` fix loop in our CI |
| Hooks as approval gates | `commit-gate.sh` (secrets, escalation, lane-evidence, risk corroboration, plan scope…), `branch-isolation-guard.sh`, deny-on-no-response `ESCALATIONS.md`, profiles minimal/standard/strict, break-glass env vars | ✅ | CLAUDE.md hook table. Gaps: `settings.json` top-level keys are only `hooks` (no `permissions`, no `sandbox`); `ask` decisions unused; deny messages spot-checked once (`commit-gate.sh:117` has reason + "Run: git add…" route) — the rest **unknown** |
| CI/CD | `harness-ci` (ubuntu+macOS), `ci-strict-gate.sh` two-tier, post-merge bookkeeping PRs, `### Rollback` required on high-risk | 🟡 / ➖ | No `claude -p` judgment step in CI (grep `claude -p` outside specs hits only tests/eval notes). Deployment/MCP tiers ➖ (no deployed app) |
| Closing the loop | `trust-metrics.md` ledger (82 rows, latest 2026-10-02), `harness-audit.sh` → `audit-log.jsonl` + band, `harness-status.sh` | 🟡 | Band is a fixed threshold, not σ-based; last three entries all `findings: 39` ("solutions_stale": 31, "backlog_stale": 8) with no response path → nothing turns a breach into an intent |
| Source of truth | `specs/` tracked in Git; `gh-NNN` slugs; Linear refs (e.g. `MIN-64`) in ledger | 🟡 | Linkage exists informally; no rule naming SoT per artifact |

### 3.1 Where the harness is ahead — keep these, don't "simplify" toward the playbook

- **Evidence tiers** (traceability ≠ provenance ≠ truth) with mandatory `Verifies:` / `Does not
  verify:` lines. The playbook never distinguishes "the row exists" from "the row is honest".
- **Intent oracle independent of plan.** The playbook's compliance pass reviews against
  `plan.md`; our `/intent-review` reviews against the *verbatim request, blind to the plan*, which
  catches a wrong plan that passes its own review. (Playbook relies on the product owner for this.)
- **Index-safe gate config** (`gate-config-must-read-index.md`) — the playbook's own release gate
  admits "an engineer could set `GITHUB_REF` by hand"; we already treat agent-writable config as
  untrusted.
- **Deny-on-no-response escalation** — stronger than "ask", and works headless.
- **Eval honesty discipline** (first run is the record; claims scoped to fixtures) and the
  small-n caution from `2026-07-22-self-improving-harness-adoption.md` — the playbook's "every eval
  passing / maybe a lower threshold" says nothing about noise at n = 20–50.
- **Review-escape ledger** = the playbook's "every incident becomes an eval", already applied to
  review misses.

### 3.2 Where the playbook does not transfer

- **Non-engineer authors, Cowork, product-owner role, Claude Design** — this is a solo meta-repo.
  Relevant only as guidance we ship to consumer repos.
- **Managed settings via MDM** — no org here; but consumers adopting `allowManagedHooksOnly` will
  silently disable our project-level hooks unless they move them into managed settings. That is a
  documentation gap worth closing (see M6).
- **Auto-generated spec.md on intent merge** — ceremony we deliberately scale by signal
  (`rules/orchestration.md` artifact policy). Don't add it.
- **Human approval hooks during Build** — the playbook itself says no; our design already agrees
  (lanes decide ceremony, confidence decides interruption).

---

## 4. Lessons, distilled into what changes for us

1. Our weakest link is the same one the playbook makes central: **the configuration that steers
   the agent (skills, rules, CLAUDE.md, agents) is not regression-tested on change.** We test the
   *hooks* thoroughly (`scripts/run-tests.sh`) but the *prompts* only manually.
2. **A check the agent can edit is not a check.** We apply this to gate config (index-only reads)
   but not to tests during a fix.
3. **A metric with no response tier is decoration.** `audit-log.jsonl` proves it.
4. **Every artifact should carry IDs the next stage cites.** We have `SC-n` and Files; we lack
   them at the intent level (constraints / open questions aren't addressable), so the intent oracle
   can only compare prose.
5. **Small always-on context is a feature.** Every always-on byte is paid every session; detail
   belongs in path-scoped rules or skills (which our two-tier rule loading already supports).

---

## 5. Open questions

- Budget: memory notes the GitHub Actions billing limit was hit on 2026-10-08 — continuous LLM
  evals in hosted CI may not be affordable. Local scheduled runs or a self-hosted runner are the
  likely substitute. **Decision needed from the user.**
- Should the structured intent fields be filled by the agent (risk: paraphrase drift into the
  oracle) or only the verbatim block kept as oracle with structure as a *derived* view? This note
  recommends the latter.
- Whether consumer-facing guidance (managed settings, REVIEW.md, sandbox) belongs in this repo's
  `templates/` or in `docs/` only.

---

## 6. Suggestions — ordered easy → hard

Effort: **S** ≈ hours · **M** ≈ 1–3 days · **L** ≈ a week or more. Lane is the expected
`feature-intake` lane given current hard-gate rules (edits to `hooks/`, `settings.json`,
`templates/`, or workflow-engine prose raise it).

### Easy (S)

| ID | Suggestion | Playbook source | Where | Lane |
|---|---|---|---|---|
| **E1** | **Write a review policy (`REVIEW.md`-style) for the review skills**: what counts as Important vs Nit, a nit cap, a do-not-report list (generated files, anything CI already enforces), and a mandatory "compliance vs PLAN.md SC-n + SUMMARY Intent" pass label on each finding | Play 9 | new `REVIEW.md` or a section in `skills/correctness-review/` | normal (workflow-engine → audit) |
| **E2** | **Audit every deny message for "reason + route to approval"** and add the missing route lines (e.g. "set `BRANCH_ISOLATION_REASON=…`", "record decision in ESCALATIONS.md") | Play 10 | `hooks/commit-gate.sh`, `hooks/branch-isolation-guard.sh`, `hooks/lib/` | high-risk (hooks) |
| **E3** | **Add the "mistake twice" rule to `/compound`**: a learning that recurs a second time is promoted to `critical-patterns.md` (or a path-scoped rule), and the promotion is the compound output | Play 4, Play 9 step 4 | `skills/compound/SKILL.md` | normal |
| **E4** | **Structured intent view under the verbatim block**: optional `Problem / Outcome / Constraints (C1..) / Out of scope / Open questions (Q1..)` fields, explicitly marked *derived, non-oracle*; `/intent-review` keeps using only the verbatim text | Play 1 | `templates/SUMMARY.template.md`, `skills/feature-intake/SKILL.md` | high-risk (templates) |
| **E5** | **Failing-test-first protocol for bug fixes**: when `Input-type` is a bug fix, the `### Verify` table must contain a red row (test fails before fix, with commit sha) and a green row after | Play 7 | `skills/feature-intake`, `skills/subagent-driven-development`, `scripts/verify_summary.py` (advisory first) | normal → high-risk if verifier logic changes |
| **E6** | **Define one leading + one lagging indicator per workflow stage** in `trust-metrics.md` (definitions only, no tooling yet) — e.g. intake→PLAN latency, task-review first-pass rate, plan drift, review-escape rate | All plays' "How to measure it" | `docs/harness-experimental/trust-metrics.md` | tiny |

### Medium (M)

| ID | Suggestion | Playbook source | Where | Lane |
|---|---|---|---|---|
| **M1** | **Trim always-on context toward "one page"**: move the hook table detail, Codex alpha boundary, and long Gotchas out of CLAUDE.md into `HARNESS.md` / path-scoped rules; keep commands, the workflow chain, and "things the agent gets wrong". Measure before/after bytes | Play 4 | `CLAUDE.md`, `rules/` (note: removing always-on status is a behavior change per CLAUDE.md) | high-risk (redefines always-on set) |
| **M2** | **Test-protection hook during fix tasks**: PreToolUse Edit/Write deny on test paths when the active SDD task's Files list excludes them (or the task is a bug fix past its red-test commit); break-glass reason env var; mirror the same check at commit/CI because Edit hooks miss shell rewrites | Play 7, Play 10 | new hook or `branch-isolation-guard.sh` extension + `ci-strict-gate.sh` | high-risk |
| **M3** | **Plan↔diff sync**: when a wave commit stages paths outside PLAN Files, require PLAN.md in the same commit (warn → block after a measured precision window, like `weakening-validation`'s history) | Play 3 | `commit-gate.sh` `check_plan_scope` | high-risk |
| **M4** | **Indicator script**: compute E6's indicators from Git + SUMMARY + ledger (latencies from commit timestamps, plan drift = merged paths ∖ PLAN Files, rework = fix rounds persisted into SUMMARY since `.harness-state/` is gitignored); show in `harness-status.sh` | Play 3/4/12 measurement | `scripts/harness-status.sh`, new `scripts/harness_indicators.py` | normal |
| **M5** | **Adopt the playbook's eval-runner hardening for our existing evals**: each fixture pins a `from` commit and `may_change`; the run happens in a scratch worktree with `evals/` removed; scorer copied before the run; stray-file check fails the run; never `--bare`. Start with `intake-classifier` (cheapest, deterministic scorer exists) | Play 8 | `scripts/run_*_eval.py`, `evals/workflow/intake-classifier/` | normal |
| **M6** | **Consumer security profile + managed-settings guidance**: a `permissions.allow` safe inner loop + secret-read denies in the strict profile; a doc on `allowManagedHooksOnly` (our hooks must move into the managed file or they stop firing) and sandbox credentials | Play 10 (managed settings) | `scripts/install-harness.sh` profiles, `docs/` | high-risk (settings/install) |

### Hard (L)

| ID | Suggestion | Playbook source | Where | Lane |
|---|---|---|---|---|
| **H1** | **Continuous eval gate on configuration change**: any diff to `skills/`, `rules/`, `agents/`, `CLAUDE.md`, or `templates/` runs the relevant eval split (headless `claude -p`) and gates the merge on pass rate — with a margin/significance rule, not plain non-regression (small-n finding from the 2026-07-22 note). Runs locally or on a self-hosted runner given the Actions billing limit | Play 8 | new workflow or local `scripts/run-config-evals.sh` + `ci-strict-gate.sh` hook-in | high-risk |
| **H2** | **Control bands over the harness's own metrics** (audit findings, CI failure rate, review-escape rate, task-review fix rounds): deterministic σ + Western Electric script, unit-tested; `bands.yaml` tiers log / diagnose (read-only) / propose (PR only) | Play 12 | `scripts/harness-audit.sh` successor, `post-merge-maintenance.yml` | high-risk |
| **H3** | **Breach → intent → intake**: the propose tier writes a draft SUMMARY `### Intent` (author: monitoring agent) and routes it to `/feature-intake`; dismissals tune bands. First target: the stuck `solutions_stale: 31` / `backlog_stale: 8` findings | Play 12 | builds on H2 + `skills/feature-intake` | high-risk (redefines workflow entry) |
| **H4** | **In-PR agent review loop** for consumers: `claude-code-action` running a REVIEW.md-driven pass that reads PLAN.md + SUMMARY, `@claude` fix loop until green, second-time findings auto-proposed for `/compound`; human code-owner approval stays the only merge path | Play 9, Play 11 | consumer templates / `.github/` example | high-risk |

### Suggested order

`E6 → E2 → E1 → E3 → E5 → E4` (each is independent and cheap), then `M5 → H1` (the single biggest
gap, and M5 is H1's prerequisite), then `M2 → M3` (protect the loop), then `M4 → H2 → H3`
(measure, then close the loop). `M1` and `M6` can run whenever; `H4` last, as it targets consumers.

---

## Appendix — lesson URLs

Base `https://academy.claude.com/courses/ai-native-sdlc-playbook/`:
`introduction` · `capture-intent` · `requirements-and-design` · `plan-mode` · `claude-md` ·
`skills-as-institutional-knowledge` · `parallel-sessions-and-subagents` ·
`give-claude-a-feedback-loop` · `continuous-evals-in-ci` · `ai-in-the-pr-review-loop` ·
`hooks-as-approval-gates` · `ci-cd-integration-and-deployment` · `closing-the-loop-on-metrics` ·
`closing-thoughts-and-resources`
