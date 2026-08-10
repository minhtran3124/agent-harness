---
slug: codex-support
status: active
owner: Minh Tran
created: 2026-08-10
---

# Codex Support — Phase Roadmap (Phases 1–4)

This is the umbrella record for making Codex a peer workflow runtime. It holds the shared design
artifacts and the constraints every phase inherits. **Executable tasks and Success Criteria live in
the per-phase plans**, not here — one plan per independently-shippable phase, so each phase can land
with a complete and honest evidence record instead of waiting on the whole initiative.

| Phase | Plan | Status | Delivers |
| --- | --- | --- | --- |
| 1 | `specs/codex-support-phase-1/PLAN.md` | active | versioned capability baseline: matrix, validator, sanitized 0.147.0 evidence, capture contract suite |
| 2 | `specs/codex-support-phase-2/PLAN.md` | proposed | evidence-driven packaging decision: disposable hybrid-vs-direct probe, recorded decision + fallback trigger |
| 3 | `specs/codex-support-phase-3/PLAN.md` | proposed | semantic source neutralisation: repository-rooted rule delivery, invocation-neutral prose, neutral agent contracts |
| 4 | `specs/codex-support-phase-4/PLAN.md` | proposed | runtime-neutral hook input seam: one payload normaliser, fail-closed gates, advisory hooks unchanged |

Shared artifacts owned by this slug and consumed across phases:

