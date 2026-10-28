# Implementer prompt

Fill the brackets and send this to a fresh `coding` subagent, one per plan step.

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
- FIRST: Read `rules/auto-correct-scope.md`. It is not auto-loaded for you. Fix small bugs and
  blockers yourself and report each as a deviation. Return BLOCKED instead of acting on a Rule 4
  situation.
- If you change prose under `skills/`, `rules/` or `agents/`, Read it, then
  apply `skills/asd-ste100/SKILL.md`.

Return: status (DONE | BLOCKED | NEEDS_CONTEXT), commits (sha, subject), files touched,
Done-when output (excerpt on failure), and any concerns.
```
