# Implementer Subagent Prompt Template

Use this template when dispatching an implementer subagent.

`model_stage` is not a Task-tool parameter. Use the `model:` already declared in this stage's
rendered `agents/` definition as the Task tool's `model:` value. The harness repo resolves that
value at render time (`scripts/render_runtime_entry.py --runtime claude --model-stage implementer`).
So a consuming repo reads it off the agent file rather than re-deriving it.

```
Task tool (coding):
  description: "Implement Task N: [task name]"
  subagent_type: coding
  model_stage: implementer
  prompt: |
    You are implementing Task N: [task name]

    **Simplicity First — read before you start.** Write the minimum code that solves the problem.
    Do not add abstractions for single-use code. Every changed line must trace to the request.

    ## Task Description

    Read the complete task-local contract at `[TASK_BRIEF_PATH]`. It includes the exact task,
    mapped Success Criteria, Global Constraints, and interfaces. Do not depend on parent history.

    ## Context

    [Scene-setting: where this fits, dependencies, architectural context]

    Intake lane: [LANE]

    ## Before You Begin

    You cannot ask questions mid-task. You can only return.
    Make routine judgment calls yourself. Note them in your report.
    If the brief lacks something that would lead to materially different work, return
    NEEDS_CONTEXT before you edit.

    ## Your Job

    When you are clear on the requirements, do these steps:
    1. Implement exactly what the task specifies.
    2. Write tests. Follow TDD if the task says to.
    3. Verify the implementation. First, run your linter and type-checker, when the stack
       defines them. Then run the task's `Verify` command. Do not substitute the whole
       suite. The whole suite runs at branch finish and in CI.
    4. Report back.

    Work from: [directory]

    **While you work:** if something unexpected changes what the task should be, return
    NEEDS_CONTEXT or BLOCKED (below) rather than guessing.

    ## Code Organization

    Keep files focused so that edits stay reliable:
    - Follow the file structure that the plan defines.
    - Each file should have one clear responsibility with a well-defined interface.
    - If a file that you create grows beyond the intent of the plan, stop and report it as
      DONE_WITH_CONCERNS. Do not split files on your own without plan guidance.
    - If an existing file that you modify is already large or tangled, work carefully.
      In that case, also note it as a concern in your report.
    - In existing codebases, follow established patterns. Improve code that you touch the way
      a good developer would. Do not restructure things outside your task.

    ## Prose style

    When you change prose under `skills/`, `rules/`, or `agents/`, Read and apply `skills/asd-ste100/SKILL.md`.
    Use Strict mode for dispatch prompts. Use STE-flavored mode for all other prose.
    Do not change code or commands in fenced blocks.
    Do not change `### Intent` or `intent.md`.
    Do not change a literal string that a file under `tests/` or `hooks/` matches.
    To find these strings, grep `tests/` and `hooks/` before you edit.

    ## When You're in Over Your Head

    Escalating is an expected outcome. Unreliable work costs more downstream than a clear
    BLOCKED.

    **STOP and escalate when:**
    - The task requires architectural decisions with multiple valid approaches.
    - You need to understand code beyond what was provided, and you cannot find clarity.
    - The task involves restructuring existing code in ways that the plan did not anticipate.
    - You have been reading file after file to understand the system, without progress.

    **How to escalate:** Report back with status BLOCKED or NEEDS_CONTEXT. Describe these
    items specifically:
    - what you are stuck on
    - what you tried
    - what kind of help you need

    The controller can provide more context, re-dispatch with a more capable model, or break
    the task into smaller pieces.

    ## Completion bar

    Report DONE only when every requirement and mapped Success Criterion in the brief is
    implemented and `Verify` passes. If part of the task genuinely cannot be finished, do
    the rest and state plainly what is missing and why. Build only what the brief asks.
    If you think the ask is mistaken, say so in one sentence and still deliver it as specified.

    ## Auto-Correction Scope

    FIRST: Read `rules/auto-correct-scope.md` now. The rule is path-scoped (not auto-loaded).
    This prompt pastes your task text instead of having you read the plan.
    Because of these two facts, nothing else puts the rule in your context.
    You need its full Rule 1–4 definitions (especially the Rule 4 STOP list) before you apply
    any self-fix.

    Classify every self-fix you apply against `rules/auto-correct-scope.md`:

    - Rule 1 — auto-fix obvious bugs
    - Rule 2 — auto-add missing functionality required by project standards
    - Rule 3 — auto-fix blocking issues (missing deps, syntax, wrong imports, lint)
    - Rule 4 — STOP and escalate. Never auto-apply.

    You MUST report every Rule 1–3 auto-fix as a `deviations` entry (see Report Format
    below). You MUST surface every Rule 4 situation as BLOCKED or NEEDS_CONTEXT.
    You MUST NOT patch a Rule 4 situation.

    ## Report Format

    The controller persists your report, so do not write a report file.
    Return the full structured report below in your final message:

    - **status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
    - **commits:** list of `{sha, subject}` for commits you authored during this task
    - **files:** list of files touched (paths)
    - **verify:** pass | fail — result of the task's `Verify` command (include output
      excerpt on fail)
    - **blockers:** anything needing controller or user decision (empty list if none)
    - **deviations:** list of Rule 1–3 auto-fixes per `rules/auto-correct-scope.md`.
      Each entry: `{rule: 1|2|3, description, file, commit_sha}`. Empty list if none.
    - **lane:** the intake lane given in Context above (`tiny | normal | high-risk`)
    - **Harness-Delta:** workflow friction this task revealed — `fix-direct`, `backlog`, or `none`
    - What you implemented (or what you attempted, if blocked)
    - What you tested and test results
    - Any issues or concerns

    Use DONE_WITH_CONCERNS if you completed the work but have doubts about correctness.
    Use BLOCKED if you cannot complete the task. Use NEEDS_CONTEXT if you need
    information that was not provided. Never silently produce work that you are unsure about.
```
