# Diagnosing-bugs routing canaries

Each row gives an input, the tool call that the session must make or not make, and the outcome.
The skill sets `disable-model-invocation: true`. The runtime blocks a Skill-tool call for it.
So `intake` routes a bug fix with a Read of the file.
A human or a meta-eval session runs these cases. Per-commit CI does not run them.

| ID | Input (abbreviated) | Expected tool call | Expected outcome |
|----|---------------------|--------------------|------------------|
| RC-01 | "what does `lint-doc-truth.sh` check?" | no Read of `skills/diagnosing-bugs/SKILL.md`, no Skill call for it | the session answers the question. No diagnosis starts. |
| RC-02 | "fix: the deploy script exits 0 when the copy fails" (through `intake`) | Read `skills/diagnosing-bugs/SKILL.md`, no Skill call for it | intake writes `Input-type: bug fix`. Phase 1 starts before the depth route. |
| RC-03 | `/diagnosing-bugs` with a bug report | the skill runs | Phase 1 starts after the isolation step |
| RC-04 | "fix an off-by-one in one helper function" (depth S, bug fix) | Read `skills/diagnosing-bugs/SKILL.md` | all six phases run. `diagnosis.md` has all six fields. No "cause known" shortcut (D4). |

## Notes

- RC-01 is the over-firing canary. A quick question must not start a diagnosis.
- RC-02 is the chaining canary. The runtime blocks a Skill call for this skill.
  So a Skill call means that the route failed.
- RC-04 pins design decision D4. Depth S carries the full diagnosis cost.
