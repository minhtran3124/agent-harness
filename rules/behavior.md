# Behavioral Guidelines

> These guidelines bias toward caution over speed. For trivial tasks, use judgment.

Reduce common LLM coding mistakes. Apply to all work in this project.

## 1. Think Before Coding

- State assumptions explicitly before implementing. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, name what's confusing and stop. Don't guess.
- `not_observed != absent` — a missing search result, an unread file, or unavailable memory means *unknown*, not *absent*. Before claiming something does not exist, state where you looked.

## 2. Simplicity First

- Minimum code that solves the problem. Nothing speculative.
- No abstractions for single-use code.
- No error handling for impossible scenarios.
- No features, flexibility, or configurability that wasn't requested.
- If you write 200 lines and it could be 50, rewrite it.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

When editing existing code:
- Don't improve adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

Transform tasks into verifiable goals before starting:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Don't claim done without evidence — run the test, check the output, read the result.

## 5. Communicate Clearly

- Surface blockers immediately — don't silently work around them.
- When you change direction mid-task, say so and why.
- One sentence per update is enough. Don't narrate internal deliberation.

> **These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.