# Research Brief — acceptance-contract-loop-budget

Depth mode: **Deep** (high-blast: workflow-engine surface — skills/, rules/, templates/,
scripts consumed by hooks/CI). Spec: `specs/acceptance-contract-loop-budget/design.md`.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Extend existing (verify_summary.py gate + skill prompts) — no new scripts, no new hooks |
| **Why this is the lightest credible path** | Every integration point already exists: `check_lane_evidence` is the shared lane-evidence function both modes and the commit gate call; the receipt ship-gate and intent-review oracle list are extension points, not new machinery |
| **Confidence** | 90% |
| **Next step** | writing-plans — sequence contract chain (waves 1–2) and loop budget (independent wave) |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Meta-repo: skill/hook/rule harness for Claude Code (no application stack — `techstacks/` empty by design) |
| Primary language + runtime | Markdown skill prompts + Python 3 scripts + bash hooks |
| Relevant scripts | `scripts/verify_summary.py`, `scripts/ci-strict-gate.sh`, `scripts/check_verify_rows.py`, `scripts/check_review_receipt.py`, `scripts/run-tests.sh` |
| Important constraints | Verify commands pipe-free + <60s (critical KB entry); `verify_summary.py --lane` is the declared single source of truth for lane→evidence (`rules/auto-correct-scope.md:38`); PYTESTS list in `run-tests.sh:55` is hardcoded — new test files must be added there |

## Feature Understanding and Assumptions

- **Requested feature:** machine-readable expected results at plan time (SC table) + bounded fix-loop (cap 3 + progress guard), per approved design.md.
- **Success means:** a new high-risk/normal plan cannot ship without every SC proven by a Verify row; a correctness fix-loop can no longer spin unbounded.
- **Assumptions confirmed:** parser positional (`cells[0..3]`), trailing 5th column round-trips `_rewrite_table` unchanged; ci-strict-gate delegates entirely to verify_summary.
- **Needing confirmation:** none blocking — spec review round 2 verified all load-bearing claims against ground truth.

## Local Findings

- **Extension points (all `Local`, file:line from exploration):**
  - `verify_summary.py`: `main` :393, argparse :400–407; lane mode → `_check_lane_targets` :227 → **`check_lane_evidence` :182** (shared accumulation point — SC-coverage logic belongs here, NOT in `run_checks` which is execution-only); check mode :422–496; `--check` suppresses `_rewrite_table` :490–494.
  - `skills/writing-plans/SKILL.md` :39–48 (`## File Structure`, runs "before defining tasks") — insertion point for the SC-authoring step; plan schema itself has exactly one home: `rules/plan-format.md` (SKILL.md :50–70 delegates).
  - `skills/intent-review/SKILL.md` :57–72 (`## 1. Oracle input`) — contract becomes a third oracle bullet after design.md Success Criteria (:63–64); reflect in Section 4 dispatch inputs :91–97 and Section 5 taxonomy :99–114. Conflict rule stays: verbatim request wins.
  - `skills/subagent-driven-development/SKILL.md` :228–249 (`## Review Receipt`) — ship gate; design deliberately does NOT extend the receipt schema; exit-gate wording extends the checklist + Final Intent Review residual gate :208–220 and Red Flags :434–438.
  - `skills/correctness-review/SKILL.md` :128–130 — the unbounded "repeat until ✅" line to replace with cap + progress guard.
- **Test conventions:** `scripts/test_verify_summary.py` (colocated, importlib loader, `make_summary`/`write_summary` helpers); hermetic-git pattern in `scripts/test_check_review_receipt.py`. Register new/extended test file in `run-tests.sh` PYTESTS (:55). L1 lint `check_verify_rows.py` (:27–40 of run-tests.sh) already scans SUMMARY Verify commands — PLAN SC-table commands should get the same pipe-free/no-full-suite lint (small extension, same script).
- **Constraints from rules:** `wave-parallelism.md` Invariant 1 zero file overlap — plan must keep SC work and loop-budget work on disjoint files (they are); `auto-correct-scope.md` :38 — SC-coverage must land in `verify_summary.py` itself, not prose only.
- **KB consultation (Deep requirement):**
  - `verify-row-must-be-pipe-free-and-under-60s` (critical) — SC check commands inherit both constraints; its "Guardrail: proposed" lint is partially shipped as `check_verify_rows.py` → extend to PLAN SC tables.
  - `automation-readiness` (critical) — answered explicitly: this adds **no standing automation**; it extends an already-wired gate. Fail-safe: fail-open by construction (no PLAN/no SC table → today's behavior); failures are loud commit-gate messages. Warranted/objective: fires only when a contract was authored; pass/fail is exit-code objective.
  - `test-and-doc-lint-gate-scope` — PYTESTS explicit; doc-truth lint will check any paths named in edited rule/skill docs.

## Upstream Findings

- Workflow skills descend from `obra/superpowers` (memory: skills-forked-from-superpowers, with documented deliberate deviations). The acceptance-contract + bounded-loop mechanics are internal governance design with no upstream dependency; no external repo pattern needed. Label: `Local`/`Inference`. Web sweep skipped as best-effort-not-blocking — the feature has zero external surface.

## Docs Findings

- Not applicable — no external library/API involved; all contracts are repo-internal (verify_summary/ci-strict-gate/skill prompts). Version discipline: scripts are stdlib-only Python.

## Recommendation

- **Primary:** extend existing — `check_lane_evidence` for SC coverage (both modes get it for free), trailing `Criterion` column, prompt edits in 4 SKILL.md files + `rules/plan-format.md` + template, tests in `scripts/test_verify_summary.py`.
- **Next-best alternative lost:** new standalone `check_acceptance.py` script — rejected: duplicates parsing, violates the declared single-source-of-truth (`auto-correct-scope.md:38`), adds a wiring surface.
- **Would flip the decision:** if `check_lane_evidence` could not see the spec directory (it can — `_check_lane_targets` resolves paths).

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** (a) SC parsing from PLAN.md must ignore fenced illustration blocks (same rule as task parsing — fenced = illustration); (b) `/context-propagation-audit` will require proof that each consumer (implementer subagent, reviewers, scorer) actually receives the SC instructions — plan must include explicit Read steps, not assume `paths:` injection (write-flows don't trigger it).
- **Evidence gaps:** none load-bearing.
- **Follow-up questions:** none.

## Source Pack

- Local files read/explored: `rules/plan-format.md`, `scripts/verify_summary.py`, `scripts/ci-strict-gate.sh`, `scripts/run-tests.sh`, `skills/{writing-plans,intent-review,subagent-driven-development,correctness-review}/SKILL.md`, `templates/SUMMARY.template.md`, `templates/REVIEW-RECEIPT.template.json`, `docs/solutions/harness/{verify-row-must-be-pipe-free-and-under-60s,automation-readiness}.md`, `rules/{wave-parallelism,auto-correct-scope,orchestration}.md`.
- Upstream/docs: none (internal-only feature; see sections above).

## Evidence Boundary

> Confirmed from artifacts: parser positional layout; `_rewrite_table` 5-col round-trip; ci-strict-gate delegation; receipt schema aggregate-only; unbounded fix-loop text; insertion points listed above with line numbers.
> Inferred from patterns: SC lint extension effort (small — same regex family as `check_verify_rows.py`).
> Not checked: `evals/` behavioral fixtures for review-chain (may want an eval later; out of scope per design non-goals).
