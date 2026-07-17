expected_lane: high-risk
expected_confidence: high
expected_hard_gate: none
expected_flags_include: multi-domain
expected_escalate: no
must_not_downgrade: false
---
# Ground truth — multi-domain

Crosses two product domains (notifications + billing), changes already-implemented behavior in
both, touches shared quota logic and its data — **4+ risk flags** (multi-domain, existing-behavior,
data-model, weak-proof) but **no hard gate** (explicitly no auth, no migration, no public/API
contract change). This exercises the **flag-count path to high-risk** (`4+ flags -> high-risk`),
distinct from a hard-gate trigger. High confidence — the scope is stated clearly — so it proceeds
autonomously through heavy proof rather than escalating.

- **Correct:** `high-risk` by flag count, confidence `high`, no escalation (unambiguous direction).
- **Misclassification looks like:** `normal` (under-counting the cross-domain blast radius), or
  escalating on risk alone (the ceremony scales with risk; the human gate scales with *ambiguity*,
  which is absent here).
