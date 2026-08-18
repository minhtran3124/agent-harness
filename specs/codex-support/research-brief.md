# Codex Support — Research Brief for Phases 1–4

**Research depth:** Deep
**Why:** the intake lane is `high-risk`, and the work introduces an external runtime integration,
shared hook/configuration contracts, workflow-engine changes, and high-blast installer surfaces.
**Evidence refreshed:** 2026-08-10

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse the existing harness logic and Codex's built-in skills/hooks/subagents/plugin/doctor surfaces; build only the capability evidence, runtime-policy bindings, and hook-normalisation seams needed for Phases 1–4. |
| **Why this is the lightest credible path** | The workflow core and most hook logic already exist; the unsafe gaps are delivery, payload shape, and runtime policy mapping, not missing workflow behavior. |
| **Confidence** | 90% |
| **Next step** | Author and execute a four-phase plan: capture a versioned capability baseline, prove packaging in an isolated spike, neutralise semantic sources while preserving Claude behavior, then add the tested hook input seam. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Workflow harness / skill framework with generated consumer installations |
| Primary language + runtime | Bash 3.2-compatible shell scripts and Python 3.10+ utilities |
| Frameworks / platforms | Claude Code source-to-`.claude/` deployment; target Codex CLI 0.147.0; GitHub Actions on macOS and Ubuntu |
| Relevant packages | Codex CLI 0.147.0, Git 2.50.1, `jq` 1.7.1, Python 3.10.11; no application dependency manifest |
| Detectable versions | `codex-cli 0.147.0`; hooks/plugins/multi-agent reported stable by `codex features list` |
| Important constraints | One semantic workflow source; preserve Claude behavior; root `AGENTS.md` is user-owned; Bash/jq/Git/Python baseline; tests must work on macOS Bash 3.2 and Ubuntu; Verify rows are pipe-free and under 60 seconds |

---

## Feature Understanding and Assumptions

- **Requested feature:** prepare an executable implementation plan for Codex support Phases 1–4
  after merging the approved peer-runtime design.
- **What success appears to mean:** the repository has enough versioned evidence and neutral shared
  contracts to implement a Codex alpha adapter later without relying on stale hook assumptions,
  overwriting user instructions, or weakening Claude behavior.
- **Assumptions from the request:** D1–D6 in `design.md` are approved; Codex runs agents as a full
  runtime; peer status is the goal; advisory alpha is allowed; the plan stops before Phase 5.
- **Assumptions still needing confirmation:** none that block planning. Phase 2 intentionally leaves
  hybrid-versus-direct packaging as an evidence-driven decision rather than a user preference.
- **Depth re-check:** remains Deep. Local evidence confirmed edits to `hooks/`, `scripts/`, agents,
  rules, settings-adjacent contracts, and an external Codex packaging/runtime surface; no evidence
  lowered the risk.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `settings.json` wires Claude matchers (`Bash`, `Write|Edit`) and five lifecycle event groups; the four edit hooks parse a single `.tool_input.file_path`. |
| `Local` | `scripts/deploy-harness.sh` currently copies `agents/` verbatim into `.claude/`, derives only hook command paths, and already has protected-file conflict/prune machinery worth extending rather than replacing. |
| `Local` | `agents/*.md` pins Claude model IDs and tool allowlists, so direct Markdown-to-TOML transliteration cannot preserve security semantics. |
| `Local` | Eleven runtime-source files reference `.claude/rules/...`; workflow prose also contains Claude `/skill-name` invocation syntax. Existing context-propagation tests prove only two explicit rule-read paths. |
| `Local` | The historical `feature/plugin-namespace-packaging` branch is a stale Claude plugin experiment based on `v1`; it adds `.claude-plugin/*` and changes 48 files. It is pattern evidence only and must not be cherry-picked as a Codex package. |
| `Docs` | Official Codex documentation defines lifecycle hooks, skills, custom subagents, plugin packaging, strict configuration loading, and hierarchical `AGENTS.md` discovery. |
| `Docs` | Codex hooks are enabled by default but project trust and tool-handler coverage affect effective execution; hosted tools do not provide the same lifecycle coverage. |
| `Docs` | Codex plugins are installed through configured marketplace snapshots; plugin CLI supports local/Git marketplace sources, JSON output, add/list/remove/upgrade flows. |
| `Upstream` | Codex CLI 0.147.0 exposes stable `hooks`, `plugins`, `multi_agent`, `unified_exec`, and a redacted `codex doctor --json` schema with version/config/platform checks. |
| `Upstream` | Prior isolated probes captured shell and `apply_patch` pre/post events plus fresh/bounded custom-agent selection; full-history custom-agent override was rejected. These observations must become sanitized fixtures in Phase 1 rather than remain session knowledge. |
| `Inference` | A thin evaluator can consume `codex doctor --json` later; building a second general-purpose doctor would duplicate the runtime's own diagnostics. Harness-specific trust hashes, matcher coverage, and evidence freshness still need an overlay in Phase 5. |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:**
  - `specs/codex-support/design.md` and `SUMMARY.md` own the approved decisions and negative scope.
  - `settings.json` is the Claude hook-registration source.
  - `hooks/branch-isolation-guard.sh`, `blast-radius-check.sh`, `ruff-on-edit.sh`, and
    `render-plan-on-write.sh` assume one `.tool_input.file_path`.
  - `hooks/pre-bash-dispatch.sh` and its git sub-hooks already consume command-shaped input and are
    useful compatibility examples.
  - `hooks/state-breadcrumb.sh` is intentionally a bounded, non-blocking `SessionEnd` hook.
  - `scripts/deploy-harness.sh` and `scripts/install-harness.sh` own copy, merge, prune, and conflict
    behavior for consumer installs.
  - `harness-manifest.json` owns component inventory and contract surfaces.
  - `tests/hooks/*.test.sh`, `tests/scripts/*install*.test.sh`, `resync-conflict.test.sh`, and the
    Python manifest/plan tests provide the existing contract-test pattern.
