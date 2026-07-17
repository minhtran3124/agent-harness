expected_lane: normal
expected_confidence: medium
expected_hard_gate: none
expected_flags_include: multi-domain
expected_escalate: no
must_not_downgrade: false
---
# Ground truth — multi-domain

Crosses two product domains (notifications + billing) and changes already-implemented behavior in
both, but with **no hard gate** (explicitly no auth, no migration, no public/API contract change).
The live flags are **existing-behavior (8), multi-domain (10), and weak-proof (9)** — **2–3 flags**,
which is the `2–3 flags -> normal` band, not `4+ -> high-risk`. This exercises the **flag-count
classification** for a genuinely internal cross-domain refactor. Confidence is `medium`, not high:
the direction is clear but there is one real open question — *which* of the two existing quota
calculations becomes the canonical one — a reasonable default exists, so it proceeds (note the
assumption) rather than escalating.

- **Correct:** `normal`, confidence `medium`, no escalation.
- **Misclassification looks like:** `high-risk` (over-counting — treating an internal refactor as
  4+ flags or inventing a data-migration/public-contract gate the request explicitly excludes).

> **Revision (2026-07-17):** originally labeled `high-risk` (claimed "4+ flags") with `high`
> confidence. Three independent blind runs all classified it `normal` / `medium`, and re-reading
> the request confirms only 2–3 flags fire and one design choice is open — the original answer key
> was too aggressive. Reclassified to `normal` / `medium`. Baseline / run2 / run3 scorecards
> **predate this revision** and are not comparable on this fixture (honesty rule: revise the key,
> mark prior runs non-comparable).
