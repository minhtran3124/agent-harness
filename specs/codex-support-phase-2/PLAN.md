---
slug: codex-support-phase-2
status: proposed
owner: Minh Tran
created: 2026-08-10
---

# Codex Support — Phase 2: Evidence-driven packaging decision

<!-- AT-A-GLANCE:BEGIN (generated — do not edit; refreshed by render_plan.py --summarize) -->
## At a glance

**2 tasks · 2 waves · 11 files · 0/2 done**

| Wave | Task | Title | Files | Done (acceptance) |
|---|---|---|---|---|
| 1 | 2.1 | Build a disposable hybrid-versus-direct probe (wave 1) | scripts/probe_codex_packaging.sh, tests/scripts/codex-packaging-probe.test.sh, tests/fixtures/codex-packaging/marketplace.json, tests/fixtures/codex-packaging/plugin.json, tests/fixtures/codex-packaging/agents.toml, specs/codex-support/capability-matrix.json | one safe command compares both package boundaries across discovery and lifecycle… |
| 2 | 2.2 | Record and enforce the packaging decision (wave 2) | specs/codex-support/packaging-decision.md, specs/codex-support/evidence/codex-0.147.0/packaging-hybrid.json, specs/codex-support/evidence/codex-0.147.0/packaging-direct.json, scripts/check_codex_packaging.py, scripts/test_check_codex_packaging.py, specs/codex-support/capability-matrix.json | Phase 5 has one evidence-backed package boundary and a deterministic reason to s… |

```mermaid
flowchart LR
  subgraph W0[Wave 1]
    T2_1["2.1 Build a disposable hybrid-versus-direct probe (wave 1)"]
  end
  subgraph W1[Wave 2]
    T2_2["2.2 Record and enforce the packaging decision (wave 2)"]
  end
  W0 --> W1
```

### Progress
- [ ] 2.1 — Build a disposable hybrid-versus-direct probe (wave 1)
- [ ] 2.2 — Record and enforce the packaging decision (wave 2)
<!-- AT-A-GLANCE:END -->

## 1. Motivation

Phase 5 needs exactly one package boundary for the Codex adapter, chosen on executable evidence
rather than on the plugin documentation's recommendation. Phase 2 builds a disposable probe that
compares the hybrid and direct candidates across discovery and lifecycle, then records the decision
with a deterministic fallback trigger.

Parent roadmap: `specs/codex-support/ROADMAP.md`. Depends on Phase 1's capability matrix.

## 2. Non-goals

- Emitting or installing the production Codex alpha adapter from Phase 5.
- Adding production `.codex-plugin/`, `.codex/`, or root instruction files.
- Cherry-picking the stale Claude-only `feature/plugin-namespace-packaging` branch.
- Running paid/networked Codex probes as blocking per-PR CI.

## Global Constraints

- Execute in an isolated worktree/branch; preserve all unrelated and untracked user files.
- Run `bash scripts/run-tests.sh` before the first `hooks/` or `scripts/` implementation edit and
  once after all tasks. Record full-suite evidence in the Status Log/SUMMARY prose, never as a
  sub-60-second Verify row.
- Deterministic tests require no Codex authentication, network, or mutation of a developer's real
  Codex configuration. Live plugin probes run only in a disposable OS account/runner and clean up
  the exact resources they create.
- Never log credentials, tokens, full transcripts, user home paths, repository absolute paths, or
  unrelated Codex configuration. Fixtures are schema-minimal and sanitized before commit.
- Root `AGENTS.md`, production `.codex/`, `settings.json`, and the Phase-5 installer surface are
  outside this plan and must remain byte-identical.
- Keep Bash compatible with macOS Bash 3.2; prefer Python stdlib for structured parsing; all focused
  checks below are pipe-free and complete in under 60 seconds.

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
| --- | --- | --- | --- |
| SC-1 | The packaging probe exercises hybrid and direct candidates through discovery, install, upgrade, conflict, and removal paths without touching the caller's Codex state | `bash tests/scripts/codex-packaging-probe.test.sh` | exit 0 |
| SC-2 | One packaging decision names the selected path, executable evidence, fallback trigger, ownership boundary, and unresolved gaps | `python3 scripts/check_codex_packaging.py specs/codex-support/packaging-decision.md` | exit 0 |

