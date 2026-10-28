# Agents

Sub-agent role definitions dispatched by skills (and by the orchestrator) for autonomous,
returnable work. Each agent is a focused role. Anything project-specific lives in `PROJECT.md`, or
`PROJECT.md` points to it.

## Where the role files live

The six role files ship in the plugin at `plugins/harness/agents/`. This folder holds only the
consumer-owned `PROJECT.md` and this note. `/harness:setup` creates `agents/PROJECT.md` in a consuming
repo from `plugins/harness/skills/setup/resources/PROJECT.template.md`, and never overwrites it.

## Inventory

Model, effort and tools are set in each role file's frontmatter. That is the only place they live.
A role with no `tools:` line inherits all tools. The read-only roles list only read tools, so the
harness, not the prompt, keeps them from writing.

| Agent | Role | Model | Effort | Tools | Dispatched by |
|---|---|---|---|---|---|
| `implementer` | Implement/refactor/fix code, end-to-end | claude-sonnet-5-5 | medium | all | `implement`, ad-hoc |
| `task-reviewer` | Read-only per-task spec + quality review, and the diagnosis review | claude-opus-5-5 | medium | Glob, Grep, Read | `implement`, `diagnosing-bugs` |
| `test-runner` | Run the minimal relevant tests and report/diagnose results | claude-haiku-5-5 | default | Glob, Grep, Read, WebFetch, WebSearch, Bash | after implementation |
| `researcher` | Read-only search and fact-finding for triage and xia2; returns facts with `file:line` or URL | claude-haiku-5-5 | default | Glob, Grep, Read, Bash, WebFetch, WebSearch | triage, `xia2` |
| `advisor` | Read-only second opinion on one question; returns a recommendation with reasons | claude-opus-5-5 | high | Glob, Grep, Read | orchestrator, on the advisor triggers in `CLAUDE.md` |
| `intent-reviewer` | Plan-blind check of a diff against the owner's verbatim request (gap / drift / excess) | claude-sonnet-5-5 | medium | Glob, Grep, Read, Bash | `intent-review` |

Dispatch with the namespaced type, for example `harness:implementer`.

## Portability model (mirrors xia2)

Agent role files are **universal**. They contain no stack-specific names. `PROJECT.md` is a thin
**index**, not a copy. It *points* to the repo's existing convention docs (architecture /
guidelines) for layering, error/validation, and style. It holds only the few execution facts that
no other doc reliably contains (test command, source→test mapping, failure hints).

When a repo has no such docs, its *Inline fallback* section carries the minimum.
`PROJECT.md` is the per-repo copy (a maintained file: edit it directly).

> **Why an index, not a copy:** restating a repo's architecture/guidelines here would create a
> second source of truth that drifts. Point to the real doc. Inline the content only when no such
> doc exists.

**To use these agents in another repo:** install the plugin and run `/harness:setup`. Then edit
`agents/PROJECT.md` by hand. Point it at that repo's convention docs and fill the *Test execution*
section. The role files do **not** change.

`PROJECT.md` here is an *agents-scoped* file: it drives implementation + test execution. It has
no counterpart in `skills/xia2/` — xia2 is zero-config and sets its own research depth.

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
`brainstorming` **skill**. A brainstorming subagent would be a category error. Invoke `brainstorming` directly.
