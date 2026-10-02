---
problem_type: failure
module: harness
tags: subagent-driven-development, file-handoff, implementer-report, subagent-write, harness-state, runtime-policy
severity: standard
applicable_when: Dispatching an SDD implementer (or any subagent) whose contract tells it to write its report to a file under `.harness-state/sdd/` and return only the path.
affects:
  - skills/subagent-driven-development/implementer-prompt.md
  - skills/subagent-driven-development/SKILL.md
supersedes: null
confidence: high
confirmed_at: 2026-10-02
---
## Applicable When

An SDD implementer is told to write `.harness-state/sdd/report-<task>.md` and return only status,
commits, Verify, `Harness-Delta`, and the path.

## Symptom

In `opus-5-5-review-bindings` both parallel implementers had their `Write` of the report file
refused by Claude Code ("Subagents should return findings as text"). One wrote the file through a
Bash heredoc anyway; the other returned the whole report inline, and the controller transcribed it
into the expected path for the task reviewer.

## Wrong Approach

Working around the refusal with a Bash write, or silently treating a missing report file as
"no report". The first sidesteps a runtime rule and only works while Bash file writes are allowed;
the second would drop the Deviations/Blockers half of the contract the task reviewer needs.

## Why It Failed

`implementer-prompt.md` and `rules/orchestration.md` define the file handoff as the contract, but
the Claude runtime forbids subagents from writing report files with `Write`. The contract assumes
a capability the runtime does not grant, so each implementer improvises.

## Correct Approach

Treat the inline return as authoritative when the file write is refused: the controller writes
`.harness-state/sdd/report-<task>.md` from the returned text before building the review package,
and states in the file header that it was transcribed. Long term, make the contract say that
(the controller owns the file; the implementer returns the full structured report inline).

## Guardrail

proposed: amend `skills/subagent-driven-development/implementer-prompt.md` Report Format and the
matching SKILL.md bullet so the implementer returns the full structured report inline and the
controller persists it to `.harness-state/sdd/`; add a presence case to the context-propagation
regression test.

## Related

- docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md
- docs/solutions/harness/parallel-implementers-share-one-git-index.md
