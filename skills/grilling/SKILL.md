---
name: grilling
description: "Interview the owner about an important ticket until you both share the same understanding. Use when a ticket has open decisions that the owner must settle before design or planning. Writes a 'Confirmed decisions' comment on the ticket."
allowed-tools: Read, Grep, Glob, Bash(gh issue view *), Bash(gh issue comment *), Bash(git log *), Agent, AskUserQuestion
---

# Grilling

Interview the owner until the open decisions are settled. Do nothing else until the owner confirms.

The caller names `Mode: interactive` (default) or `Mode: auto`.

## Process

1. Read the ticket. Read the code it names.
2. Map the open decisions as a design tree. A decision hangs below the decision it depends on.
3. Find the frontier. The frontier is every decision whose prerequisites are settled.
4. Ask the whole frontier in one numbered round. Use `AskUserQuestion` when it is available. Otherwise write numbered text.
5. Give each question a recommended answer. Word the question so that "yes" accepts it. Then wait.
6. Add the answers to the tree. Find the new frontier. Ask the next round.

## Facts and decisions

For a search larger than a few reads, dispatch the `researcher` agent (Haiku). Never ask the owner for something you can look up.

Only decisions go to the owner. Put each decision in the round with a recommendation.

## Unanswered decisions

A decision still unanswered or evasive after two rounds becomes an assumption. Record the recommended answer as a decision with `needs_review: true`. Move on.

## Deep trees

The tree is deep when it has more than about 3 levels or more than about 10 open decisions. Then ask the caller to run the `advisor` agent. A skill cannot spawn agents inside a workflow. In an interactive main session, you may call the `advisor` agent directly.

## Stop

Stop when the frontier is empty and the owner confirms. A "yes" to the last round counts as confirmation. Act on nothing before that.

## Output

Write the confirmed decisions as ONE comment titled "Confirmed decisions". When the ticket is a GitHub issue, run `gh issue comment <n> --body-file <file>`. Otherwise return the text.

Return a short list of the decisions to the caller. Mark each assumed decision `needs_review`.

## Auto mode

Auto mode exists only for `--no-ask` runs. In auto mode you NEVER ask. Answer every question with its recommended answer. Return each one in `decisions[]` as:

`{title, context, options, decision, why, consequences, how_to_reverse, confidence, needs_review: true}`

Do not write ADR files. Do not post a comment unless the caller asks.
