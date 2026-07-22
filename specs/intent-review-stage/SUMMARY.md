# intent-review-stage — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate — the diff will touch `templates/SUMMARY.template.md` (high-blast per PROJECT.md, caught by `ci-strict-gate.sh` via the `^templates/` pattern) and changes the workflow chain itself (orchestration: "redefine the workflow itself" → escalate); the direction is unambiguous — the user named the solution explicitly.
Flags: existing behavior, weak proof (skill prompt has no automated test)
Affects: templates/SUMMARY.template.md (5-field schema + new section), workflow chain (subagent-driven-development → finishing), skills/README.md handoff map, skills/feature-intake/SKILL.md (Step 6)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Verbatim request (2026-06-11): "once it's finished, is there any way to actually verify
that the result truly matches the original intent rather than just passing per the plan or the tests" →
agreed approach: "write the intake + plan for this intent-review stage as the next harness
improvement". Intent-review = the third oracle (intent), independent of the two existing oracles (the plan
oracle of spec-review, the runtime oracle of correctness-review); the reviewer is deliberately BLIND to PLAN.md, checking the diff against the
verbatim original request + the Success Criteria of design.md.

## What changed

Added a third oracle `/intent-review` to the review chain. The new skill
(`skills/intent-review/SKILL.md` + `intent-reviewer-prompt.md`) checks the final diff against the
verbatim original request, deliberately blind to PLAN.md; findings are classified as `gap`/`excess`/`drift` with routing
(fix-loop · escalate · report-only) + a residual gate. Capture the verbatim intent at intake
(`templates/SUMMARY.template.md` gains a `### Intent` section, and `feature-intake` Step 6 records it). Wired in as a
mandatory stage in `subagent-driven-development` after correctness-review (overview + digraph +
section + red flags + example + prompt list). Updated the inventory/handoff/chain in
`skills/README.md` + `CLAUDE.md`.

### Rationale

The gap was diagnosed in the 2026-06-11 session (the conversation following `docs/research/harness-review-improvements/research-harness-req-assessment.md`):
the current oracle chain validates code↔plan and code↔runtime but has no gate that validates
result↔intent after completion; if intake misunderstands the intent, the entire chain passes consistently yet is still wrong.
The hard gate (templates/ + workflow) was authorized directly by the user via the explicit named request
— this satisfies the "human narrowing scope" condition, so no further escalation is needed.

### Alternatives considered

- Phase-level UAT / TEST_MATRIX-from-design / PR-body intent map (items 2–4 of the analysis) —
  deferred: complementary rather than a replacement for the third oracle; to be done after this stage runs for real.
- Folding the intent check into correctness-review instead of a separate skill — rejected: mixing the two oracles
  (runtime vs intent) into one reviewer breaks their mutual blindness, and correctness-review is
  designed to be "bug-only".
- Skipping design.md and using only the verbatim request — half-rejected: the verbatim request is the
  primary oracle (always present after this change), while design.md's Success Criteria is the secondary oracle when it exists.

### Deviations

- Dogfood Finding #2 fix (gap) — committed `specs/intent-review-stage/` (PLAN.md + this SUMMARY)
  to the branch. The intake+plan deliverable existed on disk but was untracked (`??`); the intent
  reviewer caught it because the two existing oracles (spec/correctness) never inspect repo
  tracking state. Routed fix-loop → resolved in the Wave 3 commit.

### Intent Findings

<!-- Dogfood: /intent-review run standalone on this plan's own diff (BASE=f7d2d58, before wave 1).
     Oracle = the ### Intent block above. Reviewer was a fresh subagent (sonnet), blind to PLAN.md.
     First real smoke test of the stage — it reviewed its own diff. -->

- **#2 `gap` — FIXED.** `specs/intent-review-stage/` was untracked; the plan is the explicit
  co-deliverable of "write the intake + plan". Committed in Wave 3. (Real catch — exactly the class the
  third oracle exists for.)
- **#1 `drift` / #3 `excess` — advisory, resolved by authorization on record.** The reviewer read
  the intent as "write the intake + plan" and flagged shipping the full implementation as drift/excess.
  The full implementation **was authorized**: the user invoked `/executing-plans
  specs/intent-review-stage/PLAN.md` to execute this very plan — the reviewer is blind to that
  invocation (it only saw the plan-time `### Intent`). No code change needed; recorded here as the
  durable note the PR merger should see. Not escalated: authorization plainly exists.

  *Harness insight:* the intent oracle is captured at plan-authoring time ("write the plan") but
  the real intent at execution time is "execute the plan". The oracle can go stale between the two
  phases — see `### Harness-Delta`.

### Verify

<!-- Re-run by ci-strict-gate via verify_summary.py --check (diff touches templates/ → high-risk
     gate fires). Commands MUST be pipe-free: the parser splits table rows on `|`. -->

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Skill files + blind rule present (task 1.1) | `test -f skills/intent-review/SKILL.md && test -f skills/intent-review/intent-reviewer-prompt.md && grep -q "gap" skills/intent-review/SKILL.md && grep -qi "PLAN.md" skills/intent-review/intent-reviewer-prompt.md` | 0 | gap taxonomy + plan-blind rule |
| Intent captured at intake (task 1.2) | `grep -q "### Intent" templates/SUMMARY.template.md && grep -q "Intent" skills/feature-intake/SKILL.md` | 0 | oracle source |
| Stage wired ≥6 sites (task 2.1) | `test "$(grep -ci "intent[- ]review" skills/subagent-driven-development/SKILL.md)" -ge 6` | 0 | pipe-free count assert |
| Inventory/chain + doc-truth (task 2.2) | `bash scripts/lint-doc-truth.sh && grep -q "intent-review" skills/README.md && grep -q "intent-review" CLAUDE.md` | 0 | referenced paths exist |
| Ledger appended (task 3.1) | `grep -q "intent-review-stage" docs/harness-experimental/trust-metrics.md` | 0 | trust ledger row |

### Rollback

- `git revert <sha>` per-wave; it does not touch settings.json/hooks, so it reverts cleanly with git.

### Harness-Delta

- backlog (→ `/compound`) — **intent-oracle staleness.** The `### Intent` captured at intake is
  plan-authoring intent ("write the plan"); when execution is later authorized separately
  (`/executing-plans`), the oracle no longer reflects the live intent, so the intent reviewer
  flags the authorized implementation as drift/excess (dogfood #1/#3). Worth a follow-up: either
  re-capture/append intent at the execution handoff, or teach `/intent-review` to read the
  execution authorization (the `/executing-plans` invocation) alongside the intake `### Intent`.
- fix-direct — pre-existing drift noted (NOT fixed in this slug, out of scope): the comment atop
  `templates/SUMMARY.template.md` still says "five header fields" though there are six
  (Lane/Confidence/Reason/Flags/Affects/Input-type). Surfaced here per task 1.2; left for a
  dedicated touch so this diff stays surgical.
