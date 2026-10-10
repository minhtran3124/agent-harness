# Research Brief — gh-268-codex-agent-profile-paths

Depth: **Deep** (intake lane `high-risk`, workflow-engine delivery to isolated child contexts).
External surface: none new (no dependency or version-specific API is added; the Codex facts
reused here were read at `rust-v0.147.0` during #254). No upgrade needed.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing |
| **Why this is the lightest credible path** | `rewrite_payload_paths` + `payload_targets` (#253) already decide which bare paths a Codex install ships; applying them to the decoded `developer_instructions` of the four rendered profiles closes the `rules/…` gap, and the #255 installer tail already has the create-if-missing pattern for `agents/PROJECT.md`. |
| **Confidence** | 85% |
| **Next step** | `writing-plans` against `design.md`. |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Meta-repo: skill/hook harness with a Codex advisory-alpha adapter |
| Primary language + runtime | Bash (macOS 3.2 compatible) + Python 3 stdlib |
| Frameworks / platforms | Codex CLI 0.147.0 pinned evidence |
| Relevant packages | none |
| Detectable versions | `specs/codex-support/capability-matrix.json` `cli_version` 0.147.0 |
| Important constraints | Claude render output unchanged; derived copies only; PR targets `codex` |

## Feature Understanding and Assumptions

- **Requested feature:** #268 — rendered Codex profiles cite only paths a Codex install has.
- **What success appears to mean:** no bare payload-eligible path in rendered profile instructions; `agents/PROJECT.md` exists after a Codex install.
- **Assumptions from the request:** user chose "Codex installer creates it".
- **Assumptions still needing confirmation:** none.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/render_agent_definitions.py:299-335` `render_codex`: `instructions = _codex_policy(…) + "\n\n" + body`, emitted via `_toml_string` = `json.dumps(…, ensure_ascii=False)`; validated by `parse_codex_profile`. |
| `Local` | `render_codex_adapter.py:467` is the only deploy-path caller; `payload_targets` (43 targets) includes all `rules/*.md`, no `agents/*`. |
| `Local` | A simulated rewrite of the decoded instructions changes `coding.toml` (2: `rules/auto-correct-scope.md`, `rules/orchestration.md`), `reviewer.toml` (1: `rules/behavior.md`), and nothing else (spec review, 2026-10-09). |
| `Local` | The doctor compares agent TOML hashes only against the deployment manifest written from the same render; `AGENT_DISCOVERY_MISMATCH` compares names only. Tests compare two renders, not raw `render_codex` output. |
| `Local` | Claude consumers keep `agents/PROJECT.md` at `.claude/agents/PROJECT.md` (`deploy-harness.sh` `BOOTSTRAP_OWNED_FILES`, `OUT=.claude`). |
| `Inference` | On encoded TOML text a path after a `\n` escape is preceded by `n`, which the anchor `(?<![\w./-])` treats as a word character — so the rewrite must run on the decoded string. |

## Local Findings

- **Relevant files:** `scripts/render_codex_adapter.py`, `scripts/render_agent_definitions.py` (read-only), `agents/*.md`, `agents/PROJECT.template.md`, `scripts/install-codex-harness.sh`, `scripts/test_render_codex_adapter.py`, `tests/scripts/codex-install-next-step.test.sh`, `docs/codex-alpha-install.md`.
- **Reusable:** `rewrite_payload_paths`, `payload_targets`, `parse_codex_profile`, the #255 installer tail and its stub-source test.
- **Missing:** the profile rewrite; the `agents/PROJECT.md` install step.

## Upstream Findings

- **Repositories inspected:** none new for this item; the #254 reading of `openai/codex` `rust-v0.147.0` (`agents_md_manager.rs`, `multi_agents/spawn.rs`) is reused for the child-context note.
- **Gaps:** whether a Codex child loads root `AGENTS.md` remains unobserved (#269 live capture).

## Docs Findings

No external surface: the change adds no dependency, integration, or version-specific API.

## Recommendation

- **Primary:** reuse existing per `design.md`.
- **Next-best alternative and why it lost:** passing a rewrite callback into `render_codex` — cleaner coupling but changes a Claude-shared function's signature; the post-render decode/re-encode keeps Claude code untouched.

## Risks, Unknowns, and Follow-Up Questions

- **Risks:** a future agent body citing a non-payload path stays bare (closure test extended to TOML catches payload-eligible ones only).
- **Follow-up questions:** none.

## Source Pack

- **Local files read:** `scripts/render_agent_definitions.py`, `scripts/render_codex_adapter.py`, `agents/coding.md`, `agents/reviewer.md`, `agents/task-reviewer.md`, `agents/test-runner.md`, `agents/PROJECT.template.md`, `scripts/deploy-harness.sh`, `scripts/install-codex-harness.sh`, `scripts/codex_harness_doctor.py`.
- **Upstream repositories or pages checked:** https://github.com/openai/codex/tree/rust-v0.147.0/codex-rs/core/src (reused from #254)
- **Official docs domains or pages checked:** - none (local-only; no external surface)

## Evidence Boundary

> Confirmed from artifacts: which paths each profile cites; payload target membership; doctor/test comparisons.
> Inferred from patterns: escape-anchor interaction (confirmed by the spec reviewer's simulation).
> Not checked: a live Codex subagent session.
