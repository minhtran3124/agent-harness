---
problem_type: failure
module: [module from CONTEXT_ANALYSIS]
tags: [tags from CONTEXT_ANALYSIS]
severity: [severity from CONTEXT_ANALYSIS]
applicable_when: [Applicable_When from FAILURE_TRACK]
affects:
  - [files named in FAILURE_TRACK Correct_Approach (where the working code landed) — file path only, one per line]
supersedes: null
confidence: high
confirmed_at: [today's date YYYY-MM-DD]
---
## Applicable When
[Applicable_When content from FAILURE_TRACK]

## Symptom
[Symptom content from FAILURE_TRACK]

## Wrong Approach
[Wrong_Approach content from FAILURE_TRACK]

## Why It Failed
[Why_It_Failed content from FAILURE_TRACK]

## Correct Approach
[Correct_Approach content from FAILURE_TRACK]

## Guardrail
[Guardrail content from FAILURE_TRACK — a buildable artifact tagged `existing:` or `proposed:`.
`existing:` names a file/hook/rule already enforcing this; `proposed:` names an artifact to build
plus its target path. A `proposed:` guardrail is also appended to
`docs/harness-experimental/improvement-backlog.md` so the ratchet closes from learning → enforced rule.]

## Related
[Paths from RELATED_DOCS.existing_files — omit section if empty]
