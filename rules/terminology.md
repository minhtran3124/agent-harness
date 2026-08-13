---
paths:
  - "specs/**/PLAN.md"
  - "specs/**/research-brief.md"
  - "specs/**/SUMMARY.md"
---

# Terminology Rule

Controlled-language rules for prose that an agent **executes**, adapted from ASD-STE100
writing rules. The STE Dictionary is deliberately **not** adopted — its ~1,700-word allow-list
would forbid this project's own vocabulary (`worktree`, `lane`, `gate`, `blast radius`).

Every rule below is labelled with the evidence that justifies it. A rule with no measured
effect is advisory and **must not** be mechanised into a gate: see
`specs/ste-terminology-evidence/DECISION.md` for the 75-trial A/B record.

<!-- lint:scope -->
| Target | §1 Terms | §2 Modality | §3 Acceptance | Enforcement |
| --- | --- | --- | --- | --- |
| `PLAN.md` `Verify:` / `Done:` | advisory | advisory | **required** | lintable |
| `PLAN.md` `Action:` | advisory | advisory | **required** | lintable |
| `SUMMARY.md` `### Verify` rows | advisory | — | **required** | lintable |
| `SUMMARY.md` Rationale / Alternatives | advisory | — | — | none |
| `design.md`, `research-brief.md` | advisory | — | **excluded** | none |
| `SUMMARY.md` `### Intent` | **excluded** | **excluded** | **excluded** | never |
<!-- /lint:scope -->

## §3 Acceptance criteria must be machine-decidable — REQUIRED

**This is the only rule in this file with a measured behavioural effect.** An acceptance
criterion that a reader cannot decide by running something is not a criterion.

Do not write, in a `Verify:`, `Done:`, or `### Verify` field: `correctly`, `properly`,
`as expected`, `works`, `is correct`, `looks right`, `appropriate`, `reasonable`.

State instead the observable: the exact string, count, exit code, or ordering.

```
BAD   Verify: the report is correct.
GOOD  Verify: the id column reads 1,2,3,4 top to bottom and no field is empty.
```

**Measured:** with `is it correct?` as the criterion, reviewers accepted a defective
artifact in 7 of 8 runs and two of them asserted a property that was false in the file.
With the observable stated, 8 of 8 rejected it. Two models, `p = 0.0014`.

## §2 Modality — advisory, and not a compliance lever

`must` = required; skipping it is a defect. `should` = recommended; record the reason for
skipping in the artifact. Define the pair once here and use it consistently.

**Do not rely on `must` to force a step.** Measured: against a competing constraint,
`should` produced compliance in 0 of 10 runs and `must` in only 4 of 10 (`p = 0.087`) — the
other 6 stopped and escalated instead. Escalating on a real conflict is the behaviour this
harness wants, so the finding is not a defect: it means **a step that is genuinely mandatory
belongs in a gate, not in a word**. With no competing constraint both words scored 5 of 5,
so the distinction carries no weight in the easy case either.

## §1 One concept, one word — advisory only

Prefer one verb per concept so a reader is not invited to infer a rigor difference that does
not exist: `verify` (produce re-runnable proof) vs `check` (read state); `block` (a hook
denies) vs `stop` (an agent halts itself); `write` (a file) vs `create` (a branch or
worktree); `subagent` (never `sub-agent`).

`run` and `session` are **two different concepts, not synonyms**: a *run* is one workflow
pass from intake to merge; a *session* is one Claude Code process (`SessionStart` /
`SessionEnd`, `session-knowledge.sh`). One run spans several sessions — that is what
`subagent-driven-development resume <slug>` exists for. Never normalise one into the other.

**Measured: no effect.** Mixing `check` / `verify` / `confirm` / `validate` scored 40 of 40
assertions correct; using `verify` for all four scored 36 of 36, across two difficulty levels.
Keep this section for human readability. Do not build a linter on it.

## Hard exclusions

1. **`SUMMARY.md` `### Intent` — never touched, by any rule, hardcoded.** It holds the
   user's request verbatim and is the oracle for `intent-review`, the reviewer that is blind
   to `PLAN.md`. Rewriting one word there corrupts an independent review layer. This must not
   be exposed as configuration.
2. **§3 does not apply to `design.md` or `research-brief.md`.** Hedging is the content there,
   and `rules/behavior.md` §1 (`not_observed != absent`) requires it. Forcing certainty into a
   research brief manufactures false confidence.
3. **`paths:` governs prose being read, not spec archaeology.** This rule loading on a
   `PLAN.md` read is not licence to reopen a closed spec and rewrite it to conform.

## Delivery

`paths:` injection fires on **read**, not on write — write-flows do not trigger it
(verified empirically, see `CHANGELOG.md` for v2.1.216). A skill that *writes* a covered
artifact therefore never receives this file from the frontmatter above. Any write-flow that
must apply §3 needs an **explicit Read step**; the frontmatter only covers the reviewer side.
The three writers that *create* a covered artifact carry that step today:
`skills/writing-plans/SKILL.md` (`PLAN.md`), `skills/xia2/SKILL.md` (`research-brief.md`), and
`skills/feature-intake/SKILL.md` (`SUMMARY.md`). Each edge is registered in
`scripts/render_skill_prompt.py` (`CONTEXT_MATRIX` `required_reads`) and enforced by its
`--check-all`, so deleting an explicit Read or its registration fails the suite instead of
shipping. That check is traceability-tier: it proves the word `Read` and the rule path share a
line in each writer, not that the instruction is imperative or obeyed. Later *update* flows
(e.g. the execution-phase agent appending `SUMMARY.md ### Verify` rows) receive this file via
`paths:` only when they read the artifact first — that edge is not gate-enforced.
