---
type: architecture overview
title: Architecture Overview
description: How the agent-harness repo is split into an engine (skills and agents that do the work) and a harness (intake, hooks, rules, specs that decide how much process a change needs), which systems each layer owns, how a request flows from intake to ship, and where the Claude Code vs Codex runtime boundary lies.
tags: [architecture, harness, hooks, skills, codex, claude-code, run-state]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-16T04:08:21.021Z
sources:
  - id: openwiki-source-6aba6ee552a124c259124ea8
    resource: repo://adapters/codex/plugin/hooks/hooks.json
  - id: openwiki-source-a2371d6362e5db4bc834ad03
    resource: repo://CLAUDE.md
  - id: openwiki-source-09e4fd34eaf58fd8da3d4f9c
    resource: repo://evals/README.md
  - id: openwiki-source-991face7ae593d36af0365be
    resource: repo://harness-manifest.json
  - id: openwiki-source-8712df4ec416d99923280ee7
    resource: repo://HARNESS.md
  - id: openwiki-source-172c2c67283fed484624bfb6
    resource: repo://hooks/branch-isolation-guard.sh
  - id: openwiki-source-da1abaef00ad290b88a0eeda
    resource: repo://hooks/commit-gate.sh
  - id: openwiki-source-228dccaa8b5486a95fa82a08
    resource: repo://hooks/lib/gate-modes.default.sh
  - id: openwiki-source-13ebb3647c7b28e446f508e2
    resource: repo://hooks/lib/normalize-tool-input.py
  - id: openwiki-source-55df0141e1e141a2764e352c
    resource: repo://hooks/session-knowledge.sh
  - id: openwiki-source-5530e7d6799784924630358b
    resource: repo://runtime/run_state.py
  - id: openwiki-source-5813dbda4da15f9e0a4e7db5
    resource: repo://runtime/runtime_mode.py
  - id: openwiki-source-a3bde1c56e5cd62cf73ec2b5
    resource: repo://scripts/codex_harness_doctor.py
  - id: openwiki-source-4a7eaf43ec1d74d5deee3c15
    resource: repo://scripts/deploy-harness.sh
  - id: openwiki-source-fbebfbe1b8783e191e2e1099
    resource: repo://scripts/install-codex-harness.sh
  - id: openwiki-source-e06a69a77c57b73c48b87f54
    resource: repo://scripts/render_codex_adapter.py
  - id: openwiki-source-139b698785417c0b4c884c72
    resource: repo://scripts/run-tests.sh
  - id: openwiki-source-8d67ed5c5b1bd7083b7dcfc9
    resource: repo://settings.json
  - id: openwiki-source-90294476dddd37583da0fb1a
    resource: repo://templates/SUMMARY.template.md
generated: { by: "openwiki/0.7.2", at: "2026-10-16T04:08:21.021Z" }
---

# Architecture Overview

This repository is a **skills framework with a risk/trust harness on top of it**. You can read it as two layers that answer two different questions:

- **The engine** answers *"how do I build this?"* It is made of invocable `/skills` (brainstorm, research, plan, build, review, ship) and sub-agent roles.
- **The harness** answers *"how careful should I be, and who needs to approve?"* It is a thin control layer that decides, *before* the engine runs, how much ceremony a change needs and when to involve a human. Hooks then check, at edit time and commit time, what the agent said it would do.

One principle drives the harness: **ceremony scales with risk, and human interruption scales with ambiguity.** These are two separate dials. Risk (the *lane*) controls how much planning, review and evidence a change carries. Confidence and ambiguity only control whether a human is asked ([HARNESS.md](../../HARNESS.md)).

## The two layers

| Layer | Responsibility | Lives in |
|---|---|---|
| Engine | Skills that do the work. Each has hard gates and a defined handoff to the next skill. Sub-agent roles (`coding`, `reviewer`, `task-reviewer`, `test-runner`) carry out the delegated steps. | `skills/`, `agents/` |
| Harness | Classifies risk and confidence, records the decision, enforces branch isolation and commit evidence, and supplies governance rules. | `skills/feature-intake/`, `hooks/`, `rules/`, `specs/<slug>/SUMMARY.md` |

Around these two layers sit the supporting systems this repo owns: the durable run-state runtime (`runtime/`), deterministic checkers and deploy tooling (`scripts/`), artifact templates (`templates/`), the generated Codex adapter (`adapters/codex/`), behavioral evals (`evals/`), and the knowledge base (`docs/solutions/`). [`harness-manifest.json`](../../harness-manifest.json) is the single machine-readable inventory that ties them together (see [Harness Manifest and Contracts](../concepts/harness-manifest-and-contracts.md)).

## Request flow: intake → build → hooks → ship

