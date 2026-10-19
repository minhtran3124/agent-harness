# model-effort-config — Research Brief

Written 2026-10-17. Pins: repo 66e6f87; Claude Code 2.1.302 (Linux, print mode `-p` for every probe)

Depth: **Deep** (intake lane `high-risk`; hard gates `high-blast` and `workflow-engine`). External
surface: yes — the design relies on version-specific Claude Code behavior (agent and skill
frontmatter, SessionStart input and output). No depth change after evidence.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Build the applier on top of existing parts (reuse `render_agent_definitions.py`, the deploy pipeline and the SessionStart hook pattern) |
| **Why this is the lightest credible path** | Claude Code already applies `model`/`effort` from agent and skill frontmatter (probed); only the merge, validation and write step is new. |
| **Confidence** | 75% — A1, A2, A3, A4, A6 and the `inherit` probe hold; A5 is false in print mode and only documented for interactive mode. |
| **Next step** | **Rule 4 STOP (design go/no-go A5):** ask the user whether a hook-written agent change taking effect from the next session in headless runs is acceptable, then `writing-plans`. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Claude Code skills framework and workflow harness (meta-repo, no application stack) |
| Primary language + runtime | Bash hooks and scripts; Python 3.12 standard library (`/usr/lib/python3.12` in probe traceback) |
| Frameworks / platforms | Claude Code 2.1.302 (`claude --version`); Codex advisory alpha adapter (out of scope, D3) |
| Relevant packages | none — the applier needs only the Python standard library |
| Detectable versions | Claude Code 2.1.302; no YAML dependency (`grep -rln "import yaml" scripts runtime hooks` empty) |
| Important constraints | `rules/behavior.md`; `CLAUDE.md` hook table and doc-truth lint; `scripts/check-hook-root-source.sh` ratchet; `docs/solutions/harness/gate-config-must-read-index.md`; `docs/solutions/harness/hook-root-must-not-come-from-install-location.md` |

---

## Feature Understanding and Assumptions

- **Requested feature:** one JSON file that sets `model`/`effort` per agent and skill, plus one command that loads it into the harness workflow (`specs/model-effort-config/intent.md`).
- **What success appears to mean:** design.md SC-1…SC-12.
- **Assumptions from the request:** settings apply at install and at a new session (`startup`, `clear`); a mid-session `/model` or `/effort` is never reverted; option A scope split.
- **Assumptions still needing confirmation:** whether the A5 result (below) is acceptable — this is a design go/no-go, not a fact.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | Probe 1 (scratch repo, `claude -p --model opus --effort high`): agent `probe-agent` with `model: haiku`, `effort: low` ran on `claude-haiku-5-5` (`modelUsage`); its subagent transcript records `"effort":"low"` ×3 while the main transcript records `"effort":"high"`. Proves **A1** and **A6** (truth, measured 2026-10-17). |
| `Local` | Probe 1 hook stdin: `{"hook_event_name":"SessionStart","source":"startup",…}`; matcher `startup\|clear` fired. Proves **A3** for `startup` (truth); `clear` not observable in `-p`. |
| `Local` | Probe 3: skill with `model: haiku`, `effort: low` invoked as `/probe-skill` ran only on `claude-haiku-5-5` (201 output tokens); transcript `"perTurnEffort":"low"`. Proves **A2** (truth). |
| `Local` | Probe 4: SessionStart hook added `model: haiku` to a skill; `/probe-skill` ran on Haiku **with and without** `reloadSkills` (212 and 217 Haiku output tokens). Skill frontmatter is read at invocation. **A4 holds**; `reloadSkills` is not required for a frontmatter-only change. |
| `Local` | Probe 7: skill `model: inherit` ran on the session model (`claude-opus-5-5` only), no error. `inherit` is valid in `SKILL.md`. |
| `Local` | Probes 5 and 9: SessionStart hook rewrote agent `model: haiku` → `sonnet`; the agent still ran on Haiku (81 Haiku output tokens, no Sonnet usage), also after a 10 s wait. Probes 6 and 8: a mid-session rewrite (with and without a 10 s wait) also ran on Haiku. **A5 is false in print mode** (truth). |
| `Docs` | code.claude.com/docs/en/sub-agents.md: "Claude Code watches `~/.claude/agents/` and `.claude/agents/`. When you add or edit a subagent file on disk … the next delegation uses the updated definition, with no restart needed." Exceptions: new `agents` directory, `--add-dir`, `--disable-slash-commands`. The watcher was not observed in `-p` (probes 6, 8, 9). |
| `Docs` | Same page: `model` accepts `sonnet`, `opus`, `haiku`, `fable`, a full ID, or `inherit`; `effort` accepts `low`…`max`, "available levels depend on the model", and overrides the session effort but not `CLAUDE_CODE_EFFORT_LEVEL`. |
| `Docs` | code.claude.com/docs/en/hooks.md: SessionStart `source` values `startup`, `resume`, `clear`, `compact`, `fork`; output accepts `reloadSkills`; no model/effort output. `PreModelSwitch` can block a switch, and its timeout blocks it. |
| `Docs` | Changelog 2.1.295: "Fixed a skill's `allowed-tools` and `effort` being dropped when the Skill tool finished before the response stream ended … in `-p` runs". Skill `effort` needs ≥ 2.1.295. 2.1.299: `/reload-skills` re-sends the skill list. |
| `Local` | `scripts/render_codex_adapter.py:47` `expected_codex_hooks()` renders every `settings.json` hook into `adapters/codex/plugin/hooks/hooks.json`; a new SessionStart hook would appear in the Codex adapter unless excluded. |
| `Local` | `scripts/run-tests.sh:191` discovers `scripts/test_*.py` by glob; `:159` runs every `tests/hooks/*.test.sh` and `tests/scripts/*.test.sh`. No list edit is needed for new tests. |
| `Local` | `tests/scripts/deploy-profile.test.sh:43-67` asserts per-profile hook sets by name; `harness-manifest.json` `hooks` and `hook_profiles` list hooks by name. |
| `Inference` | Interactive sessions probably pick up a hook-written agent change after the watcher fires (Docs), so the A5 gap likely affects headless (`-p`) runs only; not observed — no TTY driver (`tmux`, `expect`) is installed here. |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:**
  - `agents/runtime-bindings.json`
  - `scripts/render_agent_definitions.py` (`render_claude`, `CLAUDE_EFFORTS`)
  - `scripts/deploy-harness.sh`: `CONSUMER_SCRIPTS`, `render_agents`, `copy_consumer_subset`, `rewrite_derived_paths`, `derive_settings`, `prune_orphans`, `preflight_protected`
  - `scripts/install-harness.sh` (`PAYLOAD`)
  - `hooks/session-knowledge.sh`, a SessionStart pattern with `HOOK_DIR` and `REPO_ROOT` from `CLAUDE_PROJECT_DIR`
  - `harness-manifest.json` (`hooks`, `hook_profiles`, `skills`)
  - `scripts/render_codex_adapter.py`
  - `scripts/check-hook-root-source.sh`
  - Tests: `tests/hooks/session-knowledge.test.sh`, `tests/scripts/deploy-profile.test.sh`, `tests/scripts/deploy-prune.test.sh`, `tests/scripts/install-harness.test.sh`, `tests/scripts/consumer-subset.test.sh`, `scripts/test_render_agent_definitions.py`
