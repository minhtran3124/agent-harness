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
agent-executed text is simpler and easier for an agent to read. (assumed: which of these is
meant is open — see Open questions)

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

- Which reading is meant?
  - A. Rewrite existing harness prose (skills, rules, agents; ~14.7k words) into STE-flavored style.
  - B. Adopt `asd-ste100` as a harness skill and wire it into authoring steps (for example, used when writing or editing skills, rules, and dispatch prompts), without a bulk rewrite.
  - C. Add `ste-lint.py` as an advisory (warn-only) check in CI or tests.
  - Any combination of the above.
- Should the result be measured (as `ste-terminology-evidence` did) before adoption, since prior trials found no effect from word-level consistency?
- Is `.agents/skills/asd-ste100/` plus `skills-lock.json` to be committed as a vendored third-party skill, or moved under `skills/`?

## What success looks like

(assumed) Rewritten or newly written agent-executed prose passes `ste-lint.py` hard rules
(semicolons, sentence length, phrasal verbs, nominalization, marketing adjectives) within an
agreed baseline, and every existing test in `bash scripts/run-tests.sh` still passes.

## Original request

check the skill asd-ste100 in @.agents/skills/asd-ste100/
/feature-intake thinking about apply it for our current harness workflow to help simplify text and help agent can read it with comfortable way.
