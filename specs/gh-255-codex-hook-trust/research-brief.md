# Research Brief — gh-255-codex-hook-trust

Depth: **Deep** (intake lane `high-risk`; the installer and doctor decide the enforcement claim).
External surface: yes (Codex CLI version-specific behaviour), so upstream source was read at two
version tags. No upgrade needed.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing |
| **Why this is the lightest credible path** | The doctor already has the advisory/unsupported split, a free-form `diagnostic_summary`, `--no-persist`, and `--codex-bin/--codex-home`; the Claude installer already calls `init-structure.sh`; the install tests already run a fake Codex. #255 adds one reason, one installer tail, a matrix text update, and docs. |
| **Confidence** | 85% |
| **Next step** | `writing-plans` against the approved `design.md`. |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Meta-repo: skill/hook harness for Claude Code with a Codex advisory-alpha adapter |
| Primary language + runtime | Bash (macOS 3.2 compatible) + Python 3 stdlib |
| Frameworks / platforms | Codex CLI 0.147.0 pinned evidence (macOS arm64); latest stable 0.162.0 (2026-10-08) |
| Relevant packages | none (stdlib only) |
| Detectable versions | `specs/codex-support/capability-matrix.json` `cli_version` 0.147.0 |
| Important constraints | `CLAUDE.md` runtime support boundary ("Treat an `enforced` claim today as a bug"; "the adapter never edits trust choices"); `check_codex_capabilities.py` closed capture vocabulary; PR targets `codex` |

## Feature Understanding and Assumptions

