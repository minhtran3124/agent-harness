---
name: intent-review
description: Independently review a finished diff against the owner's verbatim original request, blind to the plan. Use to detect missing requested behavior, intent drift, and unrequested excess scope.
allowed-tools: Read, Grep, Glob, Agent, Task, Bash(git diff *), Bash(git log *), Bash(gh issue view *)
---

# Intent Review

This is the one plan-blind check. It asks: would the person who wrote the request recognise this
diff as what they asked for?

## Inputs

Pass the reviewer exactly two things:

1. **The request**, verbatim: the issue body or task text, or the text the caller passes.
2. **The diff range** `BASE..HEAD`.

Never pass the plan, the design, the research brief, `PLAN.md` prose, ADRs, answers to grilling
questions, or any summary by the orchestrator. The plan can carry the same misreading this review
exists to catch.

If the request is missing, STOP and say so. Never reconstruct it.

## Dispatch

Dispatch the `intent-reviewer` agent in a fresh context with only those two
inputs. In a workflow, the calling script does the dispatch.

## Output

Each finding quotes the request clause it evaluates:

- `gap`: a requested outcome is missing.
- `drift`: the diff differs from the request. State `changes behaviour: yes|no`.
- `excess`: built but not asked for.

End with `Verdict: match | gaps found`. The exact format is in `agents/intent-reviewer.md`.

## Route findings

- **gap, or drift that changes behaviour:** fix it if the fix is clear and in scope. Otherwise ask
  the owner. In auto mode, record a decision with `needs_review: true`.
- **drift that does not change behaviour, and excess:** list them in the PR. Never remove them
  without the owner's yes.

## Auto mode

Never ask the owner. Take the recommended option. Return `decisions[]` entries:
`{title, context, options, decision, why, consequences, how_to_reverse, confidence, needs_review}`.
Write no ADR files; `decision-record` does that. Set `needs_advisor` when the calling script
should consult the advisor.
