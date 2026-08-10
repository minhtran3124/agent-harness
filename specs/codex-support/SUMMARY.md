# codex-support — Summary

Lane: high-risk
Confidence: high
Reason: Adds a second agent-runtime target for the whole harness — touches the workflow engine
(skills/, agents/, rules/), every hook, the install/deploy path, and the hard-gate enforcement
surface. `workflow-engine` + `high-blast` + `external-provider` fire.
Flags: workflow-engine, high-blast, external-provider, public-contract
Affects: hook-registration, artifact-schema-plan, hard-gate-vocabulary, lane-evidence-mapping
(all four contracts gain a second consumer runtime)
Input-type: new initiative

### Intent

> make the deep research and deep review current codebase in current repo (on simplify branch)
> now i want to support for the user with codex. Let thinking and make the overral design + high
> level spec for it. need to high lvl design first, dont go too detail or implementation.

Follow-up decisions (2026-08-08):

> 1. Codex runs the agents too, not only the reviewer; it is peer to Claude Code.
> 2. Codex is a peer runtime.
> 3. Ship advisory.

Revision request (2026-08-10): update the proposal after deep review, before implementation.

## What changed

Design only — no adapter or enforcement code. Refreshed `design.md` and its Vietnamese translation
against current Codex documentation, Codex CLI 0.147.0 live probes, and the current repository
contracts. The revision keeps the shared-source architecture but replaces stale or unsafe premises
with testable contracts.

### Rationale

Codex has the necessary extension surfaces, so the architecture is implementable. It is not safe to
treat the adapter as a mechanical file-format conversion: hook payloads differ, Codex sandboxing is
not a Claude tool allowlist, root `AGENTS.md` is user-owned, and hooks cannot diagnose their own
absence. The revised design makes those boundaries explicit before implementation begins.

The main corrections are:

- replace the stale “experimental/missing apply_patch hooks” premise with an exact event/tool/
  platform capability matrix and captured fixtures;
- define a file-set hook normaliser with explicit `known|partial|unknown` gate policies;
- define runtime-neutral agent capabilities plus reviewed Claude/Codex policy bindings;
- require fresh/bounded Codex custom-agent dispatch and a strict reviewer profile;
- prefer hybrid plugin/project packaging, subject to an executable Phase-2 spike;
- preserve root `AGENTS.md` through a bounded managed section or opt-in pointer;
- add an out-of-hook runtime doctor so disabled/untrusted hooks cannot self-certify enforcement;
- retain `state-breadcrumb.sh` at `SessionEnd` unless a separate replaceable Stop-snapshot design is
  proven;
- add builder and reviewer provenance, mixed-runtime semantics, and harness-blind external review;
- put deterministic adapter checks on every PR and require behavioural parity before GA.

### Alternatives considered

- **Fork the harness per runtime** — rejected because shared workflow policy would drift.
- **Purely mechanical Markdown/TOML adapter** — rejected because model/tool/sandbox/context fields
  carry runtime-specific security policy.
- **Generate all of root `AGENTS.md`** — rejected because Codex reads the existing user-owned root
  file and this repository intentionally keeps content there that differs from `CLAUDE.md`.
- **Use SessionStart to detect advisory mode** — rejected because a disabled or untrusted hook
  cannot report its own absence.
- **Move the breadcrumb hook directly to Stop** — rejected because Stop can repeat and preserve an
  early stale snapshot under the existing idempotency model.
- **Declare peer at alpha** — rejected; D3 permits advisory alpha, while D2 requires deterministic
  and behavioural parity before the GA peer claim.

### Deviations

- The original design called adapters mechanical and placed behavioural parity after the installer.
  The revision intentionally makes policy bindings explicit and moves GA after both parity tiers.
- The original design implied generated `AGENTS.md`; the revision gives the tracked root file a
  non-clobber ownership contract.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| English/Vietnamese top-level structure | `test "$(grep -c '^## [0-9]' specs/codex-support/design.md)" -eq "$(grep -c '^## [0-9]' specs/codex-support/design.vi.md)"` | 0 | both documents contain the same 11 numbered sections | |
| Documentation truth lint | `bash scripts/lint-doc-truth.sh` | 0 | refreshed design references only supported repository paths | |
| CI-equivalent suite | `bash scripts/run-tests.sh` | 0 | shell suites and Python tests pass | |

### Not auto-verified

- Plugin versus direct packaging suitability reached **traceability** from official plugin docs;
  no Codex plugin package was built. Phase 2 is the blocking executable spike.
- Native Windows compatibility was **not verified**. The design explicitly limits the initial
  baseline to macOS/Linux/WSL until `commandWindows` or a native adapter is implemented.
- End-to-end Claude/Codex behavioural parity was **not verified** because this remains a design-only
  change. Phase 7 defines that truth-tier release gate.
- The isolated Codex probes observed shell and `apply_patch` pre/post events and fresh/bounded custom
  agent selection on CLI 0.147.0; they did **not** prove every specialised handler or hosted tool is
  covered. The runtime doctor and versioned capability matrix keep that negative scope explicit.

### Rollback

- `git revert <sha>` — documentation only; no runtime files are wired.

### Harness-Delta

- backlog — path-scoped rule loading is a pre-existing context-delivery risk independent of Codex.
  The Phase-3 explicit-read contract should be implemented and audited even if Codex support is
  later paused.