```mermaid
flowchart TD
    REQ[User request] --> INTAKE["/feature-intake"]
    INTAKE -->|writes Lane and Confidence| SUM["specs/slug/SUMMARY.md"]
    INTAKE --> BRANCH[Cut a task branch]
    BRANCH --> LANE{Lane}
    LANE -->|tiny| EDIT[Direct Edit]
    LANE -->|normal| SDD["/subagent-driven-development"]
    LANE -->|high-risk| CHAIN["/brainstorming then /xia2 then /writing-plans"]
    CHAIN --> SDD
    SDD --> REVIEWS["correctness-review and intent-review"]

    subgraph ENGINE [Engine: skills and agents]
        EDIT
        CHAIN
        SDD
        REVIEWS
        AGENTS["agents: coding, reviewer, task-reviewer, test-runner"]
    end
    SDD -.-> AGENTS

    subgraph HARNESS [Harness: hooks, rules, specs]
        BIG["branch-isolation-guard.sh on Edit or Write"]
        CG["commit-gate.sh on Bash git commit or push"]
        SK["session-knowledge.sh on SessionStart"]
        RULES["rules/*.md"]
        MANIFEST["harness-manifest.json gate modes"]
    end

    EDIT --> BIG
    SDD --> BIG
    REVIEWS --> CG
    EDIT --> CG
    SUM --> CG
    MANIFEST --> CG
    CG -->|allow| SHIP["/compound then /finishing-a-development-branch"]
    CG -->|deny| FIX[Fix lane, evidence or diff]
    FIX --> CG
    RULES -.-> INTAKE
    SK -.-> INTAKE
```

*Engine skills do the work. Harness hooks check each edit and each commit against the lane that intake declared, before the work can ship.*

Step by step:

1. **Intake runs first.** `/feature-intake` classifies the request with a risk checklist and the hard gates. It writes `Lane:` and `Confidence:` into `specs/<slug>/SUMMARY.md`, a file copied from [`templates/SUMMARY.template.md`](../../templates/SUMMARY.template.md). The header block of that template is machine-read: `commit-gate.sh` greps the `Lane:` line.
2. **Every lane cuts a branch before the first edit.** `branch-isolation-guard.sh` denies implementation edits on a shared branch (`HARNESS_SHARED_BRANCHES`, default `main`/`master`), whatever the lane.
3. **The lane picks the path.** *tiny* edits directly with no plan. *normal* runs `/subagent-driven-development` with one task reviewer that gives two verdicts. *high-risk* runs the full chain `/brainstorming → /xia2 → /writing-plans → build`. After the build come `context-propagation-audit` (for workflow-engine diffs), `correctness-review`, and `intent-review`, which compares the diff with the original request and does not see the plan. Then `/compound` and `/finishing-a-development-branch`. See [Skill Chain](../workflows/skill-chain.md).
4. **Escalation follows confidence, not lane.** Low confidence, or a hard gate, stops the work and records a question in `specs/<slug>/ESCALATIONS.md` (deny-on-no-response). A hard gate found mid-task escalates whatever the original lane was.
5. **Hooks check the claim.** At commit time, `commit-gate.sh` compares the staged diff with the declared lane. An agent therefore cannot label a risky change "tiny" and commit it. See [Commit Gate](../enforcement/commit-gate.md).

## Major owned systems

### Hooks (`hooks/`)

Three bash hooks are registered in the root [`settings.json`](../../settings.json):

| Hook | Trigger | Role |
|---|---|---|
| `commit-gate.sh` | PreToolUse `Bash` | The only gate for `git commit`/`push`. Bash calls that are not git exit at once. Shell input it cannot fully parse is denied. It runs the secrets scan, the pending-escalation gate, the lane-evidence gate (`verify_summary.py --lane`), the run-state artifact gate, risk corroboration, and the plan-scope check, plus strict-only app gates. |
| `branch-isolation-guard.sh` | PreToolUse `Write\|Edit` | Blocks implementation edits on a shared branch. It looks at the checkout that owns each edited path, not the directory the session was launched from. Edits whose paths are all under `specs/*` count as bookkeeping and are allowed. |
| `session-knowledge.sh` | SessionStart | Loads `docs/solutions/critical-patterns.md`, an `INDEX.md` pointer, up to 5 active runs from `runtime/run_state.py list --active --json`, and the cached Codex runtime-mode context. It never blocks: every path exits 0. |

Both PreToolUse hooks pass the raw tool payload through `hooks/lib/normalize-tool-input.py`. This normalizer converts Claude and Codex payloads, including Codex `apply_patch` programs, into one path-set contract. It tells the runtimes apart by the payload shape (`turn_id` means Codex, `session_id` means Claude), and any input it cannot fully resolve is reported as `unknown`. The hooks treat `unknown` as a deny. The commit gate reads per-gate block/warn modes only from the git index (`git show :harness-manifest.json`) or from defaults built into `hooks/lib/gate-modes.default.sh`. It never reads a worktree copy, because an agent could edit that copy just before the gate reads it.

