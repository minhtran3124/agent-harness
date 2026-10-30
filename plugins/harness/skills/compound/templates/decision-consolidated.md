---
problem_type: decision
module: [module from CONTEXT_ANALYSIS]
tags: [union of tags from all DECISION_TRACK blocks + CONTEXT_ANALYSIS — deduplicated]
severity: [severity from CONTEXT_ANALYSIS]
applicable_when: [applicable_when from CONTEXT_ANALYSIS]
affects:
  - [union of affected files across all DECISION_TRACK blocks — one per line]
supersedes: null
confidence: high
confirmed_at: [today's date YYYY-MM-DD]
---

## Applicable When
[applicable_when from CONTEXT_ANALYSIS]

## Decision 1
### Context
[Context from DECISION_TRACK_1]
### Options Considered
[Options_Considered from DECISION_TRACK_1]
### Decision & Rationale
[Decision_and_Rationale from DECISION_TRACK_1]
### Applicable When
[Applicable_When from DECISION_TRACK_1]
### Consequences
[Consequences from DECISION_TRACK_1 — omit section if [none]]

## Decision 2
### Context
[Context from DECISION_TRACK_2]
### Options Considered
[Options_Considered from DECISION_TRACK_2]
### Decision & Rationale
[Decision_and_Rationale from DECISION_TRACK_2]
### Applicable When
[Applicable_When from DECISION_TRACK_2]
### Consequences
[Consequences from DECISION_TRACK_2 — omit section if [none]]

(Repeat ## Decision N pattern for each additional DECISION_TRACK_N block.)

## Related
[Paths from RELATED_DOCS.existing_files — omit section if empty]