- `design.md` / `design.vi.md` — the approved high-level design.
- `research-brief.md` — the deep research behind it.
- `capability-matrix.json` + `evidence/codex-<version>/` — written in Phase 1, read by Phases 2 and 4.
- `SUMMARY.md` — the design-phase record (PR #194).

## 1. Motivation

The approved design establishes Codex as a future peer workflow runtime, but an alpha adapter must
not be built on session-only observations or field-for-field assumptions. Phases 1–4 create the
evidence and neutral seams that make Phase 5 safe: a versioned capability baseline, an executable
packaging decision, runtime-neutral instruction/agent policy, and one tested hook-input contract.

## 2. Non-goals

- Emitting or installing the production Codex alpha adapter from Phase 5.
- Modifying the root `AGENTS.md`, creating a production `.codex/` tree, or claiming non-clobber
  integration is complete.
- Adding runtime mode recording, the final harness-specific doctor overlay, review-receipt
  provenance, per-PR Codex parity gates, or behavioural parity from Phases 5–7.
- Claiming native Windows support. The target baseline remains macOS, Linux, and WSL; unobserved
  platforms stay explicit.
- Forking workflow policy, skills, rules, or hook bodies per runtime.
- Running paid/networked Codex probes as blocking per-PR CI.
- Cherry-picking the stale Claude-only `feature/plugin-namespace-packaging` branch.
- Neutralising hook/script user-facing message prose (e.g. the `/compound` hint printed by
  `hooks/commit-quality-gate.sh`): Phase 3 Task 3.1 classifies these as owned runtime-entry
  exceptions deferred to Phase 5 rather than rewriting high-blast hook bodies in a bulk prose wave.

## 3. Shared constraints (inherited by every phase plan)

- Execute in an isolated worktree/branch based on current `simplify`; preserve all unrelated and
  untracked user files.
- Run `bash scripts/run-tests.sh` before the first `hooks/` or `scripts/` implementation edit and
  once after all tasks. Record full-suite evidence in the Status Log/SUMMARY prose, never as a
  sub-60-second Verify row.
- Treat official documentation as traceability, sanitized captured output as provenance, and live
  behavioral probes as truth. Every capability row states `observed`, `documented`, or `unknown`,
  with CLI version, platform, config hash, evidence path, and freshness; unknown never becomes pass.
- Deterministic tests require no Codex authentication, network, or mutation of a developer's real
  Codex configuration. Live probes run only in a disposable OS account/runner and clean up the exact
  resources they create.
- Never log credentials, tokens, full transcripts, user home paths, repository absolute paths, or
  unrelated Codex configuration. Fixtures are schema-minimal and sanitized before commit.
- Preserve Claude's installed behavior and conflict/prune guarantees.
- Shared sources use repository-root rule paths and invocation-neutral skill names. Runtime-specific
  syntax belongs only in runtime entry/binding artifacts.
- Root `AGENTS.md`, production `.codex/`, `settings.json`, and the Phase-5 installer surface are
  outside these plans and must remain byte-identical.
- Keep Bash compatible with macOS Bash 3.2; prefer Python stdlib for structured parsing; all focused
  checks are pipe-free and complete in under 60 seconds.
- Workflow-engine changes require a context-propagation audit during implementation, followed by the
  normal correctness and intent review chain before shipping.

## 4. Cross-phase risks

- **Capability evidence becomes stale while still looking complete.** Mitigation: version/platform/
  config hashes, freshness rules, fixture existence checks, and explicit unknown states.
- **Live probes mutate real Codex state or incur unplanned model cost.** Mitigation: disposable
  account/runner precondition, paid-probe flag, fake CLI tests, exact cleanup ledger, and no blocking
  live CI.
- **The packaging spike accidentally becomes an unsupported production adapter.** Mitigation: only
  temporary generated candidates and evidence are committed; production plugin/project files remain
  Phase 5.
- **Bulk prose neutralisation changes policy meaning.** Mitigation: inventory-first changes, context
  review per match, handoff/structural regressions, and mandatory context-propagation audit.
- **Agent extraction weakens Claude reviewer isolation.** Mitigation: total capability mapping,
  semantic/golden comparison, explicit read-only/no-nesting assertions, and deploy conflict tests.
- **Patch parsing misses an edit form.** Mitigation: observed golden fixtures, mutation cases,
  partial/unknown status, branch guard fail-closed, and advisory hooks fail-visible.
- **macOS/Linux shell behavior diverges.** Mitigation: keep structured parsing in Python stdlib,
  preserve Bash 3.2 compatibility, and run the full cross-platform CI suite before shipping.
- **Phase boundaries drift.** Mitigation: no production Codex install, root instruction mutation,
  runtime-mode schema, review provenance, or parity/GA work enters Phases 1–4; record any discovered
  need as a Phase-5+ follow-up rather than auto-expanding scope.

## 5. Status Log

- 2026-08-10 — PR #194 merged into `simplify` at `cf29af3`. Deep research refreshed against the
  current tree, Codex CLI 0.147.0, official OpenAI documentation, installed CLI command surfaces,
  and the stale Claude plugin branch. `research-brief.md` and the proposed Phase 1–4 plan authored;
  no implementation performed.
- 2026-08-10 — Claude Code reviewed the Codex-authored plan and updated it (file lists
  grep-checked against the tree): added the missed `tests/scripts/writing-plans-contract.test.sh` to
  Task 3.2 (its line 5 asserts the literal `.claude/rules/plan-format.md` read that 3.2 rewrites);
  added `templates/` neutralisation to Task 3.3 and the hook/script message-prose owned exception to
  Task 3.1 and Non-goals; added Task 4.4 + the dispatch/prompt criteria closing the
  `pre-bash-dispatch.sh`/`scope-gate.sh` empty-fallback fail-open (design §3.1 applied to
  shell/prompt gates) with unified-exec and UserPromptSubmit golden fixtures added to Task 4.1;
  added the `trust-config.json` evidence fixture to Task 1.2; added the blocked-environment
  escalation path to Task 2.2. No implementation performed.
- 2026-08-10 — Phase 1 (Tasks 1.1, 1.2) implemented in `872dc32`; see
  `specs/codex-support-phase-1/SUMMARY.md` for its record and negative scope.
- 2026-08-10 — This file was `PLAN.md` and carried all 12 tasks and 14 Success Criteria. Review of
  the Phase-1 diff found the SUMMARY had never been updated, and the cause was structural: a single
  plan whose SC contract spans four independently-shippable phases cannot keep an honest mid-flight
  record, because `commit-quality-gate.sh` Check 1.6 blocks every `specs/<slug>/` commit until the
  SUMMARY's Verify rows cover **all** SC ids. Split into four phase slugs, each with its own SC
  table numbered from SC-1; this file became the roadmap. Task and constraint text was carried over
  verbatim except where a phase-specific correction is recorded in that phase's Status Log.