> SC ids are per-plan (`rules/plan-format.md`). The roadmap's original global numbering maps as
> SC-4→SC-1 and SC-5→SC-2.

## 4. Tasks

### Task 2.1 — Build a disposable hybrid-versus-direct probe (wave 1)

- **Files:** scripts/probe_codex_packaging.sh, tests/scripts/codex-packaging-probe.test.sh, tests/fixtures/codex-packaging/marketplace.json, tests/fixtures/codex-packaging/plugin.json, tests/fixtures/codex-packaging/agents.toml, specs/codex-support/capability-matrix.json
- **Action:** Test-first, implement a probe that materializes two temporary candidates from current
  sources: hybrid (plugin-owned skills/hooks plus project-owned agents/instruction pointer) and
  direct project sync. Exercise strict config parsing, marketplace/plugin discovery, install/list,
  skill discovery, hook registration visibility, agent discovery, no-op reinstall, source update,
  local customization conflict, removal, and cleanup. Deterministic tests use a fake Codex CLI and
  assert the exact CLI/config protocol. A real run is permitted only in a disposable OS
  account/ephemeral runner and must prove it is not pointing at the caller's Codex state before any
  mutation. Do not add production `.codex-plugin/`, `.codex/`, or root instruction files.
- **Verify:** `bash tests/scripts/codex-packaging-probe.test.sh`
- **Done:** one safe command compares both package boundaries across discovery and lifecycle
  behavior, emits machine-readable results, and leaves neither project nor Codex user state behind.
- **Criteria:** SC-1
- **Interfaces:** Consumes: current skills and hooks trees, neutral package assumptions, Codex plugin CLI. Produces: `scripts/probe_codex_packaging.sh`, packaging fixture contracts, probe result schema used by Task 2.2.

### Task 2.2 — Record and enforce the packaging decision (wave 2)

- **Files:** specs/codex-support/packaging-decision.md, specs/codex-support/evidence/codex-0.147.0/packaging-hybrid.json, specs/codex-support/evidence/codex-0.147.0/packaging-direct.json, scripts/check_codex_packaging.py, scripts/test_check_codex_packaging.py, specs/codex-support/capability-matrix.json
- **Action:** Run the real probe in an approved disposable environment and save sanitized results
  for both candidates. Write the decision with selected path, plugin/project ownership, discovery
  evidence, reinstall/upgrade/conflict behavior, trust implications, unresolved gaps, exact fallback
  trigger, and a statement that the stale `.claude-plugin` branch was inspected but not reused. Add
  a stdlib checker that rejects missing evidence, a decision unsupported by its result, an absent
  fallback criterion, or claims broader than the capability matrix. Select hybrid only if every
  required discovery/lifecycle case passes; otherwise select direct sync without changing the
  semantic-core contracts. If no approved disposable environment is available, do not run the probe
  against real Codex state and do not fabricate evidence: record a
  `specs/codex-support-phase-2/ESCALATIONS.md` block (`decision: pending`) for environment
  provisioning and leave the packaging decision unwritten — Phase 5 stays blocked rather than
  silently defaulting to either candidate. New packaging fixtures carry a `capture` label from the
  closed vocabulary established in Phase 1.
- **Verify:** `python3 -m pytest scripts/test_check_codex_packaging.py -q && python3 scripts/check_codex_packaging.py specs/codex-support/packaging-decision.md`
- **Done:** Phase 5 has one evidence-backed package boundary and a deterministic reason to switch to
  the fallback; the matrix and decision agree on every unresolved capability.
- **Criteria:** SC-2
- **Interfaces:** Consumes: Task 2.1 result schema and live probe output. Produces: `specs/codex-support/packaging-decision.md`, packaging evidence JSON, `scripts/check_codex_packaging.py`.

## 5. Risks

- **The packaging spike accidentally becomes an unsupported production adapter.** Mitigation: only
  temporary generated candidates and evidence are committed; production plugin/project files remain
  Phase 5.
- **Live probes mutate real Codex state or incur unplanned model cost.** Mitigation: disposable
  account/runner precondition, fake CLI tests, exact cleanup ledger, and no blocking live CI.
- **No approved disposable environment exists when the phase runs.** Mitigation: the explicit
  escalation path in Task 2.2 — Phase 5 blocks rather than defaulting to a candidate.

## 6. Status Log

- 2026-08-10 — Split out of the single four-phase `specs/codex-support/` plan; not started.