Hook profiles (`minimal`, `standard`, `strict`) are listed in `harness-manifest.json` `hook_profiles`. The installer applies them. `minimal` drops `session-knowledge.sh`, and `strict` adds the app gates.

### Rules (`rules/`)

The governance rules are Markdown prose. Loading has two tiers, set by each file's frontmatter. A rule file **without** `paths:` frontmatter loads in every session: `behavior.md`, `architecture.md`, `guidelines.md`, `orchestration.md`, `research-depth.md`. A rule file **with** `paths:` loads only when a matching `specs/**` file is read: `plan-format.md`, `wave-parallelism.md`, `auto-correct-scope.md`, `terminology.md`, `review-policy.md`. So adding `paths:` to a rule takes it out of the always-on set. Rules are what the code cannot check mechanically. Anything that can be checked mechanically becomes a hook or a checker.

### Specs and templates (`specs/`, `templates/`)

`specs/<slug>/` is the tracked record of each unit of work: `SUMMARY.md`, `PLAN.md`, `ESCALATIONS.md`, intent files, review receipts, and the run-state files. `templates/` holds the canonical shapes (`SUMMARY`, `ESCALATIONS`, `INTENT`, `QUESTIONS`, `REVIEW-RECEIPT`). The SUMMARY template defines the evidence contract:

- a five-field header: `Lane`, `Confidence`, `Reason`, `Flags`, `Affects`;
- the verbatim `### Intent`, which `intent-review` uses as its reference;
- a `### Verify` table with one row per check that was actually run;
- a `### Not auto-verified` section that states which claims no gate checks.

The manifest records `templates/SUMMARY.template.md` as a contract surface whose consumers are `scripts/verify_summary.py` and `hooks/commit-gate.sh`.

### Runtime run-state (`runtime/`)

[`runtime/run_state.py`](../../runtime/run_state.py) is a durable, event-sourced state machine for each spec slug. It keeps three files per slug:

- `specs/<slug>/events.jsonl`: an append-only event log;
- `events.jsonl.lock`: an `fcntl` lock around the read-validate-append sequence;
- `RUN.json`: an atomically written projection that can be rebuilt from the event log.

Its states are active (`queued`, `investigating`, `planning`, `implementing`, `verifying`, `awaiting_ci`, `ready_to_merge`, and others), interrupt (`blocked`, `escalated`), and terminal (`shipped`, `cancelled`, `superseded`). Waiting states need `--waiting-on`, and interrupt states need `--resume-event`. The CLI (`init`, `transition`, `status`, `list`, `rebuild`) returns 0 on success, 2 for invalid input or an invalid transition, and 3 for storage, chain, or projection failures. Its callers, as listed in the manifest's `durable-run-state-checkpoints` contract, are the intake, subagent-driven-development, and finishing skills, `session-knowledge.sh`, `scripts/harness-status.sh`, and the post-merge maintenance workflow. `runtime/resume_decision.py` turns run state into a resume action and task cursor for `resume <slug>`. `runtime/runtime_mode.py` stores sanitized Codex doctor results in the gitignored `.harness-state/codex-runtime.json`. Details are in [Run-State Engine](../runtime/run-state-engine.md).

### Scripts and checkers (`scripts/`)

`scripts/` contains three kinds of tool:

- **Evidence checkers** that gates call. `verify_summary.py` decides what counts as lane evidence. Others include `check_plan_contract.py` and `check_review_receipt.py`.
- **Consistency checkers** that CI runs. `check_manifest.py` checks the manifest against the hook and skill inventories. `lint-doc-truth.sh` fails when a documented path is missing or the hooks table contradicts `settings.json`. There are also `check_runtime_neutral_sources.py` and the Codex capability and packaging checkers.
- **Deploy and render tooling**: `deploy-harness.sh`, `install-harness.sh`, `render_agent_definitions.py`, `render_codex_adapter.py`, `deploy-codex-adapter.sh`, `codex_harness_doctor.py`.

`scripts/run-tests.sh` is the single test entry point that CI runs. It covers syntax checks, the doc-truth lint, the manifest checks, the hook contract tests in `tests/hooks/`, the script integration tests in `tests/scripts/`, and the Python unit tests.

Not all of `scripts/` reaches consumers. Only an allow-list (`CONSUMER_SCRIPTS`: `verify_summary.py`, `check_plan_contract.py`, `check_review_receipt.py`, `resolve_finish_context.py`, and a few others) is synced into consumer repos. The rest is harness-development tooling.

### Evals (`evals/`)

`evals/` holds fixture-based *behavioral* evals that measure skill judgment against labeled ground truth:

- `workflow/intake-classifier/` scores how accurately `/feature-intake` assigns lanes;
- `skills/review-chain/` scores how many planted defects the reviewers catch;
- `agents/test-runner/` scores the accuracy of the `test-runner` role.

