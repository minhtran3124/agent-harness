# codex-support-phase-2 — Summary

Lane: high-risk
Confidence: high
Reason: Selects the package boundary Phase 5 will implement and adds executable lifecycle probes
that mutate isolated Codex configuration/cache state.
Flags: workflow-engine, external-provider
Affects: codex-capability-evidence
Input-type: plan execution (Phase 2 of `specs/codex-support/ROADMAP.md`)

### Intent

Review the Phase-1 review/fix commit `be9bc21`, refine Phase 2 against the current Codex contract,
and begin implementation only after Phase 1 remains sound.

## What changed

Phase 1 passed focused review and the 480-test baseline with no remaining Critical or Important
finding. Phase 2 then added a disposable hybrid-versus-direct packaging probe, deterministic fake
CLI coverage, an isolated real Codex 0.147.0 capture, a packaging-decision validator, and the
selected hybrid boundary with a concrete direct-sync fallback.

The hybrid candidate owns reusable skills and hooks in a plugin while the project adapter owns
custom agents and bounded repository integration. Both HOME and CODEX_HOME are redirected to fresh,
distinct temporary directories for every CLI call. The committed evidence contains no user paths,
auth, transcripts, model calls, or unrelated configuration. Direct sync remains an owned `unknown`,
not a fabricated passing comparison: Phase 5 must observe Codex discovery and the real conflict
installer before it can be selected.

## Review-driven refinements

- `codex --strict-config plugin ...` is rejected by CLI 0.147.0 even though strict config is a
  top-level flag. The probe now measures strict parsing separately by rejecting an unknown key and
  parsing an empty valid config through to the expected non-terminal boundary, then uses supported
  plugin commands.
- `marketplace upgrade` is Git-only. The offline local probe exercises source refresh through
  plugin/marketplace remove and re-add instead of inventing a local upgrade protocol.
- CLI 0.147.0 caches a local plugin under manifest version `0.0.1`, while current builder docs say
  the segment is `local`. The probe discovers exactly one installed version directory.
- CLI lifecycle and cached-file visibility do not prove runtime execution. The evidence and checker
  require `runtime_execution_observed: false`; Phase 5 must prove skill invocation and hook trust.
- Hybrid failure is publishable as an owned `unknown`; the checker requires only the selected
  candidate to pass. A synthetic unit case proves that a failed hybrid can select a proven direct
  fallback, while the current unproved direct candidate cannot be selected.
- Reinstall idempotence compares the unique cache version and a deterministic content fingerprint
  before and after the second add. Fault injection proves a mutation turns the hybrid result unknown.

## Decision

Select **hybrid** for Phase 5. If a disposable Phase-5 runtime probe cannot both invoke installed
plugin skills and trust/execute installed plugin hooks without mutating unrelated user state, run
the direct-adapter proof and select direct only if that candidate passes. Otherwise Phase 5 stays
blocked. The stale Claude `.claude-plugin` branch was not reused.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Packaging lifecycle contract | `bash tests/scripts/codex-packaging-probe.test.sh` | 0 | 17 fake-CLI isolation, strict-parse, protocol, privacy, fallback-publication, and reinstall-fingerprint cases | SC-1 |
| Packaging decision evidence | `python3 scripts/check_codex_packaging.py specs/codex-support/packaging-decision.md` | 0 | selected evidence, matrix agreement, fallback, ownership, and unresolved gaps | SC-2 |

The 11-case packaging checker unit suite is part of `scripts/run-tests.sh`; it is intentionally not
a Verify row because the repository test runner owns interpreter/pytest resolution. The final
CI-equivalent run completed `ALL GREEN` with 491 Python tests. Full-suite evidence stays in prose
rather than a Verify row because it exceeds the strict per-row time budget.

## Not auto-verified

- Plugin skill invocation, hook execution/trust, and project-agent dispatch require a disposable
  model-backed Phase-5 probe and remain explicitly unobserved.
- Direct project discovery and real direct-sync update/conflict/removal behavior remain unobserved;
  `packaging-direct.json` records their Phase-5 owner and exit condition.
- The ChatGPT desktop plugin UI and networked Git marketplace upgrade are outside the local,
  no-network probe boundary.
- Linux and WSL packaging lifecycle remain unobserved; the committed capture is macOS arm64.

## Rollback

Remove the Phase-2 probe/checker, fixtures, decision, and packaging evidence; then restore the
`packaging.plugins` matrix row to its Phase-1 CLI-surface evidence. No production plugin or project
adapter was installed, so rollback has no user-state cleanup step.

### Harness-Delta

- backlog — the official builder documentation and CLI 0.147.0 disagree on the cache version
  segment for local plugins (`local` versus the manifest version). Keep probes version-tolerant and
  re-check this behavior when upgrading Codex.
