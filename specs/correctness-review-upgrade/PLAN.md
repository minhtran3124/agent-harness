---
slug: correctness-review-upgrade
status: shipped
owner: Minh Tran
created: 2026-06-09
---

# Correctness Review Upgrade — close the compound loop at review time

> **For Claude:** REQUIRED SUB-SKILL: use `subagent-driven-development` (or `executing-plans`)
> to implement this plan task-by-task. This plan edits **skill prompt documents only** — no
> app code, no pytest. Every `<verify>` is a `grep`-based assertion that the required content
> landed; exit 0 = pass.

**Goal:** Upgrade the final adversarial correctness review in `subagent-driven-development` by
grafting the best mechanics from Boris `/code-review` and Every `/ce-code-review` onto our
existing infrastructure — without inventing new machinery.

**Design source:** conversation synthesis (Boris vs Every comparison) + `docs/research-compound-loop-closure.md`
(the compound loop is OPEN — `/compound` writes, only `/xia2` + `/brainstorming` pull back; the
review stage does not). No separate `design.md` was produced; this header + research doc are the spec.

## 1. Motivation

External AI reviewers added by the client catch real bugs our design/plan/review chain misses.
Root cause (diagnosed earlier): our per-task reviews are anchored to the plan as the oracle —
a bug that faithfully implements a flawed spec passes them. We already added a final adversarial
correctness reviewer (`correctness-reviewer-prompt.md`). This plan makes it *learn from our own
history* and *dispose of findings durably*, borrowing three mechanics:

