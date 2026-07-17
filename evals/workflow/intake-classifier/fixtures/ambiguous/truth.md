expected_lane: any
expected_confidence: low
expected_hard_gate: none
expected_flags_include: none
expected_escalate: yes
must_not_downgrade: false
---
# Ground truth — ambiguous

"Make the dashboard better" has more than one materially different interpretation (performance?
layout? new widgets? accessibility?) — you cannot state the single thing the user wants in one
sentence. This isolates the **confidence axis from the risk axis**: regardless of what lane the
eventual work lands in, confidence is `low` and intake must **escalate to confirm intent before
work** (`rules/orchestration.md`: low confidence escalates regardless of lane).

- **Correct:** confidence `low`, escalate `yes`. `expected_lane: any` — the lane is *not* scored
  here; the point is the interruption decision, not the ceremony level.
- **Misclassification looks like:** proceeding autonomously at `high` confidence on a one-line vague
  request (guessing an interpretation instead of asking).
