# Research Brief — gh-253-codex-full-payload

Depth: **Deep** (intake lane `high-risk`, high-blast `hooks/` edit). No upgrade needed; the
evidence matched the intake signals.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing |
| **Why this is the lightest credible path** | Every mechanism already exists: the consumer subset and the Markdown path rewrite in `scripts/deploy-harness.sh`, the generic non-clobber `project/` overlay sync in `scripts/deploy-codex-adapter.sh`, the append-only `.gitignore` step in `scripts/install-harness.sh`, and the multi-candidate helper probe in both hooks. Item 1 points them at a third location. |
| **Confidence** | 85% |
| **Next step** | `writing-plans` against `design.md` (with the gitignore component added). |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Meta-repo: skill/hook harness for Claude Code with a Codex advisory-alpha adapter |
| Primary language + runtime | Bash (macOS 3.2 compatible) + Python 3 stdlib |
| Frameworks / platforms | Claude Code hooks/skills; Codex CLI 0.147.0 plugin + marketplace (observed macOS arm64) |
| Relevant packages | none (stdlib only) |
| Detectable versions | `VERSION`; Codex evidence pinned in `specs/codex-support/evidence/codex-0.147.0/` |
| Important constraints | `CLAUDE.md` Gotchas (run `scripts/run-tests.sh` before `hooks/`/`scripts/` edits; ci-strict-gate block tier); roadmap §3 shared constraints (Bash 3.2, no real Codex config mutation in tests, Claude behaviour preserved) |

## Feature Understanding and Assumptions