- **Requested feature:** #255 — hook trust visible and actionable; installer next step; named doctor reason for a missing hook helper; trust evidence; docs; `init-structure.sh` in the installer.
- **What success appears to mean:** after install, the user reads the doctor mode and exactly what to do to trust the hooks; a missing helper is named; nothing edits trust.
- **Assumptions from the request:** user-approved — visibility now, `hooks/list` later; missing helper = advisory.
- **Assumptions still needing confirmation:** none.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Upstream` | `codex doctor --json` has no hook-trust field at `rust-v0.162.0` (`codex-rs/cli/src/doctor.rs`: only a "startup warning hooks" count and a `[features].codex_hooks` deprecation note; `doctor/security.rs` is endpoint-security software). 0.147.0 pinned evidence `doctor.json` has none either. |
| `Upstream` | App-server `hooks/list`: `HooksListParams { cwds }`, `HooksListResponse`, `HookMetadata { …, pluginId, enabled, isManaged, currentHash, trustStatus }`, `HookTrustStatus = "managed" \| "untrusted" \| "trusted" \| "modified"` — present at both `rust-v0.147.0` and `rust-v0.162.0` (`codex-rs/app-server-protocol/schema/…/v2/`). No CLI subcommand exposes it (`codex-rs/cli/src/` has no hooks command at 0.162.0). |
| `Upstream` | 0.147.0 TUI: `startup_hooks_review` prompt — "Hooks need review / N hooks are new or changed. / Hooks can run outside the sandbox after you trust them. / 1. Review hooks 2. Trust all and continue 3. Continue without trusting (hooks won't run)"; `/hooks` ("view and manage lifecycle hooks") browser — "Trust: New hook - review required … Press t to trust" (`codex-rs/tui/src/snapshots/…startup_hooks_review_prompt.snap`, `…hooks_browser_untrusted_enabled_handler.snap`, `slash_command.rs:104`). |
| `Local` | Doctor reason split `scripts/codex_harness_doctor.py:446-491`; `TRUST_UNKNOWN`/`HOOKS_UNTRUSTED` from `_doctor_reasons`; `diagnostic_summary` str→str in `runtime_mode.make_record` (`runtime/runtime_mode.py:126-161`); reason codes must match `^[A-Z][A-Z0-9_]*$`. |
| `Local` | Hook helper candidates: `hooks/commit-gate.sh:168`, `hooks/session-knowledge.sh:122-124`; `session-knowledge.sh:95` probes `runtime/run_state.py` at the root only. |
| `Local` | `check_codex_capabilities.py:59-74, 237, 281, 355-370`: closed `ALLOWED_CAPTURES`; fixtures must be `observed`; `official-documentation` only on OpenAI docs hosts; `unknown` evidence requires `source.kind: unavailable` and `evidence_path: null`. |
| `Local` | `install-harness.sh:239-246` runs `init-structure.sh --root "$TARGET_DIR"`; `init-structure.sh` is create-if-missing and exits 0. |
| `Local` | Codex installer deletes its temporary clone on exit (`install-codex-harness.sh:44-45`); the payload does not include the doctor (`deploy-harness.sh` `CONSUMER_SCRIPTS`). |
| `Inference` | `trustStatus: trusted` is approval of an exact hook hash, not an observed hook run; per `CLAUDE.md` it cannot alone unlock `enforced`. A live capture is needed before the follow-up may change the mode. |

## Local Findings

- **Relevant files:** `scripts/install-codex-harness.sh`, `scripts/codex_harness_doctor.py`, `scripts/test_codex_harness_doctor.py`, `tests/scripts/codex-install.test.sh`, `specs/codex-support/capability-matrix.json`, `docs/codex-alpha-install.md`, `scripts/init-structure.sh`.
- **Extension points:** `diagnose()` reason lists; `_install_reasons`; `diagnostic_summary`; the installer tail after the `.gitignore` step.
- **Conventions:** non-fatal installer tail; fail-closed doctor input errors (exit 2); tests via the fake Codex.
- **Reusable:** all of the above; the existing `installed_project()` fixture.
- **Missing:** a named hook-dependency reason; installer next step; docs for the untrusted state.

## Upstream Findings

- **Repositories inspected:** `openai/codex` at `rust-v0.147.0` and `rust-v0.162.0`.
- **Capability present upstream:** per-hook trust via app-server `hooks/list`; not in `doctor --json`.
- **Worth modeling (follow-up):** a JSON-RPC client for `codex app-server` → `hooks/list` filtered by the Agent Harness `pluginId`.
- **Gaps:** behaviour read from source and UI snapshots, not observed in a run (no `codex` on this Linux host).

## Docs Findings

- **Official sources checked:** none newer than the source tree for this surface; the Codex hooks UX is documented here from the TUI snapshots at the pinned tag.
- **Version-matched:** yes (0.147.0), plus latest stable 0.162.0.

## Recommendation

- **Primary:** reuse existing per `design.md`.
- **Why the next-best alternative lost:** wiring `hooks/list` now (user chose to defer: no live capture possible here, and trust approval is not an observed run).
- **What would change it:** a Codex release adding trust to `doctor --json`, or a live macOS capture of `hooks/list`.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** the installer's doctor call under `set -euo pipefail` (guarded); doctor output parsing.
- **Evidence gaps:** none of the Codex UX was observed live.
- **Follow-up:** a new issue to wire `hooks/list`.

## Source Pack

- **Local files read:** `scripts/install-codex-harness.sh`, `scripts/install-harness.sh`, `scripts/init-structure.sh`, `scripts/codex_harness_doctor.py`, `runtime/runtime_mode.py`, `scripts/check_codex_capabilities.py`, `specs/codex-support/capability-matrix.json`, `specs/codex-support/evidence/codex-0.147.0/{doctor,trust-config}.json`, `hooks/commit-gate.sh`, `hooks/session-knowledge.sh`, `scripts/test_codex_harness_doctor.py`, `CLAUDE.md`.
- **Upstream repositories or pages checked:** https://github.com/openai/codex/tree/rust-v0.162.0/codex-rs/cli/src (doctor.rs, doctor/security.rs) ; https://github.com/openai/codex/tree/rust-v0.147.0/codex-rs/app-server-protocol/schema (HooksListParams, HookMetadata, HookTrustStatus) and the same at rust-v0.162.0 ; https://github.com/openai/codex/tree/rust-v0.147.0/codex-rs/tui/src (startup_hooks_review, hooks_browser_view, slash_command.rs) ; `gh release list --repo openai/codex`
- **Official docs domains or pages checked:** - none found (no official page documents hook trust in `doctor --json` or `hooks/list`)

## Evidence Boundary

> Confirmed from artifacts: local doctor/installer/validator behaviour; upstream source at both tags.
> Inferred from patterns: that `trustStatus` reflects the gate Codex applies at run time.
> Not checked: any live Codex run (no binary on this host; Linux is `PLATFORM_UNVERIFIED` anyway).
