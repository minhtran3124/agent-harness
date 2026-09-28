---
status: active
---

# PLAN — cheap adoptions from the Spotify comparison

Lane: normal. Source: `docs/research/2026-09-09-spotify-portal-ai-plugins.md` §7, items #1, #8, #9, #2.

## 1. Approach

Four independent adoptions, disjoint files, one branch. Each was re-verified on disk before work
started. Item #2 is scoped to a pilot because its full form invalidates the activation eval
baseline — see SUMMARY Rationale.

## 2. Tasks

### Task 1.1 — Gate skill/agent frontmatter with the plugin validator (wave 1)

- **Files:** scripts/check-plugin-validate.sh, scripts/run-tests.sh
- **Action:** **Scope changed after investigation — the item as written in the report was wrong.**
  It proposed adding frontmatter to `agents/README.md`, `agents/PROJECT.md` and
  `agents/PROJECT.template.md` so `claude plugin validate --strict .` passes. That would REGISTER
  THEM AS THREE DISPATCHABLE AGENTS: the validator classifies every `*.md` under `agents/` as an
  agent, and those three are an index, a per-repo config and its template. Claude Code currently
  ignores them *because* they lack frontmatter (they are absent from the available-agent list).
  Moving them is also not free — `agents/PROJECT.md` is in `deploy-harness.sh`'s
  `BOOTSTRAP_OWNED_FILES` and is referenced by `agents/coding.md` and `agents/test-runner.md`.
  Instead: a checker that fails on any validator **error**, and on any **warning** outside a
  justified three-file allowlist, wired into `run-tests.sh` L1 (which is what CI runs). Skips with a
  NAMED reason when the `claude` CLI is absent — a silent skip is how a gate stops being a gate.
- **Verify:** `bash scripts/check-plugin-validate.sh`
- **Done:** Exits 0 on a clean tree, and exits 1 naming the skill when a `SKILL.md` loses its
  `description:` — demonstrated, not assumed.

### Task 2.1 — Add the `--help` rule (wave 1)

- **Files:** rules/behavior.md
- **Action:** Add §3: before relying on a CLI flag or subcommand, run its `--help`. Adapted from
  `skills/setup/SKILL.md:13` in the Spotify repo. Keep the file's stated bar — it only holds rules a
  frontier model does not already apply reliably — so state the failure mode, not the platitude.
- **Verify:** `grep -c 'help' rules/behavior.md`
- **Done:** §3 exists and names the observable failure (an invented flag).

### Task 3.1 — Extend `allowed-tools` to the 9 skills lacking it (wave 1)

- **Files:** skills/brainstorming/SKILL.md, skills/compound/SKILL.md, skills/context-propagation-audit/SKILL.md, skills/correctness-review/SKILL.md, skills/finishing-a-development-branch/SKILL.md, skills/intent-review/SKILL.md, skills/subagent-driven-development/SKILL.md, skills/using-git-worktrees/SKILL.md, skills/writing-plans/SKILL.md
- **Action:** Derive each skill's list from the tools its own body actually instructs — never a
  generic grant. Read-only review skills get no write tool. A skill that dispatches subagents keeps
  that capability. Under-granting breaks the skill, so verify each list against the skill's own text.
- **Verify:** `bash scripts/lint-skill-bash.sh`
- **Done:** All 12 skills declare `allowed-tools`; no skill lost a tool its body uses.

### Task 4.1 — Description pilot, 3 skills (wave 2)

- **Files:** skills/xia2/SKILL.md, skills/brainstorming/SKILL.md, skills/correctness-review/SKILL.md
- **Action:** Rewrite `description:` in the two-clause shape `<capability>. Use when <user
  situations>.` Add an anti-trigger to the overlapping pair (`xia2` vs `brainstorming`) so each
  declines when the other fits, per the Spotify `search/SKILL.md:3` pattern. `correctness-review` is
  the control: rewritten for voice, no anti-trigger.
- **Verify:** `python3 scripts/audit_skill_prompts.py`
- **Done:** The 3 descriptions read as user situations; the pair carries mutual anti-triggers; the
  eval consequence is recorded in SUMMARY `### Not auto-verified`.

## 3. Success criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
| --- | --- | --- | --- |
| SC-1 | Skill/agent frontmatter breakage fails the suite | `bash scripts/check-plugin-validate.sh` | exit 0 |
| SC-2 | Every skill declares `allowed-tools` | `bash scripts/check-allowed-tools.sh` | exit 0 |
| SC-3 | Existing skill/hook contracts still hold | `bash tests/hooks/scope-gate.test.sh` | exit 0 |

SC-1 and SC-2 are traceability (a validator passes, a field is present). Neither proves a skill still
works with its narrowed tool list — that is stated in `### Not auto-verified`, not claimed here.

## 4. Out of scope

- The remaining 9 `description:` rewrites — blocked on re-baselining the 192-case activation corpus.
- Report item #3 (marketplace packaging) — an escalation, tracked separately.