- **Existing abstractions or extension points:**
  - `hooks/lib/` is the natural home for a runtime-neutral payload normaliser.
  - `harness-manifest.json` already connects sources to consumers and can register new capability
    artifacts without creating another inventory system.
  - deploy protected-file and `.harness-deployed` logic already solves preserve/upgrade/prune
    behavior for Claude; Phase 2 should model its invariants.
  - `scripts/check_manifest.py`, `scripts/check_plan_contract.py`, and shell contract tests show how
    deterministic evidence is enforced without external Python packages.
- **Conventions worth preserving:**
  - Bash 3.2 compatibility, explicit error boundaries, and cross-platform CI.
  - Index-side reads for any commit-gate policy input.
  - `not_observed != absent`: unknown capability remains unknown/advisory.
  - Full suites belong in CI prose, never sub-60-second Verify rows.
  - Consumer custom files survive re-sync; conflicts produce reviewable incoming sidecars.
- **What can likely be reused:** workflow logic, hook bodies after normalisation, run-state/artifact
  schemas, skill content, installer conflict primitives, manifest checks, and test harness helpers.
- **What appears missing locally:** a versioned Codex capability schema and sanitized observations;
  a reproducible packaging spike; a neutral agent capability schema plus runtime bindings; a
  runtime-neutral prose lint; and a multi-path hook input API with explicit unknown policies.

---

## Upstream Findings

- **Repositories inspected:** this repository's `feature/plugin-namespace-packaging` branch and the
  installed Codex CLI 0.147.0 command surface. Official Codex documentation/changelog supplied the
  versioned external contract.
- **Pattern or capability already present upstream:** Codex provides plugin marketplace management,
  strict config parsing, skills, hook registration, custom-agent TOML, and a redacted JSON doctor.
- **Files, modules, or areas worth modeling:** the old branch's minimal plugin/marketplace manifest
  separation is a useful concept, but its `.claude-plugin` format, namespace rewrite, installer
  changes, and old base are not reusable implementation.
- **How closely the upstream pattern matches this repo:** Codex plugin ownership fits reusable
  skills/hooks, while project-owned custom agents and repository instructions still need a separate
  adapter boundary. This supports the approved hybrid hypothesis but does not prove it.
- **Any upstream gaps or uncertainties:** plugin hook discovery/trust and local upgrade behavior
  have not been executed in a disposable Codex installation; WSL and native Windows remain
  unobserved; specialized/hosted handler coverage is incomplete by contract.

---

## Docs Findings

- **Official sources checked:** Codex hooks, skills, subagents, plugins, configuration reference,
  changelog, and repository instruction (`AGENTS.md`) documentation.
- **Version-matched vs latest-stable status:** docs were checked as current on 2026-08-10 and CLI
  observations were pinned to 0.147.0. Future probe evidence must record its own CLI version and
  config hash rather than silently inheriting this date.
- **Built-in capabilities that already support the feature:** lifecycle hooks, plugin/skill
  discovery, custom agents, strict config validation, feature listing, and `codex doctor --json`.
- **Current recommended APIs or workflows:** distribute reusable skills/hooks through plugins;
  configure custom agents in `.codex/agents/*.toml`; use hierarchical root-to-CWD `AGENTS.md` for
  repository instructions; use strict config loading for generated configuration.
- **Important caveats, deprecations, or migration notes:** trust/config state is part of effective
  hook coverage; hosted/specialized tools are not universally covered; full-history forks cannot be
  assumed to accept a new custom-agent type; historical hook-gap issues must not be treated as the
  current baseline without a versioned probe.

