---
name: own
description: "Run grilling or brainstorming in ownership mode. The owner answers each big decision first, then sees the agent's recommendation and a counter-argument. Use when the owner types /harness:own grill or /harness:own brainstorm. Not for autopilot or --no-ask runs."
argument-hint: "<grill | brainstorm> <#issue | issue URL | file path | free text>"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(gh issue view *), Bash(gh issue comment *), Bash(git log *), Agent, AskUserQuestion
---

# Own — the owner thinks first

The owner must be able to explain and defend each big decision. So for a big decision the owner
answers first, and only then sees your recommendation.

## Arguments

`/harness:own <mode> <target>`

| Mode | Base skill | Extra steps |
|---|---|---|
| `grill` | `${CLAUDE_PLUGIN_ROOT}/skills/grilling/SKILL.md` | none |
| `brainstorm` | `${CLAUDE_PLUGIN_ROOT}/skills/brainstorming/SKILL.md` | `references/brainstorm.md` |

If the mode is missing or unknown, ask for it with `AskUserQuestion`. If the arguments contain
`--no-ask` or `Mode: auto`, stop. Say that this skill needs an owner who answers.

## Base skill and precedence

Read the base skill and follow its process, its output files and its stop rule, in interactive
mode. Where this file and the base skill disagree, this file wins. The base skill's auto mode
never applies.

## Big decisions

First map the decisions. In `grill` this is the design tree. In `brainstorm` it is the approach
and its open choices. A decision is big when one of these is true:

- It is hard to reverse. It touches a data schema or storage, a public API or contract, an
  external dependency, security or auth, running cost, or behavior that users see.
- Your confidence in your own recommendation is low.

Keep at most 3. If more qualify, keep the 3 that are hardest to reverse. Tell the owner in one
line: "I will ask you first on: X, Y, Z." The owner can add or remove items. The owner's list wins.

All other decisions are small. Ask them as the base skill says, with a recommended answer.

## The protocol for one big decision

1. Ask in plain text, not with `AskUserQuestion`. One decision per message. Give no options and
   no recommendation: "What would you choose for X, and why?" Then wait.
2. Give your recommendation and its reason. Say where it differs from the owner's answer.
3. Give the strongest argument against your own recommendation. When you differ, your
   recommendation already argues against the owner's answer, so both sides now have a case. Call
   the `advisor` agent only when the owner asks for a second opinion.
4. Ask for the final choice with `AskUserQuestion`. List distinct options: the owner's answer
   first, then your recommendation if it differs, else the option the counter-argument favors,
   then "more facts". Label each option by its content only. Add no tag that points to your
   pick, such as "(Recommended)", "(my recommendation)" or "Take my recommendation:". The owner
   has already heard your view, and a tag would anchor them again. The owner decides.

When the owner has no first answer, record `Owner first answer: none`. In step 4, offer your
recommendation, the option the counter-argument favors, and "more facts".

Record each big decision in `specs/<slug>/decision.md`. Add three lines after `Decision:`:

```text
- Owner first answer: <what the owner said before seeing your answer>
- Agent recommendation: <yours>
- Counter-argument: <the argument against your recommendation>
```

## Output

The base skill's output, plus a short list of the big decisions. For each one, show the owner's
first answer and the final choice.
