# research-citation-ledger — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate — the change extends `skills/xia2/SKILL.md` (research workflow) and adds a new verification gate; scope explicitly limited by the user to an opt-in gate for high-risk research
Flags: workflow-engine, multi-domain (skills/xia2 + scripts/ + templates or rules)
Affects: research-depth-policy (rules/research-depth.md → consumers skills/feature-intake, skills/xia2)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

"review ảnh hiện tại, đúc kết ra kiến thức từ đó, sau đó so sánh với repo harness hiện tại trên branch simplify. Xem xét thử chúng ta có thể học và áp dụng dc gì ở đây." (HERMES v0.20 grounded-citations infographic)

Scope decided by user selection: "Spec gap A qua intake — route gap A qua /feature-intake để classify lane rồi spec citation ledger cho research brief (sources.json + quote-evidence gate, opt-in high-risk)." Gap A from the review: research briefs cite raw URLs with no ledger, no attached quotes, and no verification — a hallucinated doc claim flows unchecked into design.md and PLAN.md.

## What changed

Intake record only, so far. Target: a per-spec citation ledger (`specs/<slug>/sources.json`) where xia2 registers each source URL at retrieval and receives a stable `[n]`; claims in research-brief.md cite `[n]`; an optional fact-check pass attaches quotes; a deterministic checker proves ID/URL/Sources consistency and `quote ⊆ provided evidence text` after normalization; the Sources section is rendered from the ledger, never hand-written. Opt-in gate for the high-risk lane, warn-first — mirroring the `REQUIRE_NOT_AUTO_VERIFIED=1` rollout precedent.

### Rationale

HERMES v0.20's core lesson fits this repo's evidence-tier principle (CLAUDE.md "Gate verifiability"): the gate enforces traceability only — it does not verify that evidence truly came from the URL (provenance) or that the claim is true. Verified gap: `specs/skill-prompt-refactor/research-brief.md` cites 5+ bare URLs with no quote and no checker; no source/citation/evidence script exists in `scripts/`.

### Alternatives considered

- Inline quotes in the brief without a ledger — weaker: no stable IDs, no render-from-ledger consistency, harder to check robustly.
- Re-fetch each URL as a Verify row — rejected: network-dependent, flaky, breaks the <60s pipe-free verify-row rule; HERMES deliberately leaves evidence↔URL in the not-verified panel.
- Full design fork deferred to `/brainstorming` output (design.md, pending approval).

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| lane evidence | `python3 scripts/verify_summary.py --lane research-citation-ledger` | 0 | high-risk evidence present | |

### Not auto-verified

- The `high-risk` lane call itself is judgment — risk-corroboration corroborates diff signals at commit time, not the classifier's reasoning — reached traceability (Lane line exists, hook will corroborate); not re-run because lane assignment is a human/judgment artifact by design.
- The claim "research briefs hallucinate sources often enough to justify a gate" is anecdotal (one inspected brief) — reached traceability (the gap exists: bare URLs, no checker); not re-run because no hallucination-rate measurement exists in-repo.

### Rollback

- `git revert <intake-sha>` — removes the spec directory; no runtime surface exists yet.

### Harness-Delta

- none
