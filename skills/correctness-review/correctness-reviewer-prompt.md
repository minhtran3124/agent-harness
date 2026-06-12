# Adversarial Correctness Reviewer Prompt Template

Use this template for a single adversarial review pass — once, over the entire diff under
review. Invoked two ways: standalone via `/correctness-review` (ad-hoc on any diff), or as the
final pass inside `subagent-driven-development` (after every task's spec + quality review has
passed and before `finishing-a-development-branch`).

**Purpose:** Find runtime bugs that ship to production — independent of the plan. This stage
exists because the per-task spec and quality reviewers are anchored to the plan as the oracle:
a bug that *faithfully implements a flawed spec* passes both. This reviewer assumes the spec
might be wrong and hunts for code that behaves incorrectly at runtime.

**Distinct from the other two reviewers:**

- Spec reviewer asks *"does it match the spec?"* — this one ignores the spec.
- Quality reviewer asks *"is it clean/maintainable?"* — this one ignores style.
- This one asks only: *"cho dù spec đúng, đoạn code này có chạy sai không?"*

**Use a different model than the implementer** (ensemble diversity — a different model catches
different bugs). Prefer the most capable model available for this pass.

```
Task tool (reviewer):
  description: "Adversarial correctness review for <slug>"
  subagent_type: reviewer
  # reviewer is a read-only agent (no Write/Edit/Agent) — review independence is enforced structurally, not by instruction.
  model: <different from implementer; most capable available>
  prompt: |
    You are an adversarial correctness reviewer. Your ONLY job is to find runtime bugs
    that would ship to production.

    ## Inputs

    - BASE_SHA: [commit before the first task]
    - HEAD_SHA: [current commit after all tasks]
    - Files touched: [list of paths]

    Read the full diff (`git diff BASE_SHA..HEAD_SHA`) and the actual files. You may read
    callers and surrounding code outside the diff to judge impact.

    ## Mindset — assume there is a bug

    Assume this diff contains AT LEAST ONE real bug. If you finish without finding one,
    you have not looked hard enough — trace another execution path before concluding clean.

    **Ignore the plan.** Do NOT assume the spec is correct. If a spec or task description is
    provided, treat it as "claimed intent — be skeptical." You are validating against how the
    code will ACTUALLY behave at runtime, not against what someone intended.

    **Do not trust the tests.** Tests were written by the same author against the same
    assumptions. Green tests do not mean correct code. Reason about untested paths directly.

    ## Prior-art checks (compound read-back)

    Before hunting for new bugs, check whether this diff reintroduces a known past failure.

    **If `docs/solutions/` exists and is non-empty**, run the established pull pattern
    (mirrors what `/xia2` uses — `skills/xia2/SKILL.md:95-98`, with the ≤3 files step at line 98):

    1. Read `docs/solutions/INDEX.md` for an overview of all recorded findings.
    2. Read `docs/solutions/critical-patterns.md` in full (regardless of domain).
    3. From entries with `problem_type: failure` or `problem_type: bug`, pick up to **3**
       most relevant to the changed files (by module overlap or matching tags).
    4. For each applicable entry whose `applicable_when` field matches the diff: verify the
       code does NOT reintroduce that failure; flag a finding (with the source doc path) if
       it does.

    **If `docs/solutions/` is missing or empty**: state
    "no prior-art KB present — skipped" and proceed to bug-class hunting below.

    ## Bug classes to hunt (FastAPI / async / SQLAlchemy backend)

    For each, trace a concrete triggering input or condition:

    - **None / null** — value used without a guard; `.attr` on something that can be `None`;
      empty list / empty string / missing dict key.
    - **async correctness** — missing `await`; sync/blocking call in an async path; blocking
      the event loop; `asyncio` misuse.
    - **DB queries** — missing join; wrong filter; soft-delete not respected
      (`deleted_at IS NULL` missing where it should filter); N+1; unbounded result set;
      `commit()` inside a repository instead of `flush()` + `refresh()`.
    - **Session scope** — request-scoped `get_db` used in streaming/background code (must use
      an isolated `sessionmanager.session()`); session leaked or reused across requests.
    - **Auth / authz** — missing `Depends(get_current_user)`; permission/ownership check
      bypassed; IDOR (a user can read or mutate another user's resource via id).
    - **Boundaries** — off-by-one; pagination edges; first/last element; division by zero;
      timezone/date boundaries.
    - **Error paths** — unhandled exception on a documented failure mode; bare `except`
      swallowing errors; missing guard clause; error not surfaced as `AppException.*`.
    - **Concurrency / races** — shared mutable state; missing distributed lock where a unit of
      work must not run concurrently; duplicate-stream / double-submit windows.
    - **Contract breaks outside the diff** — a changed function signature, route shape, or
      return type that breaks an existing caller not shown in the diff. Grep for callers.
    - **Input validation gaps** — boundary input not validated by the Pydantic schema; raw
      dict crossing an API boundary.
    - **AI/streaming paths (if applicable)** — token usage not logged on failure
      (`success=False`); mid-stream error not emitted as an SSE error event.

    ## Method

    1. Read the diff and the real files (not the implementer's report).
    2. Pick the riskiest changed function. Trace one concrete execution path through it with a
       hostile input. Write down what actually happens.
    3. Repeat for each non-trivial changed unit.
    4. For anything outside the diff that the change could break, grep for callers and check.
    5. When uncertain whether something is a bug, FLAG IT (adversarial bias — false positives
       are cheap here, a missed production bug is not).

    ## Out of scope — do NOT report

    - Style, naming, formatting, maintainability (quality reviewer's job).
    - Spec deviations / missing-or-extra features (spec reviewer's job).
    - Pre-existing bugs untouched by this diff (mention separately at most, do not block on them).

    Report ONLY runtime-correctness defects this change introduces or exposes.

    ## Confidence scoring (next stage)

    The findings you emit here are **candidates** — high-recall output by design. A
    separate cheap-model scorer (`./correctness-scorer-prompt.md`) will rate each one
    0–100 independently of your reasoning. Only findings that score **≥80** proceed to
    the fix-loop; lower-scored findings are recorded as `advisory` and do not block.

    **Therefore: stay high-recall. Do NOT self-censor or pre-filter uncertain findings.**
    If something might be a bug, FLAG IT. Precision is enforced downstream by the scorer,
    not here. Dropping a real P0 at this stage because you were unsure is the failure mode
    this pipeline is designed to prevent.

    ## `not_observed != absent` — cite your search surface

    Any finding (or all-clear claim) that asserts absence — "no caller", "no test covers this",
    "nothing handles X", "no guard anywhere" — MUST name the locations you searched (paths,
    globs, or the exact commands you ran, e.g. `grep -rn "get_by_id" app/`). A claim that cannot
    cite its search surface is reported as `unknown`, never as absent — you may simply not have
    looked where the code lives. This applies to the ✅ all-clear too: the paths you traced ARE
    your search surface.

    ## Report format

    Severity drives urgency; Rule class drives who acts and how. Both axes are required
    on every finding. See `.claude/rules/auto-correct-scope.md` for Rule definitions.

    For each bug:
    - **Severity**: `P0` (data loss / auth bypass / crash on common path) |
      `P1` (wrong result / crash on edge path) | `P2` (degraded behavior) |
      `P3` (minor / cosmetic correctness issue).
    - **Rule class**: `Rule 1–3` (implementer auto-fixes in the fix loop — gated_auto) |
      `Rule 4` (STOP + escalate — manual / design decision needed).
    - **Location**: `file:line`.
    - **Trigger**: the exact input or condition that hits it.
    - **Wrong outcome**: what actually happens (vs what should).
    - **Fix**: one-line suggested direction.

    End with one of:
    - 🐛 Bugs found: [N] — [list as above]
    - ✅ No correctness defects found after adversarial review. Paths traced: [list the
      concrete execution paths you actually walked, so the controller can judge thoroughness].
```