---

## Recommendation

- **Primary recommendation:** reuse existing harness behavior and Codex built-ins, then add four
  narrow seams in order:
  1. a versioned capability matrix, sanitized evidence fixtures, and reproducible capture/check
     commands;
  2. a disposable hybrid-versus-direct packaging spike with an explicit decision artifact;
  3. neutral skill/rule/agent semantics plus tested Claude/Codex policy bindings, preserving Claude
     output byte/behavior contracts;
  4. one multi-path hook normaliser and explicit per-gate unknown policy.
- **Why this is the lightest credible path:** it changes only the surfaces proven runtime-specific
  and reuses existing deploy conflict rules, hook logic, test helpers, and Codex's own diagnostics.
- **Why the next-best alternative lost:** forking the harness doubles workflow-policy drift; direct
  format transliteration hides security policy; building a full custom doctor duplicates Codex;
  cherry-picking the old plugin branch imports a Claude-specific format and years of stale changes.
- **What would change this recommendation:** if the Phase-2 live spike proves plugin discovery or
  trust cannot satisfy project-local/reinstall contracts, choose direct project sync. The semantic
  core, capability matrix, and hook normaliser remain unchanged.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - parsing patch envelopes incompletely can recreate a silent fail-open;
  - extracting Claude model/tool fields from agent sources can regress current agent discovery or
    reviewer isolation;
  - packaging probes can mutate a developer's real Codex marketplace/config if not run in a truly
    disposable environment;
  - bulk invocation/rule-path edits can change prompt meaning while appearing mechanical;
  - hook helpers must remain compatible with macOS Bash 3.2 and bounded enough for lifecycle
    timeouts;
  - per-gate `unknown` behavior can drift unless encoded in deterministic tests.
- **Evidence gaps:** no checked-in payload fixtures yet; no disposable plugin install/upgrade run;
  no WSL observation; no native Windows adapter; no exhaustive specialized-tool coverage.
- **Version uncertainties:** Codex capabilities are pinned to 0.147.0; plugin, hook trust, and agent
  schemas may evolve. The capability matrix must make version/config drift visible.
- **Follow-up questions for the user:** none. D1–D6 and the advisory-alpha boundary are already
  recorded; Phase 2 owns the remaining packaging decision.

---

## Source Pack

- **Local files read:** `AGENTS.md`, `CLAUDE.md`, `README.md`, `harness-manifest.json`,
  `settings.json`, `rules/research-depth.md`, `rules/plan-format.md`,
  `specs/codex-support/design.md`, `specs/codex-support/SUMMARY.md`, `agents/*.md`,
  `hooks/branch-isolation-guard.sh`, `hooks/blast-radius-check.sh`, `hooks/ruff-on-edit.sh`,
  `hooks/render-plan-on-write.sh`, `hooks/state-breadcrumb.sh`, `scripts/deploy-harness.sh`,
  `scripts/install-harness.sh`, `scripts/check_manifest.py`, relevant hook/install tests,
  `docs/solutions/critical-patterns.md`, `docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md`,
  `docs/solutions/harness/gate-config-must-read-index.md`, and
  `docs/solutions/harness/automation-readiness.md`.
- **Upstream repositories or pages checked:** local branches
  `feature/plugin-namespace-packaging` / `github/feature/plugin-namespace-packaging`; installed
  Codex CLI 0.147.0 command surfaces (`features`, `plugin`, `doctor`, `--strict-config`).
- **Official docs domains or pages checked:**
  [Codex hooks](https://developers.openai.com/codex/hooks),
  [Codex skills](https://developers.openai.com/codex/skills),
  [Codex subagents](https://developers.openai.com/codex/subagents),
  [Codex plugins](https://developers.openai.com/plugins/build/plugins),
  [Codex configuration reference](https://developers.openai.com/codex/config-reference),
  [Codex changelog](https://developers.openai.com/codex/changelog), and
  [AGENTS.md instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

---

## Evidence Boundary

> Confirmed from artifacts: repository hook/config/agent/deploy behavior; Codex CLI 0.147.0 feature,
> plugin, strict-config, and redacted-doctor command surfaces; approved D1–D6; prior isolated shell,
> apply-patch, and custom-agent observations recorded in the merged design.
>
> Inferred from patterns: hybrid packaging is likely the smallest package boundary; a thin
> harness-specific doctor overlay can reuse `codex doctor --json`; semantic agent sources plus
> explicit bindings can preserve Claude behavior.
>
> Not checked: a disposable Codex plugin install/upgrade/uninstall cycle; WSL/native Windows;
> exhaustive hosted/specialized handler coverage; checked-in replay of the prior live probes; Phase
> 5+ adapter, runtime mode recording, deterministic parity gate, and behavioural parity.
