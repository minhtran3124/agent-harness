# plan-format SC example — design

Written 2026-10-09. Pins: agent-harness `b0d2a92`, issue #263.

**Status:** approved by the user on 2026-10-09 (scope: fix the example only).

## 1. Goal

The fenced Success Criteria example in `rules/plan-format.md` must show a command that exists
and exits with the codes its Expected cells state, so an author who copies it gets a working SC row.

## 2. Current state

`rules/plan-format.md` lines 99–100 (inside a ```` ```markdown ```` fence, so no parser reads it):

```
| SC-1 | New markdown plan without an SC table is rejected | `python3 scripts/verify_summary.py --lint specs/<slug>` | exit 1 — missing SC table |
| SC-2 | A well-formed SC table passes the lint | `python3 scripts/verify_summary.py --lint specs/<slug>` | exit 0 |
```

`verify_summary.py` has no `--lint` flag. `python3 scripts/verify_summary.py --lint <dir>` exits 2
with "unrecognized arguments: --lint" (measured 2026-10-09). The same defect was recorded earlier
as a pre-existing advisory in `specs/audit-prompt/SUMMARY.md:128`, with the same suggested fix.

The command that does reject a plan without SC rows is `scripts/check_plan_contract.py <PLAN.md>`.
It applies only to contract plans (those declaring `## Global Constraints`). Measured on
2026-10-09 against two sample contract plans: no SC rows → exit 1 ("Success Criteria table has
no SC rows"); a well-formed SC table → exit 0 ("plan-contract: … passed").

## 3. Approaches considered

| Approach | Verdict |
|---|---|
| **A. Fix the example only** | **Chosen by the user.** One file, prose only. |
| B. Fix plus a test pinning this example | Rejected: it guards one example, and the user kept scope minimal. |
| C. Fix plus a general lint of fenced `scripts/*.py` flags against `--help` | Rejected: new lint surface; #263 marks it optional. |

## 4. Change

Replace the two rows with:

```
| SC-1 | A contract plan (one with a Global Constraints section) without SC rows is rejected | `python3 scripts/check_plan_contract.py specs/<slug>/PLAN.md` | exit 1 — no SC rows |
| SC-2 | A well-formed SC table passes the contract check | `python3 scripts/check_plan_contract.py specs/<slug>/PLAN.md` | exit 0 |
```

No other line of `rules/plan-format.md` and no other file changes.

In consumer installs, `scripts/deploy-harness.sh` `rewrite_derived_paths()` rewrites
`scripts/check_plan_contract.py` to `.claude/scripts/check_plan_contract.py`. `check_plan_contract.py`
is in `CONSUMER_SCRIPTS`, so the example stays runnable after deploy, like the old path.

## 5. Error behavior

The table stays fenced, so `render_plan.py`, `check_plan_contract.py` and `verify_summary.py`
keep ignoring it (fence masking). The change affects only what a reader copies.

## 6. Tests

No new test (approach A). Proof:

1. The new command run on a sample contract plan without SC rows exits 1, and on a well-formed
   one exits 0. The fixtures live in the session scratchpad, not under `specs/`. Both declare
   `## Global Constraints` with one bullet and one task with full `Files/Action/Verify/Done/Criteria/Interfaces`
   bullets. Only the well-formed one has an SC table. The failing run's output must contain
   "Success Criteria table has no SC rows", because the checker also exits 1 for other contract
   defects.
2. `bash scripts/run-tests.sh` exits 0. This includes the doc-truth lint over `rules/*.md`.
3. Context-propagation audit: `rules/plan-format.md` still reaches its consumers (writing-plans
   and the plan reviewer Read it explicitly; `paths:` injects it on read).

## 7. Success criteria

1. `grep -c 'verify_summary.py --lint' rules/plan-format.md` prints `0`.
2. `grep -c 'check_plan_contract.py specs/<slug>/PLAN.md' rules/plan-format.md` prints `2`.
3. The two sample-plan runs exit 1 and 0.
4. `bash scripts/run-tests.sh` exits 0 (cited in prose at finishing).

## 8. Non-goals

- A lint or test that checks fenced command examples against `--help` (approach C).
- Any other edit to `rules/plan-format.md`.
