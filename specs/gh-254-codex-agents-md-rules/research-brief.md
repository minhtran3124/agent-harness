# Research Brief — gh-254-codex-agents-md-rules

Depth: **Deep** (intake lane `high-risk`, workflow-engine signal). No upgrade needed. One finding
(Codex truncates mid-file, below) adds a deploy warning to the design; it does not change depth.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing |
| **Why this is the lightest credible path** | The managed-block lifecycle (insert / hash-gated replace / sidecar / remove), the retired-file prune, the payload path rewrite from #253, and the frontmatter tier test all exist. This item swaps the hard-coded one-line block for a rendered one and adds two warnings. |
| **Confidence** | 85% |
| **Next step** | `writing-plans` against `design.md` plus the truncation warning recorded here. |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Meta-repo: skill/hook harness for Claude Code with a Codex advisory-alpha adapter |
| Primary language + runtime | Bash (macOS 3.2 compatible) + Python 3 stdlib |
| Frameworks / platforms | Claude Code (AGENTS.md support from v2.1.277); Codex CLI 0.147.0 (pinned evidence, macOS arm64) |
| Relevant packages | none (stdlib only) |
| Detectable versions | Codex `rust-v0.147.0` tag; `specs/codex-support/evidence/codex-0.147.0/` |
| Important constraints | `CLAUDE.md` Gotchas (run `scripts/run-tests.sh` before `scripts/` edits); Claude install output byte-identical; root `AGENTS.md` user-owned (`specs/codex-support/design.md` D6); PR targets `codex` |

## Feature Understanding and Assumptions

- **Requested feature:** #254 — the five always-on rules reach a Codex session through a runtime-neutral managed `AGENTS.md` section.
- **What success appears to mean:** after a Codex install, the root `AGENTS.md` contains the five rules' text inside the markers, under budget; tests pin the inventory and size; docs explain the `AGENTS.md`/`CLAUDE.md` interplay.
- **Assumptions from the request:** inline rendered delivery (user-selected); builds on #253's payload.
- **Assumptions still needing confirmation:** none that change the recommendation.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | Block is a hard-coded string, `scripts/deploy-codex-adapter.sh:140-146`; insert/replace/sidecar/remove at `:260-313`; retired-file prune keeps edited files (`:253-258`). |
| `Local` | `sync_project install "$WORK/rendered/project"` at `:441`; a non-zero sync triggers `restore_previous_market` — so the block file must be read and validated before the first write inside `sync_project`. |
| `Local` | `render()` copies `adapters/codex/project/harness-instructions.md` to `project/.codex/harness-instructions.md` (`scripts/render_codex_adapter.py:356-358`); payload rules are already rewritten (`:366-367`). |
| `Local` | Tier test `has_paths_frontmatter`, `tests/scripts/rule-loading-tiers.test.sh:4-11`; five always-on rules = 13,980 bytes. |
| `Local` | The doctor does not read `AGENTS.md` (`grep -n "AGENTS\|agents_block" scripts/codex_harness_doctor.py` → only the manifest fixture key in its test). |
| `Upstream` | Codex 0.147.0 `codex-rs/core/src/agents_md.rs:105-141`: files are read root → cwd; when a file exceeds the remaining budget it is **truncated at the byte** (`data.truncate(remaining)`) with only a `tracing::warn`. Default budget `DEFAULT_PROJECT_DOC_MAX_BYTES` = 32 KiB (`core/src/config/mod.rs:211`). |
| `Upstream` | Same file `:231-245`: per directory the first existing of `AGENTS.override.md`, `AGENTS.md`, fallbacks wins — a root `AGENTS.override.md` hides `AGENTS.md` entirely. |
| `Docs` | Claude Code memory docs: `AGENTS.md` read only when no `CLAUDE.md`/`.claude/CLAUDE.md`/`CLAUDE.local.md` at or above cwd (default `claude-md-or-agents-md`); `claude-md-and-agents-md` loads both and skips an `AGENTS.md` already imported; `@path` imports expanded; requires v2.1.277+; setting lives under `pluginConfigs` `cc-plugin-agents-md@builtin` in user/managed settings only. |
| `Inference` | The block is appended at the **end** of root `AGENTS.md`. If user prose + block > 32 KiB, Codex truncates the tail — the rules — silently. Deploy should warn when the resulting root `AGENTS.md` exceeds 32 KiB. |

## Local Findings

