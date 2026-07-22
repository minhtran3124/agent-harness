# acceptance-contract-loop-budget — Summary

Lane: high-risk
Confidence: high
Reason: Workflow-engine hard gate — the change edits skills/*/SKILL.md, rules/plan-format.md, templates/ and scripts/verify_summary.py (workflow-as-code); direction is unambiguous and the design was human-approved before intake.
Flags: existing behavior, weak proof, multi-domain
Affects: workflow-engine (skills/writing-plans, skills/subagent-driven-development, skills/correctness-review, skills/intent-review, rules/plan-format.md, templates/SUMMARY.template.md, scripts/verify_summary.py)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> hiện tai workflow có vẻ ổn nhưng để đi theo hướng loop thì tôi nhận thấy việc design + plan xong nhưng chưa có 1 expect results cụ thể để agent sau khi code xong, run test, review code có cái để so sánh + đánh giá để đảm bảo rằng nó đạt dc 1 target cụ thể. Mục đích là làm cho việc loop hiệu quả cũng như hạn chế loop vô tận, đốt tài nguyên 1 cách vô nghĩa

> ok, đưa qua /feature-intake chạy full chain đi

Agreed design (user-approved via diagram https://claude.ai/code/artifact/24015d03-800d-4f8b-bc3c-8f38428259e4):
(1) **Acceptance Contract** — upgrade PLAN.md §3 Success Criteria from free prose to a machine-readable schema (`SC-n` + observable behavior + re-runnable check command + expected outcome), written at plan time before code; wire it into spec-compliance review and intent-review; add a `Criterion` column to the SUMMARY.md `### Verify` table with `verify_summary.py` enforcing every SC ↔ ≥1 passing row; ship exit gate = all SC pass + 0 blocking findings. correctness-review FIND stays plan-blind.
(2) **Loop Budget** — mechanize the correctness-review fix-loop bound: cap 3 fix→re-review rounds per finding, plus a progress guard (blocking count not decreasing and diff unchanged between rounds → escalate immediately via ESCALATIONS.md instead of burning tokens).

## What changed

Two mechanisms, landed across 3 waves (branch `feature/acceptance-contract-loop-budget`):

**Acceptance Contract**
- `rules/plan-format.md` — new `## Success Criteria schema (the acceptance contract)`: the `SC-<n>` table grammar (`| ID | Behavior (observable) | Check (re-runnable) | Expected |`, Check inherits the Verify guardrails, `Expected` starts `exit <n>`), fenced-table/legacy-XML exemptions, and the SUMMARY-side `Criterion` column.
- `templates/SUMMARY.template.md` — `### Verify` table gains a 5th `Criterion` column mapping each row to an `SC-n`.
- `scripts/verify_summary.py` — `parse_sc_table()` + SC-coverage enforcement in `check_lane_evidence` (and check mode): when a sibling PLAN.md declares SCs, every SC must be named by ≥1 passing Criterion row; unknown/duplicate ids error; fail-open with no SC table (+11 tests).
- Consumers: `writing-plans` authors the SC table before task decomposition (+reviewer checklist row); `subagent-driven-development` quotes task-relevant SC rows into the isolated spec-reviewer and gates ship on `verify_summary.py --check` incl. SC coverage AND 0 blocking; `intent-review` treats PLAN §3 as a third oracle (gap on unproven SC), precedence unchanged.
- `scripts/check_verify_rows.py` — `check_plan_text()` lints SC-table Check cells (pipe/slow) at L1; `run-tests.sh` passes changed PLAN.md too.

**Loop Budget**
- `skills/correctness-review/SKILL.md` — replaced the unbounded "repeat until ✅" with `## Loop budget (cap + progress guard)`: cap 3 fix→re-review rounds/finding, diff-hash progress guard, mid-loop counter rule, escalation routing to ESCALATIONS.md.

This SUMMARY is the first contract-enforced record — its `### Verify` table below proves all 6 SCs.

### Rationale

The loop (implement → test → review → fix) lacked an objective feature-level stop condition: per-task Verify proves pieces run, but nothing machine-checks "the feature hit its target", and the fix-loop was textually unbounded ("repeat until ✅"). The contract gives every post-code stage a comparison oracle written before code; the budget converts the existing escalate-after-2-failures guidance from orchestration.md into an enforced loop bound.

### Alternatives considered

- Loop Budget only (defer the contract) — rejected: without the contract the loop still has no objective exit, only a cap.
- Free-prose success criteria checked by an LLM judge — rejected: not re-runnable, not enforceable by `verify_summary.py`, contradicts evidence-over-assertion.

### Deviations

- Rule 3 — Added missing `import os` in `scripts/check_verify_rows.py`; `main()`'s PLAN.md/SUMMARY.md routing calls `os.path.basename` but the tests exercised `check_plan_text` directly, so the omission slipped past the pytest suite. Caught by running the linter on this spec's own PLAN.md. Commit `fb37f7e`.
- Plan gap (context-propagation audit FAIL) — Tasks 2.2/2.3 edited only the SKILL.md prose ("quote SC rows into the reviewer prompt") but the reusable dispatch templates `spec-reviewer-prompt.md` / `intent-reviewer-prompt.md` (not in either task's Files set) had no SC slot, so delivery to the isolated reviewers was `assumed`. Added the SC input slots + a Method step to both templates. Commit `7b44342`. PLAN 2.2/2.3 Files were under-scoped.

### Review Findings (final-pass oracles over `main..HEAD`)

- **B (fixed)** — reviewer-prompt templates lacked SC slots → context-propagation FAIL. Fixed in `7b44342` (see Deviations).
- **A (open — needs decision, Rule 4 hook)** — `hooks/commit-quality-gate.sh` Check 1.6 runs `verify_summary.py --lane` against a `mktemp` copy of the staged SUMMARY, whose parent dir has no `PLAN.md`, so `_sc_map_for_summary` fail-opens and **SC coverage is never enforced at commit time**. The *designed* ship gate (`verify_summary.py --check <slug>`, task 2.2 handoff) resolves the real sibling PLAN.md and DOES enforce it, so the feature works as specified — but the plan Risk note's claim that "the commit gate enforces SC coverage on THIS spec" is false. Fix requires a hook edit (Rule 4 / high-blast) or a `--plan-dir` override on `verify_summary.py`. Corroborated independently by correctness-review #1 and the context-propagation audit #6.
- **C (open — needs decision, ambiguous intent scope)** — The loop budget (cap + progress guard) was added only to `correctness-review`; the `intent-review` and per-task spec-reviewer fix-loops remain textually unbounded ("repeat until ✅"). Design deliberately scoped the budget to correctness-review's Rule 1–3 loop, but the verbatim request ("run test, review code ... hạn chế loop vô tận") reads as spanning all post-code review loops. Intent-review flagged this as a `gap` to surface, not silently resolve.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| SC-1 coverage gate | `python3 -m pytest scripts/test_verify_summary.py -q -k sc_coverage` | 0 | missing-coverage SUMMARY fails lane | SC-1 |
| SC-2 backward compat | `python3 -m pytest scripts/test_verify_summary.py -q -k backward_compat` | 0 | 4-col + no-SC-table specs pass as today | SC-2 |
| SC-3 check-mode exit | `python3 -m pytest scripts/test_verify_summary.py -q -k criterion_check_mode` | 0 | Criterion rows validated by actual exit | SC-3 |
| SC-4 SC-table lint | `python3 -m pytest scripts/test_check_verify_rows.py -q -k sc_table` | 0 | piped/whole-suite SC checks rejected at L1 | SC-4 |
| SC-5 loop budget | `grep -q "Loop budget (cap + progress guard)" skills/correctness-review/SKILL.md` | 0 | cap+guard subsection present | SC-5 |
| SC-6 rule schema | `grep -q "Success Criteria schema" rules/plan-format.md` | 0 | SC schema defined in the rule | SC-6 |

### Rollback

- `git revert <merge-sha>` (all changes are markdown/skill/template/script edits on one branch; no data or schema involved)

### Harness-Delta

- `branch-isolation-guard.sh` false positive: it blocks Write to the session scratchpad (`/private/tmp/claude-501/...`), a path outside the repo — visualization files are not implementation edits. Candidate fix-direct or backlog → /compound.
