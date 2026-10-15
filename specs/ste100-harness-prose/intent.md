# Intent: Apply ASD-STE100 to harness prose

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

Harness prose that agents execute (skills, rules, agent definitions, dispatch prompts) is dense
and hard to parse. Long sentences, semicolons, and stacked clauses make it easy for an agent to
misread an instruction. (assumed: the target is agent-executed prose, not specs or knowledge-base entries)

## Proposed outcome

The harness uses the vendored `asd-ste100` skill (`.agents/skills/asd-ste100/`) so that
agent-executed text is simpler and easier for an agent to read. Scope is all three parts:

- A. Rewrite existing harness prose (skills, rules, agents, dispatch prompts) into STE-flavored style.
- B. Adopt `asd-ste100` as a harness skill and call it from the steps that write or edit that prose.
- C. Add `ste-lint.py` as an advisory (warn-only) check in CI or tests.

## Affected users and systems

Agents that load `skills/*/SKILL.md`, `rules/*.md`, `agents/*.md`, and skill dispatch prompts.
Humans who maintain that prose. (assumed)

## Constraints

- Preserve every condition, scope qualifier, and hedge in rewritten text; a rewrite must not change behavior. (assumed)
- Respect `specs/ste-terminology-evidence/DECISION.md`: §1 one-concept-one-word showed no measured effect, and a `lint_ste.py` + `PostToolUse` hook was rejected; do not mechanise an unmeasured rule into a blocking gate. (assumed)
- `SUMMARY.md` `### Intent` and `intent.md` are never rewritten (`rules/terminology.md` scope table). (assumed)
- Keep prompts lean; no new ceremony for its own sake. (assumed)

## Out of scope

- Creative or user-facing marketing copy. (assumed)
- Reproducing the ASD dictionary. (assumed)

## Open questions

- Should the result be measured (as `ste-terminology-evidence` did) before adoption, since prior trials found no effect from word-level consistency?
- Is `.agents/skills/asd-ste100/` plus `skills-lock.json` to be committed as a vendored third-party skill, or moved under `skills/`?

## What success looks like

(assumed) Rewritten or newly written agent-executed prose passes `ste-lint.py` hard rules
(semicolons, sentence length, phrasal verbs, nominalization, marketing adjectives) within an
agreed baseline, and every existing test in `bash scripts/run-tests.sh` still passes.

## Original request

check the skill asd-ste100 in @.agents/skills/asd-ste100/
/feature-intake thinking about apply it for our current harness workflow to help simplify text and help agent can read it with comfortable way.

Scope answer (2026-10-14): A + B + C
