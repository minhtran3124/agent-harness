# Codex Support — Phase 5 preparation research

**Research depth:** Deep
**Prepared:** 2026-08-11
**Target:** Codex CLI 0.147.0; advisory alpha, not GA

## Bottom line

Phase 5 is ready to plan but not ready to execute its live-evidence task without an explicit
model-backed probe authorization. Keep the Phase-2 **hybrid** boundary: a generated plugin owns
reusable skills and hook registration, while a project adapter owns generated Codex agent profiles,
runtime state, and a bounded non-clobber section in the user's root `AGENTS.md`. Direct project sync
remains a tested fallback candidate, not an automatic fallback.

The implementation should be one vertical alpha slice with six sequential responsibilities:

1. close the load-bearing runtime evidence gaps;
2. render a byte-stable plugin/project adapter from the shared semantic sources;
3. install and update it without clobbering user-owned Codex or repository configuration;
4. diagnose effective trust, discovery, coverage, freshness, and platform support outside hooks;
5. move the remaining runtime-entry prose exceptions behind a checked binding;
6. prove the deterministic alpha contract on macOS, Linux, and a disposable WSL environment.

## Current baseline

- `simplify` contains shipped Phases 1–4 at merge commit `a54f5d5`.
- Local Codex remains `codex-cli 0.147.0`; `hooks`, `plugins`, `multi_agent`, and `unified_exec`
  report stable.
- Phase 2 selected hybrid packaging but observed only install/cache lifecycle, not runtime skill
  invocation, hook trust/execution, or project-agent dispatch.
- Phase 3 supplies neutral agent contracts and Codex capability mappings, but Codex TOML emission is
  deliberately disabled until Phase 5.
- Phase 4 supplies one Claude/Codex hook-input normalizer and fail-closed policies. Its unified-exec
  and `UserPromptSubmit` fixtures are documentation-derived, not captured runtime provenance.
- CI currently runs Ubuntu and macOS. WSL has no committed capture or deterministic runner.

## Official runtime contract checked for this preparation

The current [OpenAI Hooks documentation](https://learn.chatgpt.com/docs/hooks) establishes that:

- Codex discovers hooks from user/project config and enabled plugins;
- matching hook sources are additive rather than precedence-replacing;
- project-local hooks require a trusted project layer;
- non-managed command hooks are trusted against their current definition hash, so a changed hook
  must be reviewed again;
- plugin-bundled hooks use the same trust-review flow.

Consequences for Phase 5:

- file presence and plugin-list output cannot prove enforcement;
- the alpha probe must observe skill invocation, hook execution, and agent dispatch;
- doctor state must include expected-vs-effective config hash and trust freshness;
- reinstall or generated-hook changes must invalidate an `enforced` diagnosis;
- a `SessionStart` hook may display the diagnosis but cannot be its source of truth.

## Obligations inherited from Phases 1–4

| Obligation | Current evidence | Phase-5 exit condition |
| --- | --- | --- |
| Unified-exec payload envelope | Feature availability observed; envelope documentation-derived | Capture a sanitized disposable live payload and bind the fixture/matrix row to it |
| `UserPromptSubmit` envelope | Documented, advisory | Capture it when the same live probe can do so safely; otherwise retain an owned advisory exception |
| Hybrid runtime execution | Plugin lifecycle/cache observed only | Invoke an installed skill, trust/execute an installed hook, and dispatch a generated project agent |
| Direct fallback | Materialized candidate only | Probe discovery plus real non-clobber update/conflict/removal before it can be selected |
| Agent profiles | Total neutral contract; Codex emission deferred | Emit strict TOML or fail on every unmapped capability/unsupported exception |
| Root instructions | `AGENTS.md` explicitly user-owned | Sentinel-managed pointer preserves outside edits and writes reviewable incoming content on conflict |
| Runtime mode | Design only | Outside-hook doctor emits `enforced`, `advisory`, or `unsupported`; unknown never becomes enforced |
| Runtime-entry prose | Thirteen count-exact owned exceptions | Central binding renders runtime-specific entry syntax; shared policy remains semantic/invocation-neutral |
| Linux/WSL | Linux and WSL matrix rows unknown | Capture Linux and WSL dependency/config results; unavailable WSL keeps alpha advisory and blocks peer claim |

## Proposed source and generated boundaries

- `adapters/codex/` owns only small runtime binding/templates: plugin manifest, hook registration,
  project instruction fragment, schemas, and adapter constants.
- `scripts/render_codex_adapter.py` reads shared `skills/`, `hooks/`, agent contracts/bindings, and
  the manifest, then writes a temporary/generated package. Generated copies are never semantic
  sources and are not committed.
- `scripts/install-codex-harness.sh` installs from that generated package and owns only paths listed
  in its deployment manifest. It never removes or rewrites unrelated `.codex/`, `AGENTS.md`, plugin,
  marketplace, or user configuration.
- `.harness-state/codex-runtime.json` is local derived state. Durable run/SUMMARY metadata records
  only the mode and sanitized evidence identifier, not private configuration.
- Claude's `.claude/` deployment path remains byte-stable and is tested as a regression boundary.

## Decisions and constraints

- Alpha may ship in `advisory` mode; it must never call advisory enforcement “peer”.
- Hybrid failure triggers the direct probe; it does not silently select direct.
- The live probe requires explicit authorization because it invokes a model and changes isolated
  Codex state. It must redirect both `HOME` and `CODEX_HOME`, publish a cleanup ledger, sanitize
  before publication, and reject any leaked path/token/transcript.
- Native Windows, ChatGPT desktop UI, networked marketplace publishing, Phase-6 review provenance,
  Phase-7 behavioural parity, and GA claims remain out of scope.
- Phase 5 implementation starts from a new isolated branch/worktree based on `simplify`.

## Recommended execution order

Run Task 5.1 first and stop if neither hybrid nor a separately proven direct candidate can execute
the required runtime surfaces. Only then generate/install the production alpha adapter. Build the
doctor before declaring the installation usable, clear the owned runtime-entry exceptions, and end
with cross-platform deterministic evidence plus a human review of the alpha claim boundaries.