Scoring is scripted and deterministic (for example `scripts/score_intake_eval.py`). The LLM runs themselves are triggered by hand, not in CI. This keeps them separate from the deterministic tests that `run-tests.sh` executes.

### Knowledge base (`docs/solutions/`)

`docs/solutions/<category>/<slug>.md` entries with YAML front-matter record solved problems and decisions. `INDEX.md` is the browsable index, and `critical-patterns.md` is read at planning time. `session-knowledge.sh` loads both at session start, and `/compound` writes new entries after shipping.

## Source tree vs deployed tree

The root directories are the source of truth. Claude Code loads skills, agents, hooks, and rules from `.claude/`, which is a **derived, gitignored copy** built by `scripts/deploy-harness.sh`. For consumer projects, `install-harness.sh` calls the same script with `--target`. The deploy syncs `skills`, `agents`, `hooks`, `rules`, `templates`, `runtime`, and the allow-listed `scripts`. It rewrites hook commands to `$CLAUDE_PROJECT_DIR/.claude/hooks/...`, merges with the consumer's own `settings.json` hooks instead of replacing them, and does not overwrite per-repo files that the consumer owns (`rules/architecture.md`, `rules/guidelines.md`, `rules/behavior.md`, `agents/PROJECT.md`). When such a file differs, the incoming copy is written beside it as `<file>.harness-incoming`. `agents/*.json` and `adapters/` are inputs used only when rendering adapters in this repo, and they never deploy.

## Claude Code vs Codex runtime boundary

**Claude Code is the established runtime.** The **Codex advisory alpha** is a generated adapter that does not overwrite existing files. It renders the *same* skills, agents, and hook bodies through checked Codex bindings. It is **not** a peer enforcement runtime and not GA. Full observed evidence exists only for Codex CLI 0.147.0 on macOS arm64.

How the boundary works:

- **Rendering.** `scripts/render_codex_adapter.py` derives `adapters/codex/plugin/hooks/hooks.json` from the root `settings.json`. Each command is rewritten to `bash "$PLUGIN_ROOT/hooks/..."`, the `Write|Edit` matcher becomes `apply_patch|Edit|Write`, and SessionStart handlers get an `additionalContextLimit` of 2500. A hook event that has no mapping aborts the render. `adapters/codex/schema.json` is a closed schema (runtime `codex`, packaging `hybrid`) for the rendered inventory. Agent definitions for both runtimes are rendered from `agents/agent-contracts.json` and `agents/runtime-bindings.json`.
- **Installation.** `scripts/install-codex-harness.sh` delegates to `deploy-codex-adapter.sh`. That script installs the plugin, a project overlay, and a bounded `AGENTS.md` block, and it never replaces the Claude `.claude/` deployment.
- **Shared hook bodies.** Codex runs the same `hooks/*.sh` scripts. The input normalizer is what lets one set of scripts handle both payload formats.
- **Diagnosis happens outside hooks.** `scripts/codex_harness_doctor.py` reports `enforced`, `advisory`, or `unsupported`, and only `macos-arm64` is a supported platform. Its result is stored by `runtime/runtime_mode.py`. `session-knowledge.sh` only *displays* the cached result; it never runs the doctor. No current input carries observed hook trust, so a real run today returns `advisory` or `unsupported`. Treat an `enforced` result today as a bug.
- **SUMMARY metadata.** The optional `Runtime-mode` / `Runtime-evidence-id` pair in a SUMMARY is checked only for format by `verify_summary.py`. The doctor, not the commit gate, decides the actual mode.

See [Codex Advisory Alpha](../integrations/codex-advisory-alpha.md) for the install lifecycle and trust model.

## Invariants worth knowing before changing things

- **Each gate enforces one evidence tier.** The tiers are traceability (the structure exists), provenance (the evidence is re-derived from the source of truth), and truth (the check is re-run). A gate must not claim a higher tier than it enforces, and new gates document `Verifies:` / `Does not verify:` ([CLAUDE.md](../../CLAUDE.md)).
- **Some paths are hard gates in their own right.** `settings.json`, `hooks/*`, and core skill engines are `high-blast` (block mode). Skill, agent, and rule prose is `workflow-engine` (warn mode). On PRs, `scripts/ci-strict-gate.sh` blocks diffs to `hooks/`, `settings.json`, `templates/`, or `render_plan.py` unless they come with a high-risk SUMMARY whose Verify rows re-run clean.
- **Edit the manifest, not its copies.** The hard-gate vocabulary is copied into `skills/feature-intake`, `rules/auto-correct-scope.md`, and `commit-gate.sh`. CI checks those copies against `harness-manifest.json`.
- **MCP output is untrusted input.** The harness trusts only its own hooks and scripts.