- **Relevant files:** `scripts/render_codex_adapter.py`, `scripts/deploy-codex-adapter.sh`, `adapters/codex/project/harness-instructions.md`, `scripts/test_render_codex_adapter.py`, `tests/scripts/codex-install.test.sh` (+ `tests/scripts/fixtures` custom AGENTS.md), `tests/scripts/rule-loading-tiers.test.sh`, `docs/codex-alpha-install.md`.
- **Existing abstractions:** `AdapterError` fail-closed render; `_rewrite_markdown` payload rewrite; marker/hash lifecycle; `old.get("agents_block_hash")` upgrade path.
- **Conventions worth preserving:** fail closed in render, non-fatal warnings in deploy; tests use a fake `codex` binary; Verify rows pipe-free and < 60 s.
- **What can be reused:** everything above; the upgrade from the one-line block is the existing hash-matches-old replace.
- **What appears missing:** a block renderer; an `AGENTS.override.md` warning; a size warning.

## Upstream Findings

- **Repositories inspected:** `openai/codex` at tag `rust-v0.147.0` (`codex-rs/core/src/agents_md.rs`, `core/src/config/mod.rs`).
- **Pattern present upstream:** byte budget across the root→cwd chain; no include mechanism.
- **Worth modeling:** budget arithmetic in UTF-8 bytes (Codex counts raw bytes).
- **Match to this repo:** direct — the budget is the constraint the design's 20 KiB cap serves.
- **Gaps:** behaviour observed in source, not by running 0.147.0 (no `codex` binary on this Linux host).

## Docs Findings

- **Official sources checked:** Codex AGENTS.md guide; Claude Code memory docs (`#agents-md`).
- **Version-matched vs latest-stable:** Codex source is version-matched (0.147.0 tag); Codex guide and Claude docs are latest.
- **Built-in capabilities:** Claude's `@AGENTS.md` bridge and `claude-md-and-agents-md` setting.
- **Caveats:** Claude subagents that skip project instructions skip `AGENTS.md` too — the harness already injects rule paths into dispatch prompts, so unaffected. `CLAUDE.local.md` also suppresses `AGENTS.md` under the default setting — document.

## Recommendation

- **Primary recommendation:** reuse existing, per `design.md`, plus a non-fatal deploy warning when root `AGENTS.md` exceeds 32 KiB after the write.
- **Why lightest:** no new lifecycle; two renderer functions and one deploy argument.
- **Why the next-best alternative lost:** a mandatory-read list (user rejected: delivery depends on model compliance); a SessionStart hook (trust unknown, #255).
- **What would change it:** a Codex release adding include/import support, or a plugin-level instructions field.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** block placement at end of file means user prose consumes budget first (mitigated by the warning); non-ASCII rule text and locale-dependent `read_text()` in deploy (design mandates UTF-8).
- **Evidence gaps:** truncation behaviour seen in source, not observed by a run; user `project_doc_max_bytes` overrides not read (warning assumes the 32 KiB default and says so).
- **Version uncertainties:** later Codex versions may change the budget; the pin stays 0.147.0.
- **Follow-up questions for the user:** none.

## Source Pack

- **Local files read:** `scripts/deploy-codex-adapter.sh`, `scripts/render_codex_adapter.py`, `adapters/codex/project/harness-instructions.md`, `rules/*.md`, `tests/scripts/rule-loading-tiers.test.sh`, `tests/scripts/codex-install.test.sh`, `scripts/test_codex_harness_doctor.py`, `docs/codex-alpha-install.md`, `specs/codex-support/design.md`, `AGENTS.md`, `CLAUDE.md`.
- **Upstream repositories or pages checked:** https://github.com/openai/codex/blob/rust-v0.147.0/codex-rs/core/src/agents_md.rs ; https://github.com/openai/codex/blob/rust-v0.147.0/codex-rs/core/src/config/mod.rs
- **Official docs domains or pages checked:** https://learn.chatgpt.com/docs/agent-configuration/agents-md ; https://code.claude.com/docs/en/memory

## Evidence Boundary

> Confirmed from artifacts: block location and lifecycle in deploy; render copy of harness-instructions; tier test; rule byte sizes; Codex 0.147.0 budget/truncation/override logic in source; Claude AGENTS.md precedence in docs.
> Inferred from patterns: silent rule truncation when root `AGENTS.md` > 32 KiB.
> Not checked: a live Codex 0.147.0 session loading the rendered block (no `codex` binary on this host; pinned evidence is macOS arm64).
