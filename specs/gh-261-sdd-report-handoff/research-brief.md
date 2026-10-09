# Research Brief — gh-261-sdd-report-handoff

Written 2026-10-09. Pins: agent-harness `b0d2a92`. Depth: **Deep** (intake high-risk → Deep).
Re-run with evidence: no change. External surface: none.

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing: implement the documented guardrail from `docs/solutions/harness/sdd-report-file-handoff-refused-for-subagents.md` |
| **Why this is the lightest credible path** | The fix is three prose edits plus one test in an existing suite. The reviewer contract, `check_task_review_contract.py` and `CONTEXT_MATRIX` stay untouched. |
| **Confidence** | 90% |
| **Next step** | `writing-plans`: two tasks in one wave. Task 1 covers the prompts, rule and test; task 2 covers the knowledge loop. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Skill framework / workflow-as-code meta-repo |
| Primary language + runtime | Markdown skills and rules; Bash tests; Python 3 stdlib scripts |
| Frameworks / platforms | Claude Code skills; Codex advisory alpha |
| Relevant packages | none |
| Detectable versions | `VERSION` 2.28.0 |
| Important constraints | `rules/orchestration.md` is always-on (no `paths:`); `rules/*.md` and `skills/*` trip the warn-mode `workflow-engine` signal, so a context-propagation audit is required (`check_review_receipt.py --require-audit-if`) |

---

## Feature Understanding and Assumptions

- **Requested feature:** #261, approach A (user choice, 2026-10-09).
- **What success appears to mean:** design §7.
- **Assumptions from the request:** the runtime refusal is policy and will not be lifted.
- **Assumptions still needing confirmation:** none.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | Handoff text at `implementer-prompt.md:107-108`, `SKILL.md:54-56` and `rules/orchestration.md:40-41`, read 2026-10-09 on `b0d2a92`. |
| `Local` | `task-reviewer-prompt.md:21` takes `IMPLEMENTER_REPORT_PATH`; `scripts/check_task_review_contract.py:14` pins the token. Both stay unchanged. |
| `Local` | The design reviewer swept the repo with `grep -rnI` for `IMPLEMENTER_REPORT_PATH`, `report-<task>`, `full contract goes`, `reports under`, `report path`, `report file` and `harness-state/sdd`. Hits outside `specs/` and `.worktrees/`: only the three files above, the solution entry, the backlog and `docs/solutions/INDEX.md`. |
| `Local` | `scripts/render_skill_prompt.py` `CONTEXT_MATRIX` `implementer` entry requires only `rules/auto-correct-scope.md`. `context-propagation-regression.test.sh` pins only the implementer's `FIRST: Read …auto-correct-scope.md` line. Removing `[IMPLEMENTER_REPORT_PATH]` breaks neither. |
| `Local` | `tests/scripts/sdd-artifact-handoffs.test.sh` uses `set -euo pipefail` with bare `grep -q` assertions and an `echo '… passed'` tail, not the `tests/lib.sh` `t`/`pass` idiom. New checks should follow the file's own style. `scripts/run-tests.sh:150` globs `tests/scripts/*.test.sh`, so it is collected. |
| `Local` | No test or script pins the `rules/orchestration.md` "file handoff" sentence. The grep for `file handoff`, `Subagent contract` and `full contract goes` over `tests/` and `scripts/` returned nothing. |
| `Local` | `docs/harness-experimental/improvement-backlog.md:23`: the row is `open`. The solution entry's Guardrail is `proposed:`; `existing:` is the template prefix (`skills/compound/templates/failure-track.md:29-30`). |
| `Local` | `scripts/rebuild_solution_index.py` takes `--check` / `--dry-run`. INDEX order depends on `confirmed_at` (line 44), and no CI step runs the rebuild. |
| `Local` | Runtime refusal observed twice: `opus-5-5-review-bindings` (2/2 implementers, 2026-10-02, "Subagents should return findings as text") and gh-258 (4/4, 2026-10-08; the Bash heredoc fallback was also refused by worktree isolation). |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** the five files in the Evidence Ledger, `tests/scripts/sdd-artifact-handoffs.test.sh`, `scripts/rebuild_solution_index.py`.
- **Existing abstractions or extension points:** `.harness-state/sdd/` as the gitignored artifact directory; the brief/report/package path triple given to the task reviewer.
- **Conventions worth preserving:** "Never paste history or report contents" (into another prompt); the reviewer receives paths, not contents.
- **What can likely be reused:** the controller transcription header already used on gh-258 and gh-263 ("transcribed by controller from the implementer's inline report").
- **What appears missing locally:** nothing beyond the planned edits.

---

## Upstream Findings

- **Repositories inspected:** none. This is a harness-internal handoff contract driven by a runtime policy, with no upstream analogue.
- **Pattern or capability already present upstream:** none found.
- **Files, modules, or areas worth modeling:** none.
- **How closely the upstream pattern matches this repo:** not applicable.
- **Any upstream gaps or uncertainties:** none.

---

## Docs Findings

- none (local-only; no external surface)

---

## Recommendation

- **Primary recommendation:** reuse existing. Apply design §4 as written.
- **Why this is the lightest credible path:** the guardrail is already specified and observed twice; only prose and a presence test change.
- **Why the next-best alternative lost:** approach B rewrites the reviewer contract and loses the artifact used by re-review and resume (design §3).
- **What would change this recommendation:** a runtime change that lets subagents write report files. Even then, A stays correct, because the controller-owned file does not depend on it.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - R1. The test's fixed strings can drift from the prose. Mitigation: plan Global Constraints fix the exact phrases (design §4.2, §4.4).
  - R2. A stale `docs/solutions/INDEX.md` would not fail CI. Mitigation: run `rebuild_solution_index.py`, and check it with `--check` as a Verify.
- **Evidence gaps:** none.
- **Version uncertainties:** none.
- **Follow-up questions for the user:** none.

---

## Source Pack

- **Local files read:** `skills/subagent-driven-development/implementer-prompt.md`; `skills/subagent-driven-development/SKILL.md`; `skills/subagent-driven-development/task-reviewer-prompt.md`; `rules/orchestration.md`; `scripts/check_task_review_contract.py`; `scripts/render_skill_prompt.py`; `tests/scripts/sdd-artifact-handoffs.test.sh`; `tests/scripts/context-propagation-regression.test.sh`; `scripts/run-tests.sh`; `scripts/rebuild_solution_index.py`; `docs/solutions/harness/sdd-report-file-handoff-refused-for-subagents.md`; `docs/harness-experimental/improvement-backlog.md`
- **Upstream repositories or pages checked:** - none found (harness-internal contract; no upstream analogue)
- **Official docs:** - none (local-only; no external surface)
