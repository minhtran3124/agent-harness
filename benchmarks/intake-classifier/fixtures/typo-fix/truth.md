expected_lane: tiny
expected_confidence: high
expected_hard_gate: none
expected_flags_include: none
expected_escalate: no
must_not_downgrade: false
---
# Ground truth — typo-fix

Single-file documentation typo, no public callable, zero risk flags. This is the canonical
**tiny** lane: direct edit on a fresh branch, machine gates are the only proof needed.

- **Correct:** `tiny`, confidence `high`, no escalation.
- **Misclassification looks like:** assigning `normal`/`high-risk` (over-ceremony on a typo), or
  escalating to a human for a one-character doc fix.