- **Requested feature:** #253 — a Codex-only install ships everything its skills and hooks reference.
- **What success appears to mean:** zero unresolved helper references in a rendered Codex install; `commit-gate.sh` runs lane evidence under Codex; Claude output unchanged.
- **Assumptions from the request:** payload location `.codex/.agent-harness/payload/` (user-selected).
- **Assumptions still needing confirmation:** none that flip the recommendation.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | Rendered adapter (`render_codex_adapter.py --output <tmp>`) contains only `plugin/{hooks,skills}` + `project/.codex/{agents,harness-instructions.md}`; a scan of rendered `SKILL.md` files finds 26 unresolved `rules|runtime|scripts|templates` references. |
| `Local` | Skills also run skill-local helpers by project-root path: `python3 skills/visual-planner/render_plan.py` (`writing-plans`, `finishing-a-development-branch`, `rules/wave-parallelism.md`), `skills/subagent-driven-development/scripts/task_brief.py`, `bash skills/using-git-worktrees/scripts/detect-isolation.sh`. Shipped skills hold 8 non-Markdown, non-test helper files in total (found in spec review, iteration 1). |
| `Local` | `deploy-harness.sh:45-59` `CONSUMER_SCRIPTS` (6 scripts) + `CONSUMER_DATA` (`harness-manifest.json`) — the exact set Codex lacks. `:395-410` `rewrite_derived_paths` rewrites only `scripts/<subset>`, `harness-manifest.json`, and `render_plan.py` invocations, token-anchored by `(?<![\w./-])`. |
| `Local` | A scratch Claude install puts payload under `.claude/{rules,runtime,scripts,templates}`; deployed skills still cite bare `rules/…` and `runtime/run_state.py` (latent Claude gap, out of scope). |
| `Local` | `deploy-codex-adapter.sh:200-258` syncs every file under rendered `project/` with hash-tracked refresh / `.harness-incoming` / retired-file prune / remove-preserves-edits. `:347-351` rmdirs only `.codex/agents`, `.codex`, and the state dir, so nested empty payload dirs would be left behind. |
| `Local` | `commit-gate.sh:167` probes `scripts/` then `.claude/scripts/` for `verify_summary.py`; `:291` fail-open message. `session-knowledge.sh:121-122` probes `runtime/` then `.claude/runtime/` for `runtime_mode.py`. Both `cd` to the runtime-provided project root first (`commit-gate.sh:145-152`), so relative candidates are project-relative. |
| `Local` | `commit-gate.sh:111` strict untracked-`.py` deny uses `git ls-files --others --exclude-standard` and excludes only `.claude/`. The Codex installer never touches `.gitignore`, so plugin-shipped `.py` files under `.codex/.agent-harness/marketplace/` already trip it under `--profile strict` (pre-existing), and the payload would add more. `install-harness.sh:249-297` has the append-only gitignore pattern to mirror. |
| `Local` | KB `hook-root-must-not-come-from-install-location` — hooks must keep resolving the root from the runtime, never `SCRIPT_DIR`; the third candidate is project-relative, so it complies. KB `consumer-risk-modes-index-safe` — hooks must never read a worktree/`.claude/` manifest copy; the payload `harness-manifest.json` is for skills to read, and no hook will read it. |
| `Docs` | Codex execpolicy rules live in `$CODEX_HOME/rules/*.rules` (https://developers.openai.com/codex/rules). Project-scoped `.codex/rules/` loading is not documented either way. |
| `Inference` | An unnamespaced `.codex/rules/` could collide with a Codex config layer, so namespacing under `.agent-harness/` is the safe choice. |

## Local Findings

- **Relevant files:** `scripts/render_codex_adapter.py`, `scripts/deploy-codex-adapter.sh`, `scripts/install-codex-harness.sh`, `scripts/deploy-harness.sh` (subset source), `hooks/commit-gate.sh`, `hooks/session-knowledge.sh`, `adapters/codex/schema.json`, `scripts/test_render_codex_adapter.py`, `tests/scripts/codex-install.test.sh`, `tests/scripts/codex-alpha-contract.test.sh`, `docs/codex-alpha-install.md`.
- **Extension points:** renderer `render()` (adds the payload copy + Markdown rewrite); deployer `project/` overlay (no lifecycle change); hook candidate loops.
- **Conventions worth preserving:** single-source consumer subset; derived-Markdown-only rewrite; fail-closed render; append-only `.gitignore` edit that respects an already-tracked directory.
- **Reusable:** the rewrite regex shape; the gitignore block logic, ported or factored.
- **Missing locally:** a reference-closure test for any runtime's derived skills.

## Upstream Findings

- **Repositories inspected:** OpenAI Codex execpolicy docs mirror (for the `rules/` namespace question).
- **Pattern already present upstream:** none found for shipping plugin-adjacent project payloads; Codex plugins bundle skills/hooks only.
- **Areas worth modeling:** none beyond the local precedent.
- **Upstream gaps:** project-level Codex rules scoping is undocumented.

## Docs Findings

- **Official sources checked:** https://developers.openai.com/codex/rules
- **Version-matched status:** latest docs, not pinned to 0.147.0. The design only depends on *not* using `.codex/rules/`, which is safe under either answer.
- **Built-in capabilities:** none that ship non-skill payloads into a project.
- **Caveats:** none affecting this change.

## Recommendation

- **Primary recommendation:** reuse existing — the design's project payload, plus an append-only gitignore entry for `.codex/.agent-harness/`.
- **Why lightest:** no new lifecycle code; four small extensions to existing mechanisms.
- **Why the next-best alternative lost:** plugin-embedded payload depends on an unobserved cache path (see `design.md` Alternatives).
- **What would change it:** evidence that Codex exposes a stable plugin-root variable to skill text at runtime.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** (1) An over-broad Markdown rewrite corrupts prose; mitigated by the existence-gated, token-anchored rewrite and the closure test. (2) Payload `.py` files under strict profile; mitigated by the gitignore step. (3) Empty nested dirs left on remove; mitigated by deepest-first cleanup.
- **Evidence gaps:** live Codex execution of a payload-rewritten skill is not observed; deterministic tests only (roadmap: no paid probes in CI).
- **Version uncertainties:** Codex > 0.147.0 behaviour is unobserved.
- **Follow-up questions:** none.

## Source Pack

- **Local files read:** `scripts/render_codex_adapter.py`, `scripts/deploy-codex-adapter.sh`, `scripts/install-codex-harness.sh`, `scripts/install-harness.sh`, `scripts/deploy-harness.sh`, `hooks/commit-gate.sh`, `hooks/session-knowledge.sh`, `skills/*/SKILL.md`, `specs/codex-support/{ROADMAP.md,capability-matrix.json,packaging-decision.md}`, `specs/codex-support-phase-3/SUMMARY.md`, `specs/codex-support-phase-5/SUMMARY.md`, `docs/codex-alpha-install.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/INDEX.md`
- **Upstream repositories or pages checked:** https://forge.lthn.ai/core/core-agent-ide/src/commit/167553f00dc7379a0d4d54007c90cf191ed7d2f3/docs/execpolicy.md
- **Official docs domains or pages checked:** https://developers.openai.com/codex/rules

## Evidence Boundary

> Confirmed from artifacts: render output contents; the 26 missing references; hook probe orders; deployer overlay semantics; Claude consumer layout (scratch install); no `.gitignore` handling in the Codex installer.
> Inferred from patterns: the strict-profile untracked-`.py` denial in Codex consumers (from code reading, not reproduced); the `.codex/rules` collision risk.
> Not checked: real Codex CLI execution (no Codex binary on this machine); Linux/WSL Codex runtime.