- **Existing abstractions or extension points:**
  - `render_agent_definitions.py` already parses frontmatter and validates efforts, so `--defaults-out` fits there.
  - The `CONSUMER_SCRIPTS` allow-list ships the applier.
  - The `derive_settings` profile filter registers the hook by basename.
- **Conventions worth preserving:**
  - Two-space Bash and `set -u`.
  - Hooks exit 0 on missing `python3`.
  - The project root comes from `CLAUDE_PROJECT_DIR`, never from the hook's location; `check-hook-root-source.sh` enforces this.
  - `Verifies:` / `Does not verify:` lines on a new hook.
- **What can likely be reused:**
  - The frontmatter split in `render_agent_definitions.py` (`split_frontmatter`).
  - The test harness pattern in `tests/hooks/session-knowledge.test.sh`.
- **What appears missing locally:**
  - A skill-frontmatter writer.
  - A defaults snapshot.
  - A Codex exclusion for a Claude-only hook.

---

## Upstream Findings

- **Repositories inspected:** OpenCode docs (agent config), Codex CLI profile guides, Aider model settings, LiteLLM router config (earlier in this session; URLs in Source Pack).
- **Pattern or capability already present upstream:** per-agent `model` in JSON or frontmatter (OpenCode); named profiles and an effective-config view (Codex `/debug-config`); per-model `accepts_settings` validation (Aider).
- **Files, modules, or areas worth modeling:** OpenCode's same-values-in-JSON-or-frontmatter; Codex's provenance display for `--show`.
- **How closely the upstream pattern matches this repo:** close for the data shape; no upstream tool rewrites another tool's frontmatter, so the applier itself has no direct model.
- **Any upstream gaps or uncertainties:** the Codex sources are third-party blogs, not official docs.

---

## Docs Findings

- **Official sources checked:** code.claude.com/docs/en/sub-agents.md, skills.md, hooks.md, settings.md, model-config.md, env-vars.md, changelog.
- **Version-matched vs latest-stable status:** docs read 2026-10-17 against installed 2.1.302; the changelog view covered 2.1.293–2.1.302 only.
- **Built-in capabilities that already support the feature:** agent and skill `model`/`effort` frontmatter; SessionStart `source` matchers; agent file watcher (interactive, documented).
- **Current recommended APIs or workflows:** edit `.claude/agents/` on disk; the watcher applies it at the next delegation.
- **Important caveats, deprecations, or migration notes:**
  - `effort` levels depend on the model.
  - Skill `effort` in `-p` was dropped before 2.1.295.
  - The watcher misses a newly created `agents` directory.

