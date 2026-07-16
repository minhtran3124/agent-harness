---
slug: correctness-review-scorer
status: shipped
owner: Minh Tran
created: 2026-06-09
---

# Confidence-scored correctness review (Boris-style find→score→threshold)

> **For Claude:** REQUIRED SUB-SKILL: use `subagent-driven-development` (or `executing-plans`)
> to implement this plan task-by-task. This plan edits **skill prompt documents only** — no
> app code, no pytest. Every `<verify>` is a `grep`-based assertion; exit 0 = pass.

**Goal:** Insert a confidence **score → threshold** stage between the adversarial correctness
reviewer (FIND) and the D/E classification + fix-loop, so high-recall findings are filtered for
precision before any fix work — the missing layer that keeps an adversarial reviewer from
flooding the implementer with false positives.

**Design source:** conversation analysis (Boris `/code-review` vs Every `/ce-code-review`).
No separate `design.md` / `research-brief.md` — the design is fully specified below; this is a
self-contained prose change to an existing, shipped skill.

## 1. Motivation

The correctness reviewer (shipped in PR #6) is deliberately **high-recall**: "when uncertain,
FLAG IT." Today every flagged finding flows straight into the fix-loop (D) and residual gate (E)
— there is **no precision filter**, so the implementer can end up chasing false positives. Boris's
`/code-review` solves exactly this by **separating generation from filtering**: independent
finders emit candidates, then a *separate* cheap-model scorer rates each finding 0–100 against a
verbatim rubric, and everything below a threshold (Boris uses 80) is dropped.

This plan adds that score→threshold layer. The reviewer stays high-recall; precision is enforced
downstream. Result: the adversarial bias is preserved without the noise tax.

## 2. Non-goals

- **Cross-persona agreement** (Every's confidence signal — ≥2 independent lenses agreeing). We
  have a *single* correctness reviewer, so agreement has nothing to agree across. It is the
  natural follow-up **after** a multi-lens fan-out exists; recorded as a Decision alternative
  (§Decision) and deferred. This plan implements the **independent-scorer** variant only.
- **Multi-lens / parallel finders** — separate, larger change; out of scope.
- **B — feature-intake flag → reviewer-persona mapping** — still deferred (touches
  `skills/feature-intake/`, high-blast).
- No `settings.json` / hook / model-config changes.

## 3. Decision — independent scorer vs cross-persona agreement

**Chosen: Boris-style independent scorer.** Rationale: our FIND stage is one reviewer, not a
panel; agreement-based confidence requires ≥2 lenses that don't exist yet. An independent scorer
works with the architecture we have today and is the cheaper, simpler precision mechanism.

**Alternative (deferred): cross-persona agreement.** Promote confidence when ≥2 independent
lenses flag the same finding. Strictly better at catching scorer blind spots, but presupposes the
multi-lens fan-out (a bigger change). Revisit once that exists; the two can compose (agreement
*then* scorer).

## 4. Success Criteria

1. A new `correctness-scorer-prompt.md` exists: scores each candidate finding **0–100** against a
   **verbatim rubric**, runs on a **cheap model**, in **independent context** (sees the claim +
   the diff, NOT the finder's reasoning).
2. The rubric anchors are explicit (0 / 25 / 50 / 75 / 100) and adapted to our context — a finding
   scores low if it is pre-existing, on an unmodified line, or already caught by CI/hooks
   (`ruff`, `commit-quality-gate`, `risk-corroboration`).
3. A **threshold of 80** filters findings: only `≥80` enter the D (severity×Rule) classification
   and the fix-loop. The threshold value is stated once and called out as adjustable.
4. Dropped findings (`<80`) are **not silently discarded** — they are logged as `advisory` in
   `SUMMARY.md` (consistent with E's "nothing silently dropped" principle), not escalated.
5. `correctness-reviewer-prompt.md` (FIND) explicitly labels its output as *candidate findings for
   scoring* and is told to **stay high-recall / not self-censor** (the scorer handles precision).
6. `SKILL.md`'s "Final Adversarial Correctness Review" documents the full pipeline order:
   FIND → SCORE → THRESHOLD(≥80) → D classify → E residual/fix-loop.

## 5. Tasks

### Task 1 — Create the scorer prompt template

```xml
<task id="1">
  <files>skills/subagent-driven-development/correctness-scorer-prompt.md</files>
  <action>Create a new prompt template for the SCORE stage. It dispatches a CHEAP-model agent in
  INDEPENDENT context: input is one candidate finding (claim + file:line) plus the diff/files —
  NOT the finder's reasoning. The agent scores the finding 0–100 with this verbatim rubric:
  0 = false positive / pre-existing / not on a changed line; 25 = maybe real, unverified;
  50 = real but minor or rare; 75 = highly confident, real and will hit in practice;
  100 = certain, confirmed by the code. Instruct: score 0 if a linter/typechecker/CI or an
  existing hook (`ruff-on-edit`, `commit-quality-gate`, `risk-corroboration`) would already catch
  it, or if it is on a line the diff did not modify. Return `score` (0–100) + a one-line
  justification per finding. Mirror the structure/tone of the sibling `*-prompt.md` templates.
  State the default threshold is 80 (adjustable) and that scoring is independent of severity.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && f=skills/subagent-driven-development/correctness-scorer-prompt.md && test -f "$f" && grep -q "0–100\|0-100" "$f" && grep -q "80" "$f" && grep -Eqi "cheap|fast|haiku" "$f" && grep -Eqi "independent" "$f" && grep -q "commit-quality-gate" "$f"</verify>
  <done>Scorer template exists: 0–100 rubric, cheap model, independent context, threshold 80, CI/hook-aware.</done>
</task>
```

### Task 2 — FIND stage: label output as candidates, stay high-recall

```xml
<task id="2">
  <files>skills/subagent-driven-development/correctness-reviewer-prompt.md</files>
  <action>Add a short "## Confidence scoring (next stage)" note near the Report format: the
  findings this reviewer emits are CANDIDATES that a separate cheap-model scorer
  (`./correctness-scorer-prompt.md`) will rate 0–100; only `≥80` proceed to the fix-loop. Tell
  the finder to therefore STAY HIGH-RECALL — do not self-censor or pre-filter uncertain findings,
  because precision is enforced downstream. Do not change the existing bug-class hunt or the
  adversarial mindset. Surgical addition only.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && f=skills/subagent-driven-development/correctness-reviewer-prompt.md && grep -qi "confidence scoring" "$f" && grep -q "correctness-scorer-prompt.md" "$f" && grep -Eqi "high.recall|do not self-censor|candidate" "$f"</verify>
  <done>FIND prompt points at the scorer, labels findings as candidates, reinforces high recall.</done>
</task>
```

### Task 3 — Wire SKILL.md: FIND → SCORE → THRESHOLD → D → E

```xml
<task id="3">
  <files>skills/subagent-driven-development/SKILL.md</files>
  <action>In the "## Final Adversarial Correctness Review" section, insert the SCORE→THRESHOLD
  stage BETWEEN the find step and the two-axis classification (D). Document the pipeline order:
  FIND (high-recall candidates) → SCORE (cheap model, `./correctness-scorer-prompt.md`, each
  finding 0–100) → THRESHOLD (drop `<80`) → D (severity×Rule) → E (residual gate + fix-loop).
  State that dropped (`<80`) findings are recorded as `advisory` in `SUMMARY.md` (not escalated,
  not silently dropped). Note the threshold (80) is adjustable. Add the scorer template to the
  "Prompt Templates" list. Keep edits surgical.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && f=skills/subagent-driven-development/SKILL.md && grep -q "correctness-scorer-prompt.md" "$f" && grep -Eqi "score|0–100|0-100" "$f" && grep -q "80" "$f" && grep -qi "advisory" "$f"</verify>
  <done>SKILL.md documents FIND→SCORE→THRESHOLD→D→E and lists the scorer template; advisory handling stated.</done>
</task>
```

### Task 4 — Consistency lint

```xml
<task id="4">
  <files>skills/subagent-driven-development/SKILL.md, skills/subagent-driven-development/correctness-reviewer-prompt.md, skills/subagent-driven-development/correctness-scorer-prompt.md</files>
  <action>Verify cross-references resolve and the threshold/order story is consistent across all
  three files. No edits expected unless the lint fails.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && d=skills/subagent-driven-development && grep -q "correctness-scorer-prompt.md" "$d/SKILL.md" && grep -q "correctness-scorer-prompt.md" "$d/correctness-reviewer-prompt.md" && test -f "$d/correctness-scorer-prompt.md"</verify>
  <done>All three files cross-reference the scorer; no dangling paths.</done>
</task>
```

## 6. Risks

- **Threshold calibration.** 80 is Boris's number for a PR bot; our context (pre-merge gate,
  recall-first) may want lower. Stated as a starting point + adjustable — tune after first real use.
- **Cost.** SCORE adds one cheap-model call per candidate finding. Acceptable (cheap model, only
  when the reviewer produced findings), but note it in SKILL.md.
- **Depends on PR #6.** The correctness reviewer (FIND) must exist. PR #6 is shipped but not yet
  merged — branch this work off `feat/correctness-review-upgrade` (stacked) or off `main` after #6
  merges. Decide at execution time.
- **Two skill copies + deploy site.** After merge: re-sync the deployed `.claude/skills/` copy, and
  update the `harness-skills-deploy` guide/deck (a new SCORE stage in the pipeline description) —
  same follow-through as PR #6.

## 7. Status Log

- 2026-06-09 — Plan drafted (status: proposed). Awaiting execution-mode choice.
- 2026-06-09 — Executed via subagent-driven-development on `feat/correctness-review-scorer`
  (stacked on `feat/correctness-review-upgrade`/PR #6). Tasks 1–3 in one implementer; fresh-context
  review confirmed D/E content preserved + consistency. Task 4 lint OK. All grep verifies exit 0.
  Commit `255ec70`.
- 2026-06-09 — shipped via `feat/correctness-review-scorer` (PR #7, base main, stacked on PR #6).
