# Research Brief — gh-263-plan-format-lint-example

Written 2026-10-09. Pins: agent-harness `b0d2a92`. Depth: **Deep** (intake lane high-risk →
Deep per `rules/research-depth.md`). Re-run with evidence below: no change. External surface: none.

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing: point the example at `scripts/check_plan_contract.py` |
| **Why this is the lightest credible path** | That script already rejects a contract plan without SC rows (exit 1) and passes a well-formed one (exit 0), which is exactly what the example's two rows claim. |
| **Confidence** | 95% |
| **Next step** | `writing-plans`: one task, edit two lines, verify with the design §6 fixtures. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Skill framework / workflow-as-code meta-repo |
| Primary language + runtime | Markdown rules; Python 3 stdlib scripts; Bash tests |
| Frameworks / platforms | Claude Code skills/rules; Codex advisory alpha |
| Relevant packages | none |
| Detectable versions | `VERSION` 2.28.0 |
| Important constraints | `rules/plan-format.md` is path-scoped (`paths: specs/**/PLAN.md`) and explicitly Read by writing-plans and the plan reviewer; fenced tables are ignored by every parser |

---

## Feature Understanding and Assumptions

- **Requested feature:** #263. Make the fenced SC example in `rules/plan-format.md` use a command that exists.
- **What success appears to mean:** design §7. Zero `verify_summary.py --lint` hits, two `check_plan_contract.py specs/<slug>/PLAN.md` rows, fixture runs exit 1 and 0, suite green.
- **Assumptions from the request:** the scope is the example only (user decision, 2026-10-09).
- **Assumptions still needing confirmation:** none.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `rules/plan-format.md:99-100`: the only `--lint` usage. `grep -rn -- '--lint'` over `*.md`, `*.sh` and `*.py`, excluding `specs/`, `.claude/` and `.worktrees/`, finds only these two lines. |
| `Local` | `python3 scripts/verify_summary.py --lint specs/<x>` exits 2 ("unrecognized arguments: --lint"). Usage lists `--check`, `--lane`, `--plan-dir`, `--timeout` (2026-10-09). |
| `Local` | `git log -S'--lint' -- scripts/verify_summary.py` returns nothing. The flag never existed, so the example was wrong when written (it arrived with `78db5a6`, the acceptance-contract SC schema commit). |
| `Local` | `scripts/check_plan_contract.py <PLAN.md>`: on sample contract plans it exits 1 with "Success Criteria table has no SC rows", and 0 on a well-formed one (2026-10-09). A plan with no `## Global Constraints` is skipped and exits 0. |
| `Local` | `scripts/deploy-harness.sh`: `check_plan_contract.py` is in `CONSUMER_SCRIPTS`, and `rewrite_derived_paths()` rewrites `scripts/check_plan_contract.py` to `.claude/scripts/…` in consumers. The new example stays runnable after deploy. |
| `Local` | Tests that mention `plan-format.md` (`rule-loading-tiers`, `writing-plans-contract`, `lint-doc-truth`, `commit-gate`) pin the file's tier, its explicit Read, a synthetic copy, and task syntax. None pins lines 99–100. |
| `Local` | `specs/audit-prompt/SUMMARY.md:128` recorded the same defect earlier as a pre-existing advisory (score 0), with the same suggested fix. |
| `Inference` | `scripts/lint-doc-truth.sh` skips paths containing `<`, so `specs/<slug>/PLAN.md` will not trip it (confirmed by the design reviewer, 2026-10-09). |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `rules/plan-format.md`, `scripts/check_plan_contract.py`, `scripts/verify_summary.py`, `scripts/deploy-harness.sh`, the four tests listed above.
- **Existing abstractions or extension points:** `check_plan_contract.py` is the authority for "a contract plan has SC rows".
- **Conventions worth preserving:** fenced examples are illustrative and ignored by parsers; the SC grammar is `exit <n>` followed by optional free text.
- **What can likely be reused:** the checker as-is.
- **What appears missing locally:** a guard against fenced commands with invalid flags. It is out of scope (design §8).

---

## Upstream Findings

- **Repositories inspected:** none. This is a repo-internal doc example with no upstream analogue.
- **Pattern or capability already present upstream:** none found.
- **Files, modules, or areas worth modeling:** none.
- **How closely the upstream pattern matches this repo:** not applicable.
- **Any upstream gaps or uncertainties:** none.

---

## Docs Findings

- none (local-only; no external surface)

---

## Recommendation

- **Primary recommendation:** reuse existing. Use the design §4 replacement rows verbatim.
- **Why this is the lightest credible path:** the checker exists, its exit codes match the example's claims, and deploy already rewrites its path for consumers.
- **Why the next-best alternative lost:** adding `--lint` to `verify_summary.py` would create a new interface to fit a wrong doc. A pinning test or a general lint was declined by the user.
- **What would change this recommendation:** if `check_plan_contract.py` were removed from `CONSUMER_SCRIPTS`, the example would not run in consumers.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** R1. The new SC-1 Expected text, "exit 1 — no SC rows", reads as the only exit-1 cause, though the checker also exits 1 for other contract defects. Acceptable for an illustration (design reviewer advisory).
- **Evidence gaps:** none.
- **Version uncertainties:** none.
- **Follow-up questions for the user:** none.

---

## Source Pack

- **Local files read:** `rules/plan-format.md`; `scripts/check_plan_contract.py`; `scripts/verify_summary.py` (usage); `scripts/deploy-harness.sh` (`CONSUMER_SCRIPTS`, `rewrite_derived_paths`); `tests/scripts/rule-loading-tiers.test.sh`; `tests/scripts/lint-doc-truth.test.sh`; `tests/hooks/commit-gate.test.sh`; `specs/audit-prompt/SUMMARY.md`
- **Upstream repositories or pages checked:** - none found (repo-internal doc example; no upstream analogue)
- **Official docs:** - none (local-only; no external surface)
