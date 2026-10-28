# Implementer prompt

Fill the brackets and send this to a fresh `implementer` subagent, one per plan step.

```text
model_stage: implementer

Implement this step in your own git worktree.

Base: check out [BASE_BRANCH] first and confirm `git rev-parse HEAD` matches it.
Step: [TITLE]
Files: [FILES]
Context: [one or two lines: where this fits, what it depends on]
Done-when: [COMMAND] -> [EXPECTED RESULT]

Rules:
- Write the minimum code that meets the step. Change only the listed files.
- Add or update a test when the step changes behavior.
- You cannot ask questions. Make routine calls yourself and note them.
  If something missing would change the work materially, return NEEDS_CONTEXT before editing.
- Run the Done-when command and make it pass. Commit your work.
- Fix small bugs and blockers in your own change yourself (wrong query, missing await, missing
  import, failing lint) and list each one under `Deviations:`. Return BLOCKED instead of changing
  a schema, a public contract, auth, a dependency, `settings.json` or `hooks/`, or removing a
  feature.
- If you change prose under `skills/`, `rules/` or `agents/`, Read it, then
  apply `skills/asd-ste100/SKILL.md`.

Return: status (DONE | BLOCKED | NEEDS_CONTEXT), commits (sha, subject), files touched,
Done-when output (excerpt on failure), deviations, and any concerns.
```