---

## Recommendation

- **Primary recommendation:** build per design.md Approach 1. Use a single code path that reuses the renderer, deploy steps and hook conventions.
- **Why this is the lightest credible path:** the runtime already reads frontmatter (A1, A2, A6 measured), so no injection mechanism is needed. Skills take a hook-written change in the same session without `reloadSkills` (A4). `reloadSkills` can still be returned; it is harmless and covers a skill-list refresh.
- **Why the next-best alternative lost:** dispatch-time injection (Approach 2) would bypass the A5 gap for harness-dispatched agents only. It cannot set skill effort, and it changes every dispatching skill. It also applies file edits mid-session without a user action (D9).
- **What would change this recommendation:** if the user rejects the A5 lag for headless runs, a hybrid is possible. Dispatching skills would also pass `model`/`effort` on each Agent call, which needs a `DC<n>` against D9 and D11.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - The Codex adapter renders every `settings.json` hook (`render_codex_adapter.py:47`). Planning must exclude `model-config.sh` from Codex (D3), or accept a no-op Codex registration.
  - `tests/scripts/deploy-profile.test.sh` and `harness-manifest.json` hook lists must gain the new hook.
  - The new hook must pass `scripts/check-hook-root-source.sh`.
- **Evidence gaps:**
  - A5 in interactive mode (documented, not observed).
  - Whether `/clear` re-reads agents (undocumented, not observable in `-p`).
  - A7 timing (budget 1 s) is unmeasured until the hook exists.
- **Version uncertainties:** behavior is pinned to Claude Code 2.1.302; skill `effort` needs ≥ 2.1.295.
- **Follow-up questions for the user:**
  - **A5 go/no-go:** in headless (`claude -p`) runs, an agent file rewritten by the SessionStart hook keeps its old values for that run, and takes effect from the next run. In interactive sessions the docs say the agent watcher applies the change within seconds, but this was not observed here. Is that lag acceptable (keep D9/D11 unchanged), or should dispatching skills also pass `model`/`effort` per Agent call (a `DC<n>`)?

---

## Source Pack

- **Local files read:**
  - `agents/runtime-bindings.json`, `scripts/render_agent_definitions.py`, `scripts/deploy-harness.sh`, `scripts/install-harness.sh`
  - `scripts/render_codex_adapter.py`, `scripts/check-hook-root-source.sh`, `scripts/run-tests.sh`
  - `harness-manifest.json`, `settings.json`, `adapters/codex/plugin/hooks/hooks.json`, `hooks/session-knowledge.sh`
  - `docs/solutions/harness/review-model-diversity-dropped-decisions.md`, `docs/solutions/harness/hook-root-must-not-come-from-install-location.md`
  - Probe scratch repos `probe1`, `probe2`, `probe3`, `p4reload`, `p4noreload`, `p5`–`p9` in the session scratchpad
- **Upstream repositories or pages checked:**
  - https://opencode.ai/docs/agents
  - https://codex.danielvaughan.com/2026/03/31/codex-cli-profiles-configuration-switching
  - https://codex.danielvaughan.com/2026/03/27/reasoning-effort-tuning/
  - https://aider.chat/docs/config/reasoning.html
  - https://www.mintlify.com/BerriAI/litellm/api/router-config
- **Official docs domains or pages checked:**
  - https://code.claude.com/docs/en/sub-agents.md, https://code.claude.com/docs/en/skills.md, https://code.claude.com/docs/en/hooks.md
  - https://code.claude.com/docs/en/settings.md, https://code.claude.com/docs/en/model-config.md, https://code.claude.com/docs/en/env-vars.md
  - https://code.claude.com/docs/en/changelog

---

## Evidence Boundary

> Confirmed from artifacts (truth, Claude Code 2.1.302 `-p`):
> - A1: agent frontmatter `model`.
> - A2: skill frontmatter `model`/`effort`.
> - A3: `source: startup` with a `startup|clear` matcher.
> - A4: a hook-written skill change applies in the same session, with or without `reloadSkills`.
> - A6: agent `effort` beats session `--effort`.
> - Skill `model: inherit` is valid.
> - A5 is false in `-p`: hook-time and mid-session agent edits are not picked up, even after 10 s.
>
> Inferred from patterns: interactive sessions pick up agent edits through the documented watcher, so the A5 gap is likely limited to headless runs.
>
> Not checked:
> - Interactive mode (no TTY driver installed).
> - `source: clear` delivery, and whether `/clear` reloads agents.
> - A user's mid-session `/effort` (only the `--effort` flag was tested).
> - Hook timing (A7).
> - Changelog entries before 2.1.293.