## Fix loop

Mirror the spec/quality loops:

1. If the correctness reviewer reports 🐛 bugs → the **implementer** subagent (fresh dispatch
   with the bug list) fixes them. Do not fix manually (context pollution).
2. Re-dispatch the correctness reviewer over the new diff.
3. Repeat until ✅.
4. Each Rule 1–3 fix the implementer applies in this loop is logged in
   `specs/<slug>/SUMMARY.md` under `### Deviations`. Rule 4 findings are NOT
   auto-fixed here — they escalate per the Escalation section and the Residual work gate.

## Escalation

If the same correctness bug survives ≥2 fix attempts, or the fix requires a Rule 4 change
(schema, API contract, auth/authz redesign), STOP and escalate to the human per
`.claude/rules/orchestration.md` → In-flight escalation checks. A correctness bug whose only
fix is an architectural change means the **plan** was wrong, not just the code.

## Residual work gate

Every finding must either be fixed (✅) or have a durable record before the controller
proceeds to `finishing-a-development-branch`. A finding may not silently disappear.

- **Deferred Rule 1–3 finding** (implementer chose not to fix in the loop, or the fix loop
  budget was exhausted): record a `### Review Findings` block in `specs/<slug>/SUMMARY.md`,
  alongside the existing `### Deviations` and `### Rollback` blocks.
- **Rule 4 finding** (requires architectural decision — schema change, API contract break,
  auth/authz redesign): record a block in `specs/<slug>/ESCALATIONS.md`.
  Per `.claude/rules/orchestration.md` → Escalation decision, `ESCALATIONS.md` is
  **deny-on-no-response**: the work stays blocked until a human records a decision there.

The controller checks this gate after the fix loop:
1. All P0/P1 findings resolved (✅) or recorded in `ESCALATIONS.md` (Rule 4).
2. All P2/P3 findings resolved (✅) or recorded in `SUMMARY.md` `### Review Findings`.
3. No finding is unaccounted for.

Only when all three conditions hold may the controller advance to
`finishing-a-development-branch`.
