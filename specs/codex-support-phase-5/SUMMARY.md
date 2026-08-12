# codex-support-phase-5 — Summary

Lane: high-risk
Confidence: high
Reason: Adds a second-runtime package/install boundary, outside-hook trust diagnosis, runtime state,
and workflow/CI contracts across high-blast scripts and shared instruction surfaces.
Flags: external-provider, public-contract, audit/security, high-blast, workflow-engine
Affects: codex-capability-evidence, codex-adapter-rendering, codex-adapter-installation,
codex-runtime-diagnosis, agent-runtime-bindings, runtime-neutral-sources, codex-advisory-alpha
Input-type: harness improvement

### Intent

> branch da dc merge vao simplify, hay chuan bi cho phase 5

> newbranch va commit plan cho phase 5 truoc

> claude da review + fix plan, hay bat dau implement plan di

> claudecode da review + minor fix, gio hay tiep tuc cho 5.6

## What changed

- Captured sanitized, version/platform-pinned runtime evidence and selected the hybrid
  plugin-plus-project packaging path only after skill, hook, and agent execution were observed.
- Added deterministic Codex plugin/project rendering, strict agent capability bindings, and a
  non-clobber installer with update, conflict-sidecar, removal, and rollback behavior.
- Added an outside-hook doctor, sanitized local `enforced|advisory|unsupported` mode records, and
  optional run/SUMMARY metadata with fingerprint invalidation.
- Removed all Phase-5-owned runtime-entry prose exceptions behind one checked Claude/Codex binding.
- Added one composed advisory-alpha contract, registered it in the manifest and macOS/Linux CI, and
  documented lifecycle, trust review, mode semantics, and the unobserved Linux/WSL boundary.

### Rationale

An installable alpha needs one executable release boundary, not a collection of locally passing
components. The composed contract deliberately separates deterministic cross-platform compatibility
from observed runtime truth: CI can prevent adapter drift on macOS/Linux, while the doctor refuses to
inherit macOS enforcement evidence on Linux or WSL.

### Alternatives considered

- **Call the alpha peer enforcement after macOS evidence passed** — rejected; Linux/WSL runtime
  execution, persistent user trust, and per-change parity provenance remain unobserved.
- **Run paid/model-backed probes in every PR** — rejected; deterministic CI must not require an
  account, network, real user configuration, or unbounded model spend.
- **Add a nominal WSL job without a real disposable WSL environment** — rejected; a Linux runner
  relabeled WSL would manufacture provenance. WSL stays explicit unknown/advisory.

### Deviations

- Rule 1 — Extended `docs/codex-alpha-install.md`, which Task 5.6's Action requires for trust review
  and mode semantics but its file list omitted. Keeping lifecycle guidance in the existing install
  authority avoids duplicating operational instructions across root overview documents.
- Rule 2 — Task 5.6 registered `scripts/test_render_runtime_entry.py` directly in
  `scripts/run-tests.sh`. Task 5.5's shell contract already invoked it, but direct registration keeps
  the Python inventory complete and prevents a future shell refactor from silently dropping it.
- Plan deviation — `harness-manifest.json` ended up in both Task 5.3 and Task 5.4 file sets, a
  paper violation of the same-wave zero-overlap invariant. The wave executed sequentially with a
  review between tasks, so no parallel conflict occurred; recorded so the relaxation is explicit
  rather than silent.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Alpha evidence | `bash tests/scripts/codex-alpha-evidence.test.sh` | 0 | observed hybrid runtime proof; direct fallback remains unknown/unselectable | SC-1 |
