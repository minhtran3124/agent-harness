# Intent: diagnosing-bugs skill with six gated phases

Author: Claude
Status: approved

## Problem

The harness classifies `Input-type: bug fix` but routes it to no diagnosis step.
`skills/README.md` draws the bug-fix path through an external, optional `systematic-debugging`
skill. When that skill is absent, the agent reads code and guesses. `rules/auto-correct-scope.md`
and `implementer-prompt.md` require a red/green pair in `### Verify`, but say nothing about how to
find the cause before the test. No step minimises the repro, ranks hypotheses, tags
instrumentation, or deletes it.

## Proposed outcome

- A new `skills/diagnosing-bugs/SKILL.md` under 600 words, with long lists in `references/`.
- Invocation: user-invoked (`/diagnosing-bugs`) and chain-invoked by `feature-intake` for
  `Input-type: bug fix`; not model-invoked (closes Pocock #578).
- Six phases, each ending in one completion criterion: 1 feedback loop (one red command, run and
  shown; stop and ask if no loop can be built), 2 reproduce and minimise, 3 three to five ranked
  hypotheses with predictions (shown to the user; continue on own ranking if user is away),
  4 instrument (one probe per prediction, one variable at a time, `[DEBUG-xxxx]` tagged logs),
  5 fix via the bug-fix lane in `rules/auto-correct-scope.md` (failing test at a valid seam,
  committed before the fix; no seam → finding in `SUMMARY.md`), 6 cleanup (re-run the loop, grep
  and delete the debug prefix, delete throwaway harnesses, name the confirmed hypothesis in the
  commit message and SUMMARY `Rationale`).
- A redaction rule at the top of the skill: replace each secret with `<REDACTED>` before showing a
  command or output (closes Pocock #674).
- The per-task review of `subagent-driven-development` sits between Phase 4 and Phase 5 (closes
  Pocock #124).
- A diagnosis record at `specs/<slug>/diagnosis.md` (loop command, minimised repro, ranked
  hypotheses, confirmed one); `compound` reads it.
- `skills/diagnosing-bugs/scripts/hitl-loop.template.sh` for loops that need a human action.
- `skills/README.md`: the external `systematic-debugging` row and bug-fix path replaced by the new
  skill; the skill added to the handoff map.

## Affected users and systems

Agents and users fixing bugs through the harness. Files: new `skills/diagnosing-bugs/`,
`skills/feature-intake/SKILL.md`, `skills/subagent-driven-development/` (SKILL.md and/or
`implementer-prompt.md`), `skills/compound/SKILL.md`, `skills/README.md`, possibly
`rules/auto-correct-scope.md`, and the `.claude/` deployed copies via the deploy script.

## Constraints

- `diagnosing-bugs/SKILL.md` stays under 600 words; `feature-intake` stays under its ceiling
  (currently 461 body words), meeting caps by the #308 deletion test, not word trimming.
- Phase 5 relies on the prove-the-red assertion from #313 (`scripts/run_at_commit.py`).
- Changed agent prose follows `skills/asd-ste100/SKILL.md`.
- The skill must not fire on a quick question routed through intake.

## Out of scope

- Changing the red/green evidence gate in `scripts/verify_summary.py` or `hooks/commit-gate.sh`.
- Making the red-test check blocking by default.
- Adding new hooks or editing `settings.json`.

## Open questions

- Chain-invocation mechanism (assumed): `disable-model-invocation: true` stops the model from
  calling a skill through the Skill tool, which would also stop `feature-intake` from chaining it
  that way. Assumed: set `disable-model-invocation: true` and have `feature-intake` chain by
  instructing the agent to Read and follow `skills/diagnosing-bugs/SKILL.md`. Alternative: leave
  it model-invocable with a narrow description and rely on intake routing.
- `hitl-loop.template.sh` source (assumed): no `scripts/hitl-loop.template.sh` exists in this
  repo; the issue refers to Pocock's file at commit `49dd158`. Assumed: write an original
  equivalent here rather than copy third-party text.
- Review placement (assumed): "per-task review between Phase 4 and Phase 5" read as: the
  diagnosis (Phases 1–4, `diagnosis.md`) is reviewed before the Phase 5 fix task is dispatched.

## What success looks like

1. The skill runs on one recorded bug from `docs/solutions/` with a known cause, and the transcript
   shows a red loop before any hypothesis, a ranked list before any probe, and zero `[DEBUG-`
   tags in the final diff.
2. A quick question run through intake does not fire the skill.
3. `bash scripts/run-tests.sh` passes, including the skill-prompt word-count audit.

## Original request

run feature-intake for https://github.com/minhtran3124/agent-harness/issues/318
