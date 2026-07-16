---
name: intent-review
description: Run one review that checks a finished diff against the user's ORIGINAL request verbatim — the third oracle. Deliberately blind to PLAN.md, it catches "passed the plan, passed the tests, but not what the user asked for." Findings classify as gap / excess / drift with explicit routing (fix-loop · escalate · report-only) and a residual gate. Invokable standalone on any diff that has an intent statement, and called by subagent-driven-development as its last pass before shipping. Not a bug hunt (use /correctness-review) and not a style pass (use /code-review).
---

# Intent Review

Run **one** review that compares a finished diff against the **original request, verbatim**, and
route every surviving finding to a fix, an escalation, or a durable record. This is the **third
oracle** in the review chain — independent of, and blind to, the plan.

**Why this stage exists.** The chain already has two oracles, and both can pass while the result
is still wrong:

- **spec review** asks *"does it match PLAN.md?"* — but the plan itself can mis-encode the intent.
- **correctness review** asks *"does it run correctly?"* (blind to the plan) — but correct code
  can still build the wrong thing.

Neither asks *"would the person who asked for this recognize it as what they asked for?"* When
intake or design misread the intent, every downstream gate passes **consistently** and the result
is still wrong (Goodhart: the `<verify>` commands are written by the plan author, so they only
measure what the plan thought mattered). The single human gate after implementation is the PR
merge — but nothing gives the merger an intent artifact to check against. This stage is that
check, run by a fresh blind reviewer before hand-off.

**Three oracles, mutually blind:**

| Oracle | Skill | Asks | Blind to |
|---|---|---|---|
| PLAN | spec review (per-task) | does it match the spec? | — |
| runtime | `/correctness-review` | does it run correctly? | the plan |
| intent | `/intent-review` (this) | is it what the user asked for? | the plan |

`correctness-review` is blind to the plan to catch **bugs**; `intent-review` is blind to the plan
to catch **drift** — the symmetry is deliberate. A reviewer that can see PLAN.md will anchor on it
and re-confirm the same possible misreading instead of going back to the source request.

**Two entry points, one pipeline:**

- **Standalone** — `/intent-review` on any diff that has an intent statement (a `### Intent` block
  in `specs/<slug>/SUMMARY.md`, or intent the user provides inline). Use it on a branch before a
  PR, or on any range you name.
- **In-flow** — `subagent-driven-development` calls this after `/correctness-review` passes and
  before `finishing-a-development-branch`.

## When to Use

- After correctness review, before opening a PR or merging — a final check that the change is what
  was actually requested.
- Standalone on any diff when you have the original request and want intent coverage decoupled from
  the full workflow.
- Automatically, as the last gate inside `subagent-driven-development` (no manual call needed).

Not a bug hunt — that is `/correctness-review`. Not a style/maintainability pass — that is
`/code-review` or the per-task quality reviewer. This skill checks **intent fidelity only**.

## 1. Oracle input — establish the intent, do NOT infer it

Before anything else, assemble the oracle. The intent is the **user's original request, verbatim**:

1. **Primary oracle** — read the `### Intent` block from `specs/<slug>/SUMMARY.md`. This is the
   request captured verbatim at intake (`feature-intake` Step 6). It is the source of truth.
2. **Secondary oracle (if it exists)** — the **Success Criteria** of `specs/<slug>/design.md`.
   Use it to sharpen the intent, never to replace the verbatim request.

**If both are absent → STOP.** Ask the user to provide the original request. Do **not** reconstruct
intent from PLAN.md, research-brief.md, or the diff itself — those are downstream of the intent and
inherit any misreading. Inferring intent from the plan defeats the entire purpose of a third oracle.

**If the two oracles conflict** (the verbatim request and design.md Success Criteria describe
different things): the **verbatim request wins**, and the conflict is itself a `drift` finding that
must escalate — it signals the design drifted from intent at the very start.

## 2. Blind rule — the reviewer must not read the plan

