# Research: Chachamaru127/claude-code-harness vs. our harness-skills

> Deep-dive of https://github.com/Chachamaru127/claude-code-harness (cloned at v4.15.0,
> ~1,625 files: 188 skill files, 176 Go files, 195 test files, 170 benchmark files,
> 122 docs). Compared against this repo (`harness-skills`).
> Researched: 2026-06-12. Method: full clone + 3 parallel deep-read passes
> (skills/workflow · Go core/automation · testing/benchmarks/portability).

---

## 1. What they do best

### 1.1 A Go-native enforcement core instead of bash hooks

Their guardrail engine is ~54K LOC of Go compiled to a single binary (`bin/harness`),
dispatched from one declarative `hooks/hooks.json` (40+ hook types). Rules R01–R14 are
pure functions `(RuleContext) → {Decision, Reason}` evaluated first-match-wins:

- **Hard-deny**: sudo (R01), protected-path writes — `.git/`, secrets, `*.pem`, SSH keys,
  shell rc files, `.claude/hooks` (R02), secret-file reads (R09), direct edits to
  generated `settings.json` (self-protection).
- **Break-glass ask**: `.env` writes ask *only if* a reason is pre-registered in
  `harness.toml`; otherwise denied (R03).
- **Advisory**: TDD enforcement (R14), reviewer-prohibited commands (R08) — warn, log,
  don't block, until a rollout phase graduates them.

Why it matters: type-safe decisions, a 10ms latency budget no interpreter can hit,
SQLite-backed audit trails (8 tables: sessions, signals, task_failures, work_states…),
and a state machine that survives session restarts.

### 1.2 Benchmarks with actual statistics — they *measured* whether the harness works

This is the rarest thing in the prompt-framework space. `benchmarks/breezing-bench/`
contains a two-phase study of whether their validation instructions improve agent task
success:

