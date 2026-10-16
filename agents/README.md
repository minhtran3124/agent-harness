# Agents

Sub-agent role definitions dispatched by skills (and by the orchestrator) for autonomous,
returnable work. Each agent is a focused role. Anything project-specific lives in `PROJECT.md`, or
`PROJECT.md` points to it.

## Inventory

| Agent | Role | Model class | Dispatched by |
|---|---|---|---|
| `coding` | Implement/refactor/fix code, end-to-end | implementation high-capability | `subagent-driven-development`, ad-hoc |
| `reviewer` | Structurally read-only review passes (correctness-review, intent-review) | review high-capability | review skills |
| `task-reviewer` | Read-only per-task spec + quality review | review high-capability | `subagent-driven-development` |
| `test-runner` | Run the minimal relevant tests and report/diagnose results | test-execution fast | after implementation |

## Portability model (mirrors xia2)

Agent role files are **universal**. They contain no stack-specific names. `PROJECT.md` is a thin
**index**, not a copy. It *points* to the repo's existing convention docs (architecture /
guidelines) for layering, error/validation, and style. It holds only the few execution facts that
no other doc reliably contains (test command, source→test mapping, failure hints).

When a repo has no such docs, its *Inline fallback* section carries the minimum.
`PROJECT.template.md` is the pristine template. `PROJECT.md` is the per-repo copy (a maintained
file — edit it directly).

> **Why an index, not a copy:** restating a repo's architecture/guidelines here would create a
> second source of truth that drifts. Point to the real doc. Inline the content only when no such
> doc exists.

**To reuse these agents in another repo:**

1. Copy `agents/` into the new project.
2. Edit `PROJECT.md` by hand: point it at that repo's convention docs and fill the *Test
   execution* section. The agent role files do **not** change.
3. Adjust the inventory table above if you add/remove agents.

`PROJECT.md` here is an *agents-scoped* file: it drives implementation + test execution. It has
no counterpart in `skills/xia2/` — xia2 is zero-config and carries its risk-classification
signals inside its own `SKILL.md`.

## Skill vs. agent — when to use which

This boundary decides whether a capability belongs in `skills/` or `agents/`:

- **Interactive / human-in-the-loop → skill (runs in the main thread).** Work that asks the
  user questions in rounds, presents options, and waits for approval between steps cannot
  run as a subagent. Subagents execute autonomously and return a single summary. They have no
  channel for a live, multi-turn dialogue with the user.
- **Autonomous / returnable → agent (runs as a subagent).** Work with a clear input and a
  self-contained output fits a fresh-context subagent that does the job and returns a summary.
  Examples of this work are to implement code, run tests, or write a PR description.

**This is why there is no `brainstorming` agent.** Brainstorming is inherently interactive
(numbered question rounds, approval gates, "user reviews the spec"), so it lives only as the
`brainstorming` **skill**. A brainstorming subagent would be a category error. The old
brainstorming agent was also a stale, drift-prone fork of the skill. Invoke `brainstorming` directly.
