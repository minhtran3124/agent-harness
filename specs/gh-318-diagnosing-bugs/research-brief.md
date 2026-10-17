# gh-318-diagnosing-bugs — Research Brief

Written 2026-10-17. Pins: repo ff90b54; Claude Code CLI 2.1.302; upstream mattpocock/skills 49dd158d1076134a641b33efb035946536778336

Depth: **Deep** (intake lane `high-risk` → Deep, `rules/research-depth.md`). No waiver. Evidence did
not change the depth.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Build the skill new and reuse the existing harness parts: the `task-reviewer` agent with its own brief, `review_package.py`, `run_at_commit.py`, `ESCALATIONS.md`, and the implementer red/green rules. Do not copy upstream text. |
| **Why this is the lightest credible path** | Every gate the design needs exists. The new work is one skill folder, ten edited files, two registrations, and two count updates in tests. |
| **Confidence** | 80% |
| **Next step** | User confirms the four design consequences under "Follow-up questions" (they widen the file list), then `writing-plans`. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Prompt/skill framework (Markdown skills, Bash hooks, Python checkers) |
| Primary language + runtime | Markdown; Bash 5.2 and Python 3 (stdlib) on Linux in this session |
| Frameworks / platforms | Claude Code 2.1.302 (observed `claude --version`); Codex advisory alpha adapter |
| Relevant packages | none (no dependency manifest is touched) |
| Detectable versions | Claude Code CLI 2.1.302 |
| Important constraints | 600-word skill ceiling counted on the whole file, frontmatter included (`scripts/audit_skill_prompts.py`); `workflow-engine` signal fires (warn mode) and requires a context-propagation-audit receipt at finishing (`scripts/check_review_receipt.py:51`); no `templates/`, `hooks/`, or `settings.json` change (design Non-goals) |

---

## Feature Understanding and Assumptions