| Deterministic rendering | `python3 -m pytest scripts/test_render_codex_adapter.py -q` | 0 | byte stability, strict schema, total capability mapping, Claude preservation | SC-2 |
| Non-clobber lifecycle | `bash tests/scripts/codex-install.test.sh` | 0 | fresh/reinstall/update/conflict/dry-run/removal/rollback canaries | SC-3 |
| Outside-hook diagnosis | `python3 -m pytest scripts/test_codex_harness_doctor.py -q` | 0 | mode, trust, platform, hash, discovery, privacy, and freshness fixtures | SC-4 |
| Runtime-mode metadata | `python3 -m pytest runtime/test_runtime_mode.py runtime/test_run_state.py scripts/test_verify_summary.py -q` | 0 | sanitized state plus legacy-compatible run/SUMMARY metadata | SC-5 |
| Runtime-entry binding | `bash tests/scripts/runtime-entry-bindings.test.sh` | 0 | paired Claude/Codex syntax and zero unowned entry exceptions | SC-6 |
| Advisory-alpha composition | `bash tests/scripts/codex-alpha-contract.test.sh` | 0 | all Phase-5 surfaces, macOS/Linux CI gate, explicit WSL advisory boundary, Claude regressions | SC-7 |
| Manifest registration | `python3 scripts/check_manifest.py` | 0 | adapter, install, diagnosis, binding, and alpha consumers resolve on disk | SC-8 |

The CI-equivalent `bash scripts/run-tests.sh` completed `ALL GREEN` before Task 5.6 with 552 Python
tests and after Task 5.6 with 559 Python tests plus all shell contracts. The full suite is recorded
in prose rather than represented as a sub-60-second Verify row.

### Not auto-verified

- **Linux and WSL real Codex runtime execution remain unobserved (traceability).** CI executes the
  deterministic contract on Linux; it does not turn a GitHub Linux runner into WSL or reproduce a
  trusted end-user Codex session. The doctor forces both platform ids to advisory.
- **Persistent user trust behavior is not model-probed (provenance).** The live probe used a
  disclosed automation-vetted hook-trust bypass in disposable state. The installer preserves trust,
  and the doctor consumes its effective value, but no real user's decision was mutated or observed.
- **Direct packaging remains unknown and unselectable (provenance).** Hybrid runtime execution was
  observed; direct discovery/runtime execution was not needed and therefore was not promoted.
- **Codex MCP scoping semantics are documentation-tier (traceability).** The rendered
  `mcp_servers = {}` isolation and context7-only enablement follow official configuration
  documentation; the live probe did not exercise MCP inheritance, so per-agent MCP confinement is
  not observed runtime behavior.
- **The doctor's default acquisition path is non-hermetic (traceability).** Without
  `--doctor-report`, it invokes the real read-only `codex doctor --json` against the user's
  effective Codex state; deterministic fixtures prove parsing and mode logic, not that live
  invocation.
- **Native Windows, ChatGPT desktop UI, and networked marketplace publication are unobserved
  (traceability).** They are outside Phase 5 and no support claim is made.
- **Behavioral/parity enforcement and review-receipt provenance are not part of the alpha
  (traceability).** Phase 6+ owns those gates; a local `enforced` doctor result is not peer-runtime
  parity or GA status.
- **The final context-propagation, correctness, and intent review chains are pending
  (traceability).** Deterministic implementation is complete, but the roadmap remains review-pending
  until their receipts are recorded.

### Rollback

- For an installed consumer, first run
  `bash scripts/install-codex-harness.sh --source . --directory "${PROJECT_DIR:?set PROJECT_DIR}" --remove --yes`
  to unregister only manifest-owned Codex state while preserving user configuration.
- Revert the Phase-5 implementation commits with
  `git revert --no-commit a54f5d5..HEAD` and then
  `git commit -m "revert: remove Codex advisory alpha"`.
- Re-run `bash scripts/deploy-harness.sh "${CLAUDE_TARGET:?set CLAUDE_TARGET}"` only for Claude
  consumers that were re-synced from this branch; Phase 5 did not change `settings.json` wiring.

### Harness-Delta

- backlog — the final review chain requires agent/session receipts that deterministic CI cannot
  produce. Keep Phase 5 review-pending until context-propagation, correctness, and intent reviews are
  recorded; do not encode a fabricated receipt into the release contract.