The dispatched reviewer is **forbidden** from reading `specs/<slug>/PLAN.md` or
`specs/<slug>/research-brief.md`. It receives only the intent oracle + the diff + the touched-file
list. Reason (state it in the dispatch): symmetric with correctness-review's plan-blindness — a
reviewer that sees the plan anchors on it and re-confirms the plan's possible misreading of intent,
which is exactly the failure this stage exists to catch.

## 3. Determine the diff range

The reviewer needs a `BASE_SHA..HEAD_SHA` range and the list of touched files:

- **In-flow:** `BASE` = commit before task 1, `HEAD` = current commit after all tasks.
- **Standalone, branch vs main:** `BASE = git merge-base main HEAD`, `HEAD = HEAD`.
- **Standalone, explicit range / PR:** the user names `BASE`/`HEAD` or a PR.

## 4. Dispatch — one fresh blind reviewer

Dispatch **one** reviewer subagent with fresh context, using `./intent-reviewer-prompt.md`. It
receives: the intent oracle + the full diff (`git diff BASE..HEAD`) + the list of touched files.

**Use a different model than the implementer** (ensemble diversity, same discipline as
correctness-review). The reviewer must quote the **verbatim intent sentence** each finding violates
— this is the guardrail against a reviewer inventing intent the user never expressed.

## 5. Taxonomy + routing

Every finding is one of three classes. Routing differs by class:

- **`gap`** — the intent asked for something that was **not shipped**.
  - *Clear and in scope* → implementer **fix-loop** → re-review until resolved.
  - *Ambiguous* (more than one reasonable reading) → `specs/<slug>/ESCALATIONS.md`; a human
    narrows scope. Do not guess.
- **`drift`** — the intent was shipped, but in a way that **differs from how the intent described it**.
  - *Behaviorally equivalent* (different surface, same outcome the user wanted) → record as an
    **advisory** with an explanation; do not block.
  - *Behaviorally different* → route like a `gap` (fix-loop if clear, escalate if ambiguous).
- **`excess`** — something was shipped that **nobody asked for** (scope beyond the intent).
  - **Report-only.** Do **not** auto-remove it: deleting shipped functionality is a Rule-4 change
    (`.claude/rules/auto-correct-scope.md` — "removing existing functionality"). Record it; removal
    needs human approval.

## 6. Residual gate — every finding fixed or durably recorded

Before reporting done (in-flow: before handing off to `finishing-a-development-branch`), every
finding must be in one of two states:

- **fixed** — ✅ with a commit sha (gap/drift routed through the fix-loop), **or**
- **durably recorded** — in `specs/<slug>/SUMMARY.md` under `### Intent Findings` (advisory drift,
  report-only excess, deferred gap), or in `specs/<slug>/ESCALATIONS.md` (ambiguous gap/drift,
  intent↔design conflict — `ESCALATIONS.md` is deny-on-no-response).

A finding with **neither** is a hard block — do not report success, do not hand off. In standalone
use with no slug, surface every finding inline as advisory instead.

## Relationship to other review skills

- **spec review (per-task, inside `subagent-driven-development`):** oracle = PLAN.md. Asks "does it
  match the spec?" This skill ignores the plan and goes back to the original request.
- **`/correctness-review`:** oracle = runtime, blind to the plan. Hunts bugs. This skill is blind to
  the plan for the *same reason* but hunts intent drift, not bugs — the two are complementary and
  never merged (mixing runtime and intent into one reviewer destroys the mutual blindness).
- **`/code-review` (global):** generic correctness + reuse/simplification cleanup. Not an intent pass.
- **`subagent-driven-development`:** calls this skill as its last gate, after correctness-review.
  Invoking `/intent-review` standalone runs the exact same pipeline without the rest of the workflow.

## Intentional differences from the correctness-review template

This skill follows the correctness-review shape (thin skill + reviewer prompt + two entry points +
residual gate) but **deliberately omits** its SCORE / THRESHOLD stage and its scorer prompt. Intent
findings route by taxonomy (`gap` / `excess` / `drift`), not by a 0–100 score — there is no
`intent-scorer-prompt.md`. Do not clone the score/threshold machinery here.

## Prompt Templates

- `./intent-reviewer-prompt.md` — dispatch the blind intent reviewer (once, whole diff).