- **C — Compound read-back** (from Every's always-on `ce-learnings-researcher`): the reviewer
  reads `docs/solutions/critical-patterns.md` + the `failure` track and turns each past finding
  into a mandatory check against the diff. This **closes the compound loop at review time** —
  today only `/xia2` and `/brainstorming` pull from `docs/solutions/`; the reviewer does not.
- **D — Two-dimensional classification** (from Every's `severity ⟂ autofix class`): every finding
  gets `severity P0–P3` **and** a `Rule 1–4` class from `.claude/rules/auto-correct-scope.md`.
  Reuses our existing autonomy taxonomy instead of a fresh one.
- **E — Residual work gate** (from Every's Residual Work Gate): a finding that is not fixed in the
  loop must land a durable record in `SUMMARY.md` / `ESCALATIONS.md`. Nothing silently disappears.

## 2. Non-goals

- **B — feature-intake flag → reviewer-persona mapping**: tracked as a SEPARATE follow-up. It
  touches `skills/feature-intake/` (high-blast) and deserves its own plan.
- **Find→score→threshold scorer + multi-lens fan-out** (Boris #1 / Every cross-persona agreement):
  out of scope here; revisit after C/D/E land.
- No changes to `executing-plans` or other execution skills in this plan (consistency pass is a
  later follow-up).
- No `settings.json` / hook / SessionStart changes (the research doc's "medium" loop-closure
  option is explicitly deferred — Rule 4 high-blast).

## 3. Success Criteria

1. `correctness-reviewer-prompt.md` instructs the reviewer to read `docs/solutions/INDEX.md` +
   `critical-patterns.md` + `failure`-track entries **when present**, and to skip gracefully when
   `docs/solutions/` is absent (it currently does not exist — scaffold-only).
2. The report format classifies each finding on two axes: `severity P0–P3` and `Rule 1–4`.
3. Findings not fixed in-loop are required to be written to `SUMMARY.md` / `ESCALATIONS.md`.
4. `SKILL.md`'s "Final Adversarial Correctness Review" section references C/D/E and routes the
   fix-loop by Rule class (Rule 1–3 → implementer auto-fix loop; Rule 4 → STOP + escalate).
5. No dangling references; both files cross-reference each other and the rules they cite exist.

## 4. Tasks

### Task 1 — C: compound read-back (graceful)

```xml
<task id="1">
  <files>skills/subagent-driven-development/correctness-reviewer-prompt.md</files>
  <action>Add a "## Prior-art checks (compound read-back)" section to the prompt, placed BEFORE
  the bug-class hunt. Instruct the reviewer to, IF `docs/solutions/` exists: read
  `docs/solutions/INDEX.md`, then `docs/solutions/critical-patterns.md` (regardless of domain),
  then up to 3 `problem_type: failure` / `bug` entries most relevant to the changed files — mirror
  the exact pull pattern `/xia2` uses (skills/xia2/SKILL.md:93-99). For each applicable past
  finding whose `applicable_when` matches the diff, verify the code does NOT reintroduce it and
  flag a finding if it does. MUST degrade gracefully: if `docs/solutions/` is missing or empty,
  state "no prior-art KB present — skipped" and proceed (the directory is scaffold-only today).
  Do not invent a new read pattern; reuse the established one.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && f=skills/subagent-driven-development/correctness-reviewer-prompt.md && grep -q "critical-patterns.md" "$f" && grep -qi "compound read-back" "$f" && grep -qi "failure" "$f" && grep -Eqi "if .*exist|missing or empty|scaffold|skip" "$f"</verify>
  <done>Prompt has a compound read-back section citing critical-patterns + failure track, mirrors the /xia2 pull pattern, and explicitly degrades when docs/solutions/ is absent.</done>
</task>
```

### Task 2 — D: two-dimensional finding classification

```xml
<task id="2">
  <files>skills/subagent-driven-development/correctness-reviewer-prompt.md</files>
  <action>Replace the existing single-axis severity (Critical/High/Medium) in the "Report format"
  section with TWO orthogonal axes per finding: (1) **Severity** P0 (data loss / auth bypass /
  crash on common path) · P1 (wrong result / crash on edge path) · P2 (degraded) · P3 (minor);
  (2) **Rule class** from `.claude/rules/auto-correct-scope.md`: Rule 1–3 = implementer auto-fixes
  in the loop (gated_auto), Rule 4 = STOP + escalate (manual/design needed). Each finding line must
  carry both `severity` and `Rule N` alongside the existing location / trigger / wrong-outcome /
  fix fields. State that severity drives urgency and Rule class drives who acts and how.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && f=skills/subagent-driven-development/correctness-reviewer-prompt.md && grep -q "P0" "$f" && grep -q "P3" "$f" && grep -q "Rule 4" "$f" && grep -q "auto-correct-scope.md" "$f"</verify>
  <done>Report format classifies every finding on severity P0–P3 AND Rule 1–4, citing auto-correct-scope.md.</done>
</task>
```

### Task 3 — E: residual work gate

```xml
<task id="3">
  <files>skills/subagent-driven-development/correctness-reviewer-prompt.md</files>
  <action>Add a "## Residual work gate" section: any finding NOT resolved in the fix-loop
  (e.g. a Rule 4 finding, or one deliberately deferred) MUST be recorded durably —
  `### Review Findings` in `specs/<slug>/SUMMARY.md` for deferred Rule 1–3, and a block in
  `specs/<slug>/ESCALATIONS.md` for Rule 4 (deny-on-no-response per orchestration.md). A finding
  may not silently disappear: the controller proceeds to finishing-a-development-branch only when
  every finding is either fixed (✅) or has a durable record. Cross-reference
  `.claude/rules/orchestration.md` (Residual / Escalation) and the existing SUMMARY `### Deviations`
  / `### Rollback` blocks.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && f=skills/subagent-driven-development/correctness-reviewer-prompt.md && grep -qi "residual work gate" "$f" && grep -q "ESCALATIONS.md" "$f" && grep -q "SUMMARY.md" "$f"</verify>
  <done>Prompt requires every unresolved finding to land in SUMMARY.md or ESCALATIONS.md before handoff; nothing is dropped.</done>
</task>
```

### Task 4 — Wire SKILL.md to C/D/E

```xml
<task id="4">
  <files>skills/subagent-driven-development/SKILL.md</files>
  <action>Update the "## Final Adversarial Correctness Review" section so it: (a) names the
  compound read-back as a first step (C); (b) describes the two-axis finding classification (D);
  (c) routes the fix-loop by Rule class — Rule 1–3 → implementer auto-fix → re-review loop, Rule 4
  → STOP + ESCALATIONS (E); (d) states the residual gate as the precondition for handing off to
  finishing-a-development-branch. Update the Example Workflow snippet's final-review block to show
  a finding tagged with both `P1` and `Rule 1`. Keep edits surgical — do not rewrite unrelated
  sections.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && f=skills/subagent-driven-development/SKILL.md && grep -qi "compound read-back" "$f" && grep -q "Rule 4" "$f" && grep -qi "residual" "$f" && grep -q "ESCALATIONS" "$f"</verify>
  <done>SKILL.md's final-review section reflects C/D/E and the Rule-classed fix-loop; example shows a 2-axis finding.</done>
</task>
```

### Task 5 — Consistency lint

```xml
<task id="5">
  <files>skills/subagent-driven-development/SKILL.md, skills/subagent-driven-development/correctness-reviewer-prompt.md</files>
  <action>Verify the two files cross-reference correctly and every cited rule path exists on disk.
  No edits expected unless the lint fails; if it fails, fix the dangling reference.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && grep -q "correctness-reviewer-prompt.md" skills/subagent-driven-development/SKILL.md && test -f .claude/rules/auto-correct-scope.md && test -f .claude/rules/orchestration.md</verify>
  <done>SKILL.md references the prompt template; cited rule files exist. No dangling paths.</done>
</task>
```

## 5. Risks

- **Two skill copies.** Source lives in `skills/`; a deployed mirror exists under `.claude/skills/`
  (see commit `43ec394` "preserve foreign skills on deploy/re-sync"). Edits here target the
  `skills/` source. After merge, run the project's deploy/re-sync so `.claude/skills/` picks up the
  change — otherwise the *running* copy is stale. Flag to user at handoff.
- **`docs/solutions/` is empty today.** Task C must be inert (graceful skip) until `/compound` or
  `/bootstrap-xia2` populates it — verified by the `done` criterion, not just code.
- **Prose verify is shallow.** `grep` proves the content landed, not that the wording is good. The
  spec-compliance + code-quality reviewer subagents (always-on in this skill) cover quality.

## 6. Status Log

- 2026-06-09 — Plan drafted (status: proposed). Awaiting execution-mode choice.
- 2026-06-09 — Executed via subagent-driven-development on branch `feat/correctness-review-upgrade`.
  Tasks 1–3 (C/D/E) → `correctness-reviewer-prompt.md`; spec/consistency review found 2 issues (Fix-loop
  contradiction, xia2 citation), fixed in-loop. Tasks 4–5 → `SKILL.md` wired + lint. All grep verifies exit 0.
  Final whole-diff coherence pass: clean (runtime-bug hunt N/A — markdown-only diff).
- 2026-06-09 — shipped via `feat/correctness-review-upgrade` (PR #6). Commits 41bb667, 768acab.