- **Requested feature:** issue #318 as pinned in `specs/gh-318-diagnosing-bugs/intent.md @ a82f1ba`, designed in `design.md` (D1–D13).
- **What success appears to mean:** the design's Success criteria.
- **Assumptions from the request:** the approved design.
- **Assumptions still needing confirmation:** the four consequences under "Follow-up questions".

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | Audit word counts, whole file (measured 2026-10-17 `audit_skill_prompts.py --json`): `subagent-driven-development` **600** of 600 (budget); `feature-intake` 539; `compound` 525; `writing-plans` 482. The design's 461 for `feature-intake` is body-only. |
| `Local` | `harness-manifest.json:228-242` `skills[]` must list the new skill: `scripts/check_manifest.py:93-99` and `scripts/render_codex_adapter.py:173-177` fail otherwise; audit, frontmatter, and tool-conformance checks skip unlisted skills. |
| `Local` | `scripts/test_audit_skill_prompts.py:145-146` asserts `skills == 14` and `companion_prompts == 11`. A new skill makes 15; a `*prompt*.md` file under it makes 12. |
| `Local` | `scripts/deploy-harness.sh:370-399,595-598` copies `skills/*` by glob; `:477-507` strips `skills/*/tests/`; `:420-444` rewrites paths in `*.md` only. The Codex renderer copies whole skill dirs, `tests/` included (`scripts/render_codex_adapter.py:207-215,251-253`). |
| `Local` | Content checks for a new skill: non-empty `allowed-tools:` (`scripts/check-allowed-tools.sh:14-24`); a `Bash(...)` grant for every backticked command (`scripts/check_skill_tool_conformance.py:141-188`); no literal `.claude/skills/`, `.claude/rules/`, or model id (`scripts/check_runtime_neutral_sources.py:23-29,91-94`); backticked repo paths must resolve after deploy, so write `skills/diagnosing-bugs/scripts/hitl-loop.template.sh`, not `scripts/hitl-loop.template.sh` (`scripts/lint-doc-truth.sh:104-158`); ```` ```bash ```` blocks pass `bash -n`/shellcheck (`scripts/lint-skill-bash.sh`). `run-tests.sh:30` does not `bash -n` skill scripts. |
| `Local` | Seam conflict with D13, verified 2026-10-17: `rules/plan-format.md:68` "A bug-fix task never writes `none`"; `skills/subagent-driven-development/task-reviewer-prompt.md:70` makes `Seams:` `none` an Important finding; `implementer-prompt.md:58-59` returns `NEEDS_CONTEXT` on `Seams: none`. `scripts/check_task_review_contract.py:22-28` pins the literal strings "Write the red test at a declared seam" and "cannot observe the behavior, return `NEEDS_CONTEXT` before any edit". |
| `Local` | Normal-lane plans: no skill names the author. `gh-302-red-green-input-type` and `gh-277-strict-gate-no-merge-base` had the session write `PLAN.md` inline; their plans have no `Plan-contract: 2` and no `Seams:`. Only `gh-312-test-seams` and `gh-313-prove-the-red` plans carry `- Plan-contract: 2` (`grep -l "^- Plan-contract: 2" specs/*/PLAN.md`). |
| `Local` | `task-reviewer` can review a non-PLAN artifact: `agents/task-reviewer.md:1-10` names no PLAN field; the PLAN-specific inputs live in `task-reviewer-prompt.md:22-94`. `task_brief.py:47-48` errors without a PLAN task, so the diagnosis review uses its own brief. Tools are Glob, Grep, Read (`agents/runtime-bindings.json:40`); the reviewer cannot re-run the loop. |
| `Local` | SDD hooks: implementer dispatch `skills/subagent-driven-development/SKILL.md:51-55`; after the last wave `:71-72` reads `references/review-chain.md`, whose `:3` starts with `context-propagation-audit`. A Phase 6 step placed in `review-chain.md` costs 0 SKILL words and is on the `resume <slug>` path. |
| `Local` | `systematic-debugging` also appears in `skills/xia2/README.md:17` (harness-only doc), besides `skills/README.md:79,144,168`. |
| `Local` | Replay case verified (truth, measured 2026-10-17 subagent run, 3 runs each): `docs/solutions/scripts/test-r-dev-tty-does-not-detect-missing-controlling-terminal.md`; pre-fix `0048a16`, fix `ac7f472` (changes only `scripts/deploy-harness.sh`); the catching assertion is in `8e72f7f`, after the fix. Overlay `git show 8e72f7f:tests/scripts/resync-conflict.test.sh` → red exit 1 (`20 passed, 1 FAILED`, case 4) at `0048a16`, green exit 0 (`21 passed`) at `ac7f472`; ~7 s per run (measured 2026-10-17). Overlay file identity at both commits checked locally (`git diff --quiet 0048a16 ac7f472 -- tests/scripts/resync-conflict.test.sh`). |
| `Upstream` | `raw.githubusercontent.com/mattpocock/skills/49dd158/skills/engineering/diagnosing-bugs/SKILL.md` (read 2026-10-17): six phases match the issue; Phase 5 adds "prove any forced mutation landed"; a "Redact" section already exists. |
| `Upstream` | `…/49dd158/skills/engineering/diagnosing-bugs/scripts/hitl-loop.template.sh` (read 2026-10-17): the script lives under the skill, not repo-root `scripts/` (that path is 404). Interface: `step "<instruction>"` waits for Enter; `capture VAR "<question>"` reads an answer; ends with `--- Captured ---` and `KEY=VALUE` lines. |
| `Upstream` | `…/49dd158/docs/engineering/diagnosing-bugs.md` (read 2026-10-17): #578 over-firing, accepted direction "start lighter, escalate"; #124 approval gate before the fix, open; #674 redaction, described as open although SKILL.md has a Redact section. The issues themselves were not readable (repo not in session scope, HTTP 403). |
| `Docs` | `code.claude.com/docs/en/skills` (read 2026-10-17, CLI 2.1.302): with `disable-model-invocation: true` the user can run `/name`; Claude cannot invoke it on its own; its description is not in context; "If Claude tries anyway, Claude Code blocks the call and instructs it not to reproduce the … steps another way." |
| `Inference` | Because of the block message above, a `feature-intake` line that says "follow the diagnosing-bugs skill" can make the model call the Skill tool, be blocked, and then refuse the steps. The line must name the Read tool and the file path and forbid the Skill tool. |
| `Inference` | Codex: no code reads `disable-model-invocation` (whole-repo grep); `specs/session-retro/SUMMARY.md:88` records Codex support for it as unconfirmed. On Codex the flag may be ignored. |

---

## Local Findings

- **Relevant files:** see the Evidence Ledger. Integration points: `skills/feature-intake/SKILL.md:60-69` (Routes); `skills/subagent-driven-development/SKILL.md:51-55,71-72` and `references/review-chain.md:3`; `implementer-prompt.md:28-31,45-71`; `task-reviewer-prompt.md:64-76`; `rules/plan-format.md:50-82`; `skills/writing-plans/SKILL.md:17-18,26-31`; `skills/compound/SKILL.md:15-25` and `subagents/solution-extractor-prompt.md:5-8`.
- **Existing abstractions:** `task-reviewer` agent; `review_package.py` (no PLAN dependency); `run_at_commit.py`; `ESCALATIONS.md`; `skills/feature-intake/tests/*.md` case format (ID table plus `## Notes`, listed in `tests/README.md:35-39`).
- **Conventions worth preserving:** skill scripts are mode `100644` and run with `bash <path>` (`skills/using-git-worktrees/scripts/detect-isolation.sh`); dispatch prompt files are named `*prompt*.md` and counted as companion prompts.
- **What can be reused:** all gates; the replay case; the implementer red/green procedure.
- **What is missing:** a diagnosis step; a standalone reviewer brief; a defined normal-lane plan author.

---

## Upstream Findings

- **Repositories inspected:** github.com/mattpocock/skills at `49dd158` (three files above).
- **Pattern present upstream:** six phases with one exit criterion each; Phase 1 lists ten loop techniques in preference order (failing test, curl, CLI on a snapshot, headless browser, replayed trace, throwaway harness, fuzz, bisect harness, differential, human-in-the-loop script).
- **Worth modeling:** the phase criteria and the loop-technique ladder (as ideas, rewritten); the `step`/`capture` interface for the HITL script.
- **Match to this repo:** upstream has no lane, reviewer, or spec-record concept. Those come from the harness.
- **Gaps:** issue texts unread (403). The doc and SKILL.md disagree on whether #674 is fixed.

---

## Docs Findings

- **Official sources checked:** `code.claude.com/docs/en/skills` (frontmatter reference, "Control who invokes a skill").
- **Version status:** read 2026-10-17 against the installed CLI 2.1.302; the page carries no version marker.
- **Built-in capabilities:** `disable-model-invocation` and `user-invocable` cover D1 directly.
- **Recommended workflow:** user-triggered workflows use `disable-model-invocation: true`.
- **Caveats:** the blocked-call message tells the model not to reproduce the steps another way (see Inference row); the flag also stops preloading into subagents.

---

## Recommendation

- **Primary recommendation:** build from scratch, reusing harness parts. The design holds, with the four consequences below.
- **Why lightest:** no new script or gate under `scripts/`; the skill folder carries its own references, brief, template, and HITL script.
- **Why the next-best alternative lost:** copying upstream text would import licence questions and a different process model; the harness parts already supply review and evidence.
- **What would change this:** if the Read-and-follow chain fails in the proof run (A1), fall back to a model-invocable skill with a narrow description.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - SDD SKILL.md is at 600/600 (budget). Any added SKILL words need equal deletions by the #308 deletion test. Mitigation: put the seam check and the diagnosis-path instruction in a new `skills/subagent-driven-development/references/bug-fix.md`, read at dispatch, and Phase 6 in `references/review-chain.md`; the SKILL.md pointer must be paid for by a deletion.
  - `feature-intake` has 61 words of headroom (budget 600, measured 539), not 139. The routing line must stay short.
  - A1: the Skill-tool block message (Docs row). The routing line must say "Read … with the Read tool; do not call the Skill tool".
- **Evidence gaps:** upstream issue texts; Codex handling of `disable-model-invocation`.
- **Version uncertainties:** the docs page has no version; behavior was not yet observed on CLI 2.1.302 (the proof run does that).
- **Follow-up questions for the user** (each widens the approved file list or refines a settled decision):
  1. **D13 needs three more edits.** `Seam: none — <reason>` → `Red test exempt` conflicts with `rules/plan-format.md:68`, `task-reviewer-prompt.md:70`, and `implementer-prompt.md:58-59`. Edit all three so a bug-fix task whose `diagnosis.md` says `Seam: none — <reason>` may write `Seams: none — <reason>`, and the reviewer and implementer accept it. Keep the two pinned literal strings.
  2. **D12 refinement.** When `diagnosis.md` exists, the fix task's plan must carry `- Plan-contract: 2` and a `Seams:` line; a missing marker or line counts as a mismatch. When the fix task has more than one seam, the first seam's point is compared.
  3. **Extra edits:** register `diagnosing-bugs` in `harness-manifest.json` `skills[]`; update `scripts/test_audit_skill_prompts.py:145-146` to 15 and 12; remove `systematic-debugging` from `skills/xia2/README.md:17` too.
  4. **Second proof run for A1.** Besides the quick-question run, record a bug-fix run through intake whose tool-call log shows a Read of `skills/diagnosing-bugs/SKILL.md` and no Skill call for it.

---

## Source Pack

- **Local files read:** `skills/README.md`, `skills/feature-intake/SKILL.md` and `tests/`, `skills/subagent-driven-development/SKILL.md`, `implementer-prompt.md`, `task-reviewer-prompt.md`, `references/review-chain.md`, `scripts/review_package.py`, `scripts/task_brief.py`, `skills/writing-plans/SKILL.md`, `skills/compound/SKILL.md`, `skills/compound/subagents/solution-extractor-prompt.md`, `skills/context-propagation-audit/SKILL.md`, `skills/xia2/README.md`, `rules/plan-format.md`, `rules/orchestration.md`, `rules/auto-correct-scope.md`, `agents/task-reviewer.md`, `agents/agent-contracts.json`, `agents/runtime-bindings.json`, `harness-manifest.json`, `scripts/deploy-harness.sh`, `scripts/install-harness.sh`, `scripts/deploy-codex-adapter.sh`, `scripts/render_codex_adapter.py`, `scripts/codex_harness_doctor.py`, `scripts/audit_skill_prompts.py`, `scripts/test_audit_skill_prompts.py`, `scripts/check_manifest.py`, `scripts/check_frontmatter_contract.py`, `scripts/check-allowed-tools.sh`, `scripts/check_skill_tool_conformance.py`, `scripts/lint-skill-bash.sh`, `scripts/check_runtime_neutral_sources.py`, `scripts/lint-doc-truth.sh`, `scripts/check_task_review_contract.py`, `scripts/check_plan_contract.py`, `scripts/ci-strict-gate.sh`, `scripts/run-tests.sh`, `docs/solutions/INDEX.md`, `docs/solutions/scripts/test-r-dev-tty-does-not-detect-missing-controlling-terminal.md`, `docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md`, `specs/gh-302-red-green-input-type/`, `specs/gh-277-strict-gate-no-merge-base/`, `specs/gh-313-prove-the-red/`, `specs/session-retro/SUMMARY.md`.
- **Upstream repositories or pages checked:** `https://raw.githubusercontent.com/mattpocock/skills/49dd158/skills/engineering/diagnosing-bugs/SKILL.md`, `…/docs/engineering/diagnosing-bugs.md`, `…/skills/engineering/diagnosing-bugs/scripts/hitl-loop.template.sh` (200); `…/49dd158/scripts/hitl-loop.template.sh` (404); `github.com/mattpocock/skills/issues/578`, `/124`, `/674` (403).
- **Official docs domains or pages checked:** `https://code.claude.com/docs/en/skills`.

---

## Evidence Boundary

> Confirmed from artifacts: audit word counts; manifest list and test counts; the three seam-rule
> conflicts; deploy glob and `tests/` stripping; replay red/green (subagent runs, commits and test
> identity re-checked locally); docs text on `disable-model-invocation`.
> Inferred from patterns: the Skill-tool block risk for Read-and-follow; normal-lane plans are
> written inline by the controller session.
> Not checked: the upstream issue texts; Codex behavior for `disable-model-invocation`; the
> Read-and-follow chain on CLI 2.1.302 (left to the proof run); the last 9,870 characters of the
> docs page.
