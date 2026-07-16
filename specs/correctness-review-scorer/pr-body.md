## Summary

Adds a **Boris-style find→score→threshold confidence filter** to the final adversarial
correctness review in `subagent-driven-development`. The reviewer (FIND) is deliberately
high-recall; this inserts a precision filter before any fix work.

- **New `correctness-scorer-prompt.md`** — a cheap-model, independent-context SCORE pass that
  rates each candidate finding **0–100** against a verbatim rubric (0/25/50/75/100), scoring `0`
  for pre-existing / CI-or-hook-catchable / unmodified-line findings.
- **FIND** (`correctness-reviewer-prompt.md`) now labels its output as *candidates* and is told to
  **stay high-recall** — precision is enforced downstream.
- **`SKILL.md`** documents the pipeline order **FIND → SCORE → THRESHOLD(≥80) → D → E**; findings
  `<80` are recorded as `advisory` in `SUMMARY.md` (not silently dropped). Threshold is adjustable.

**Design decision:** Boris independent-scorer chosen over Every cross-persona agreement — we have a
single finder; agreement needs ≥2 lenses (deferred until a multi-lens fan-out exists).

## Builds on PR #6 (merged)

The FIND stage (PR #6) is now merged into `main`, so this PR's diff is clean — just the three
scorer files:
- `skills/subagent-driven-development/correctness-scorer-prompt.md` (new)
- `skills/subagent-driven-development/correctness-reviewer-prompt.md` (Confidence-scoring note)
- `skills/subagent-driven-development/SKILL.md` (pipeline wiring)

## Verification

Markdown skill-doc change only (0 `.py`). Verified via grep assertions (Tasks 1–4, all exit 0) +
a fresh-context review confirming the D (severity×Rule) and E (residual gate) content was preserved
and correctly sequenced after the new SCORE stage.

## Follow-ups (deferred)

- Cross-persona agreement as a confidence signal (needs multi-lens fan-out).
- **B** — `feature-intake` flag → reviewer-persona mapping.
- After merge: re-sync deployed `.claude/skills/` + update `harness-skills-deploy` guide/deck.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
