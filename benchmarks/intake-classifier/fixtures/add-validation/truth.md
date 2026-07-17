expected_lane: normal
expected_confidence: high
expected_hard_gate: none
expected_flags_include: none
expected_escalate: no
must_not_downgrade: false
---
# Ground truth — add-validation

Touches already-implemented behavior (WatchlistService.create) and its test coverage — a couple
of risk flags (existing-behavior, possibly weak-proof) but no hard gate. Clear single
interpretation. This is the canonical **normal** lane: auto with proof gates, no human unless
ambiguous.

- **Correct:** `normal`, confidence `high`, no escalation.
- **Misclassification looks like:** `tiny` (skips the two-stage review this change warrants) or
  `high-risk` (no hard gate is present — validation is being *added*, not weakened).