- Exploratory: 3 tasks × 30 runs → **93.3% vs 20.0%** pass rate (p<0.001, Cohen's h=1.69).
- Confirmatory (independent design): 10 tasks × 100 runs → **84% vs 40%** (p<0.000005),
  per-task Holm–Bonferroni correction, declared threats to validity, and an honest cost
  ledger (+34% wall-clock, +54% tool calls for the +44 pt gain).
- Raw run data, configs, and analysis scripts archived in-repo.

They also narrowly operationalize the claim ("breezing = `npm run validate` + fix
instructions", not the whole pipeline) and declare confounds — pre-registration
discipline applied to a prompt framework.

### 1.3 Evidence-tier honesty: `not_observed != absent`

Every host (Claude Code / Codex / OpenCode / Cursor / Copilot) carries an explicit tier —
`supported` / `internal-compatible` / `candidate` / `future` — and **a tier only rises
when this repo holds its own bootstrap + trigger + runtime + release evidence**. Support
claims are never inherited from upstream projects. The same epistemics run inside the
skills: a missing search result, unread file, or unavailable memory must stay `unknown`
— the worker agent returns an `advisor-request` instead of guessing when a
behavior-changing task has no spec path and no skip reason.

### 1.4 Machine-checkable Definition of Done per task

Plans.md task rows carry a DoD that is a *list of validators*, not prose:

```
(a) agents/worker.md contains "600s stall" — grep ≥1 hit
(b) schema validation passes
(e) ./tests/validate-plugin.sh PASS
```

Task completion becomes CI-detectable. Status markers embed the commit hash
(`cc:完了 [hash]`), so the plan table doubles as a ledger.

### 1.5 Single-source multi-tool portability

`skills/` is the SSOT; `scripts/sync-skill-mirrors.sh` + `build-opencode.js` generate the
Codex/OpenCode/Cursor mirrors, with a `skills-codex/` overlay for host-specific
overrides and CI checks for adapter-mirror drift. One skill edit propagates everywhere;
divergence is a CI failure, not a doc rot.

### 1.6 Role-scoped tool restriction in frontmatter

The reviewer agent is structurally unable to cheat: `disallowedTools: [Write, Edit,
Bash, Agent]` in frontmatter — review independence is enforced by the harness, not by a
prompt asking nicely. Workers can't nest-spawn agents; the reviewer's APPROVE verdict
explicitly does not grant commit/push permission (commit is a separate gate).

---

## 2. What we are doing well (sometimes better)

| Area | Our position |
|---|---|
| **Risk-lane routing** | Our `/feature-intake` lane system (tiny/normal/high-risk + confidence) is more granular than their flat "lightweight vs non-trivial" split. Their small-typo path is a special case; our lanes are the routing *primitive*, corroborated post-hoc by `risk-corroboration.sh` against the staged diff — they have no equivalent of *machine-checking the declared lane against what was actually changed*. |
| **Ceremony scales with risk, human gate scales with ambiguity** | Their loop is approval-gated by default (user approves every contract). Our notify-and-proceed for high-confidence normal-lane work + `ESCALATIONS.md` deny-on-no-response is a more developed autonomy model. They optimize for one disciplined operator; we optimize for bounded autonomy. |
| **Three independent review oracles** | Our pipeline separates spec compliance → code quality → `/correctness-review` (adversarial, assumes a bug exists) → `/intent-review` (diff vs verbatim request, deliberately blind to PLAN). Their `/harness-review` is one evaluator checking spec/Plans alignment + TDD. Our intent-review's "passed the plan, passed the tests, but not what the user asked" oracle has no counterpart there. |
| **Knowledge compounding** | `/compound` with four track types (bug/knowledge/decision/**failure**), severity triage to `critical-patterns.md`, collision-aware merging, INDEX full-rebuild, and 30-day staleness fields is far richer than their harness-mem (an optional recall daemon with no schema for *what kind* of learning something is and no decay/confidence model). Our agent-memory confidence decay (`high/medium/low` + `review-by`) also has no equivalent. |
| **Codebase-aware review** | Our code-review-graph MCP (impact radius, affected flows, tests-for, blast radius overlay on PLAN.html) gives reviews structural context. Their review is file-read based. |
| **Wave parallelism** | Our zero-file-overlap waves with single-message parallel spawn and a collection protocol are a more explicit parallel-execution model than their Phase 1–4 work.yaml. |
| **Auto-correct scope** | Rules 1–4 (auto-fix / auto-add / auto-fix-blocking / STOP) with mandatory `### Deviations` reporting is a finer-grained autonomy contract than their worker NG-rules. |

Honest caveat: several of their strengths exist precisely where we are weakest — our
gates live in bash + prompt text, and we have **no empirical evidence** our chain
improves outcomes.

---

## 3. What we can learn from this repo

1. **Prove the harness works — with numbers.** We assert our chain (intake → plan →
   two-stage review → correctness → intent) catches problems; they ran 130 controlled
   runs and published p-values and the *cost* of the gain. Lesson: a harness is a
   product claim, and claims need executed evidence. Even a small version — 10 tasks,
   with/without `/correctness-review`, count escaped bugs — would convert our pitch
   from belief to measurement.

2. **Enforcement by construction beats enforcement by prompt.** Their reviewer cannot
   write; ours is instructed not to. Frontmatter `disallowedTools` / `allowed-tools` on
   review-stage agents is a zero-cost structural guarantee we are not using.

3. **`not_observed != absent` as a named, recurring contract.** We have the spirit
   (evidence-over-assertion, "never list a command that was not run") but they *name*
   the epistemic rule and repeat it at every layer — planning, worker, reviewer, support
   tiers. A named rule is greppable, teachable, and citable in reviews.

4. **Generated config with self-protection.** Their `harness.toml` → `settings.json`
   sync plus a guardrail that *denies direct edits to the generated file* eliminates the
   config-drift class entirely. Our `settings.json` vs `settings.local.json` split has
   a doc-truth lint (good) but nothing stops a hand edit from drifting.

5. **Doc claims mapped to evidence tiers.** Their README never says "works with X"
   without a tier and a graduation requirement. Our skills/README handoff map could
   carry the same: which handoffs are exercised in CI vs. merely documented
   (our external superpowers skills are exactly the "candidate" tier they would refuse
   to call supported).

6. **Honest cost accounting.** They report that quality costs +34% wall-clock and +54%
   tool calls. We never quantify what the full chain costs vs. the tiny lane — knowing
   this is what justifies (or trims) ceremony per lane.

---

## 4. Ideas to apply to our project

Ordered by leverage / effort:

### Quick wins (days)

1. **`disallowedTools` on review agents.** Give `/correctness-review` and
   `/intent-review` subagents read-only tool surfaces in their dispatch
   (no Write/Edit/Bash-mutating). Structural review independence for one line of config.
   *(High leverage, trivial effort.)*

2. **Adopt the `not_observed != absent` rule verbatim.** Add it to
   `rules/behavior.md` §1 and to the correctness-/intent-review skill prompts: a finding
   of "no callers found" must state *where was searched*; an unverified claim stays
   `unknown` rather than asserted-absent.

3. **Commit hash in plan status.** Extend PLAN.md Status Log convention so each
   completed task row records its commit sha inline (they embed it in the status
   marker). We partially do this in wave collection; make it a per-task invariant the
   doc-truth lint can check.

### Medium (1–2 weeks)

4. **Machine-checkable DoD in `<done>`.** Today our `<verify>` is one command and
   `<done>` is prose. Borrow their lettered-validator pattern: allow `<done>` to be a
   checklist where each item is grep/test/schema-checkable, so "done" becomes
   re-runnable by a hook rather than judged by an agent.

5. **Break-glass protected paths.** Our Rule 4 STOP list (settings.json, hooks/*,
   render_plan.py) is prompt-enforced. Port their R02/R03 pattern into a PreToolUse hook:
   hard-block writes to the high-blast list, with an "ask with pre-registered reason"
   escape hatch — the reason requirement turns an override into an audit record.

6. **Evidence-tier table for our own integrations.** One table in skills/README:
   each external skill / MCP dependency / handoff edge → `ci-proven` /
   `manually-verified (date)` / `documented-only`, with the rule that an edge only
   moves up with a recorded run. Cheap to add; kills silent rot.

### Larger bets (worth a spec each)

7. **A micro-benchmark for the review chain.** Seed N small tasks with known planted
   bugs / intent drifts; run with and without `/correctness-review` + `/intent-review`;
   record catch-rate and token cost into `benchmarks/`. Even 10 tasks × 5 runs gives us
   our first real number — and a regression alarm when we edit the skills. This is the
   single most valuable practice to steal.

8. **Compile the hot gates to a real binary (or at least one dispatcher).** Our 11 bash
   hooks each re-parse state per invocation. Their model — one entrypoint, declarative
   matcher table, first-match-wins, SQLite ledger, fail-open with timeouts — would make
   our gates faster, testable as units, and give the trust-metrics ledger a real store.
   Go is their choice; for us even a single Python/Go dispatcher consolidating
   `commit-quality-gate` + `risk-corroboration` + `branch-guard` + `blast-radius` would
   capture most of the benefit.

9. **Session/state ledger.** Their SQLite state machine (sessions, signals,
   task_failures, work_states + retry-escalation counters) is what our
   `state-breadcrumb.sh` + STATE.md want to grow into: resumption, repeated-failure
   detection (our "same `<verify>` fails ≥2×" escalation trigger currently relies on
   the orchestrator remembering), and subagent health telemetry become queries instead
   of conventions.

### Explicitly not worth copying

- **Multi-tool mirrors (Codex/OpenCode/Cursor).** Their biggest complexity sink
  (~480 files). We target Claude Code only; nothing to gain.
- **Full approval-gated loop.** Their "user approves every contract" default would be a
  step backwards from our lane/confidence autonomy model.
- **An out-of-process memory daemon.** Our file-based docs/solutions + agent-memory with
  confidence decay is simpler and already more structured than harness-mem.

---

## TL;DR

They built the *engineering* around a harness: compiled guardrails, statistical proof,
evidence-tiered claims, machine-checkable done-ness. We built the *judgment* around one:
risk lanes, bounded autonomy, three review oracles, compounding knowledge with decay.
The highest-leverage steals are (1) benchmark our own review chain, (2) make review
agents structurally read-only, (3) name and enforce `not_observed != absent`, and
(4) consolidate our bash gates into one testable dispatcher with a state ledger.
